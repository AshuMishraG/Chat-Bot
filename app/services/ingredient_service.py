import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings
from app.models.models import Recipe, VisionIngredient

logger = logging.getLogger(__name__)


class IngredientService:
    """
    Service to interact with Defteros ingredient taxonomy endpoints.

    Provides methods to:
    - List existing parent ingredients (secondary categories) grouped by primary category
    - Create new parent ingredients when absolutely necessary
    """

    def __init__(self) -> None:
        """Initialize service with API URL."""
        settings = get_settings()
        self.defteros_api_url = settings.defteros_api_url.rstrip("/")

    async def list_parent_ingredients(self) -> List[Dict[str, Any]]:
        """
        Fetch all parent ingredients (secondary categories) from Defteros.

        Returns:
            List of ingredient objects with structure:
            {
                "id": str,
                "name": str,  # secondary category name
                "is_perishable": bool,
                "category": {"id": str, "name": "base|mixer|additional|garnish"}
            }
        """
        url = f"{self.defteros_api_url}/parent_ingredients"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=15.0)
                resp.raise_for_status()
                return resp.json()

        except httpx.HTTPStatusError as exc:
            logger.error(
                f"HTTP error while fetching parent ingredients from {url}: {exc}"
            )
            return []
        except httpx.RequestError as exc:
            logger.error(
                f"Request error while fetching parent ingredients from {url}: {exc}"
            )
            return []

    def build_taxonomy_block(self, taxonomy: List[Dict[str, Any]]) -> str:
        try:
            by_primary: Dict[str, List[Dict[str, Any]]] = {
                "base": [],
                "mixer": [],
                "additional": [],
                "garnish": [],
            }

            # Collect items with perishable info
            for item in taxonomy or []:
                category = (item.get("category") or {}).get("name")
                name = item.get("name")
                perishable = item.get("is_perishable", False)

                if category and name and category in by_primary:
                    by_primary[category].append(
                        {"name": name, "perishable": perishable}
                    )

            lines = [
                "<secondary_category_list>",
                "Allowed secondary categories for each primary category:",
            ]

            # Format each category
            for primary, items in by_primary.items():
                if items:
                    # Deduplicate by name,
                    # Format into "7 Up": {"perishable": true}
                    json_str = json.dumps(items, indent=2, ensure_ascii=False)
                    lines.append(f"- {primary}: {json_str}")

            lines.append(
                'If none fits, propose in "new_parent_ingredients" using: {"name":"<secondary_category>","is_perishable":true|false,"category":{"name":"<base|mixer|additional|garnish>"}}'
            )
            lines.append("</secondary_category_list>")
            return "\n".join(lines)

        except Exception as e:
            logger.error("Error building taxonomy block", exc_info=True)
            return ""

    async def create_new_parent_ingredients(self, payload: Any) -> None:
        # Extract agent-proposed items (may contain empty objects)
        raw_items: List[Dict[str, Any]] = (
            getattr(payload, "new_parent_ingredients", []) or []
        )
        recipes: List[Recipe] = getattr(payload, "recipes", []) or []

        # Build a case-insensitive lookup of existing names per primary
        existing = {
            "base": set(),
            "mixer": set(),
            "additional": set(),
            "garnish": set(),
        }
        taxonomy = await self.list_parent_ingredients()
        for it in taxonomy:
            cat = (it.get("category") or {}).get("name")
            nm = (it.get("name") or "").strip().lower()
            if cat in existing and nm:
                existing[cat].add(nm)

        def parse_item(obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            if not isinstance(obj, dict):
                return None
            name = str(obj.get("name") or "").strip()
            # Accept either nested category.name or a top-level category_name
            primary = None
            category_dict = obj.get("category")
            if isinstance(category_dict, dict):
                primary = category_dict.get("name")
            if not primary:
                primary = obj.get("category_name")
            if primary:
                primary = str(primary).strip().lower()
            is_perishable = obj.get("is_perishable")
            if is_perishable is None and primary in ("mixer", "garnish"):
                is_perishable = True
            if is_perishable is None and primary in ("base", "additional"):
                is_perishable = False
            if not name or primary not in existing:
                return None
            return {
                "name": name,
                "primary": primary,
                "is_perishable": bool(is_perishable),
            }

        # 1) Gather valid proposals from agent-proposed items
        proposals: Dict[tuple, Dict[str, Any]] = {}
        for obj in raw_items:
            parsed = parse_item(obj)
            if not parsed:
                continue
            key = (parsed["primary"], parsed["name"].strip().lower())
            if key[1] in existing[parsed["primary"]]:
                continue
            proposals[key] = parsed

        # 2) Fallback: derive from recipe ingredients if agent didn't provide valid proposals
        if not proposals:
            for recipe in recipes:
                try:
                    for ing in getattr(recipe, "ingredients", []) or []:
                        cat = getattr(ing, "category", None)
                        if not cat:
                            continue
                        primary = getattr(cat, "primary", None)
                        secondary = getattr(cat, "secondary", None)
                        if not primary or not secondary:
                            continue
                        primary_l = str(primary).strip().lower()
                        name = str(secondary).strip()
                        if primary_l not in existing or not name:
                            continue
                        sec_key = name.lower()
                        if sec_key in existing[primary_l]:
                            continue
                        key = (primary_l, sec_key)
                        if key in proposals:
                            continue
                        is_perishable = (
                            True if primary_l in ("mixer", "garnish") else False
                        )
                        proposals[key] = {
                            "name": name,
                            "primary": primary_l,
                            "is_perishable": is_perishable,
                        }
                except Exception:
                    logger.debug(
                        "Skipping recipe while scanning for unknown secondaries",
                        exc_info=True,
                    )

        if not proposals:
            return

        # 3) Create all proposed parent ingredients (deduped)
        for (_primary, _sec_key), data in proposals.items():
            try:
                if _sec_key in existing[_primary]:
                    continue
                success = await self.create_parent_ingredient(
                    name=data["name"],
                    is_perishable=data["is_perishable"],
                    category_name=data["primary"],
                )
                if success:
                    existing[_primary].add(_sec_key)
                    logger.info(
                        f"Created parent ingredient '{data['name']}' under '{data['primary']}'"
                    )
            except (ValueError, TypeError) as e:
                logger.error(f"Value/Type error while creating parent ingredient: {e}")
            except httpx.HTTPError as e:
                logger.error(f"HTTP error while creating parent ingredient: {e}")
            except Exception as e:
                logger.exception(
                    f"Unexpected error while creating parent ingredient: {e}"
                )

    async def create_parent_ingredient(
        self,
        *,
        name: str,
        is_perishable: bool,
        category_name: str,
    ) -> bool:
        """
        Create a new parent ingredient (secondary category) in Defteros.

        Args:
            name: The secondary category name (e.g., "Gin-London Dry")
            is_perishable: Whether the ingredient is perishable
            category_name: Primary category ("base", "mixer", "additional", or "garnish")

        Returns:
            True if creation was successful, False otherwise
        """
        url = f"{self.defteros_api_url}/parent_ingredients"
        payload = {
            "name": name,
            "is_perishable": is_perishable,
            "category_name": category_name,
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, timeout=15.0)

                if resp.status_code in (200, 201):
                    logger.info(
                        f"Created parent ingredient '{name}' under '{category_name}'"
                    )
                    return True

                logger.warning(
                    f"Failed to create parent ingredient '{name}' ({category_name}). "
                    f"Status: {resp.status_code}"
                )
                return False

        except httpx.RequestError as exc:
            logger.error(f"Request error creating parent ingredient '{name}': {exc}")
            return False
        except httpx.HTTPStatusError as exc:
            logger.error(
                f"HTTP status error creating parent ingredient '{name}': {exc}"
            )
            return False

    async def verify_ingredients(
        self, ing_list: Optional[List[VisionIngredient]]
    ) -> List[VisionIngredient]:
        if not ing_list:
            return []
        payload = await self.list_parent_ingredients()

        # Create a lookup dictionary for existing parent ingredients for efficient access
        existing_ingredients_map = {
            item["name"].lower(): item["is_perishable"] for item in payload
        }

        for ingredient in ing_list:
            if (
                ingredient.category
                and ingredient.category.secondary
                and ingredient.category.secondary.lower() in existing_ingredients_map
            ):
                # Get the perishable status from the existing taxonomy
                existing_perishable_status = existing_ingredients_map[
                    ingredient.category.secondary.lower()
                ]
                # If the perishable status differs, update the VisionIngredient object
                should_update_perishable = (
                    ingredient.perishable is not None
                    and ingredient.perishable != existing_perishable_status
                )
                if should_update_perishable:
                    ingredient.perishable = existing_perishable_status
        return ing_list
