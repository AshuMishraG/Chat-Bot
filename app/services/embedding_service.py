import logging
from typing import Any, Dict, List, Set

import httpx
from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db.models import RecipeEmbeddings

logger = logging.getLogger(__name__)

aclient = AsyncOpenAI()

# This file is for automatic creation and syncing of recipe embeddings.
# Because of this service the embeddings will be up to date with the recipes.
# IMPORTANT: Currently, It runs only on application startup.


class EmbeddingService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def sync_embeddings(self):
        """
        Main method to synchronize embeddings. It fetches all recipes,
        finds which ones are missing embeddings, and creates them.
        """
        logger.info("Starting embedding synchronization process...")
        try:
            all_recipes = await self._fetch_all_recipes()
            if not all_recipes:
                logger.warning("No recipes found from the external API. Aborting sync.")
                return

            existing_recipe_ids = self._get_existing_embedding_ids()

            new_recipes = [
                recipe
                for recipe in all_recipes
                if recipe.get("id") not in existing_recipe_ids
            ]

            if not new_recipes:
                logger.info(
                    "All recipes are already up-to-date. No new embeddings needed."
                )
                return

            logger.info(f"Found {len(new_recipes)} new recipes that need embeddings.")

            await self._create_embeddings_for_recipes(new_recipes)

            logger.info("Embedding synchronization process completed successfully.")

        except Exception as e:
            logger.error(
                f"An error occurred during embedding synchronization: {e}",
                exc_info=True,
            )
        finally:
            await self.http_client.aclose()

    async def _fetch_all_recipes(self) -> List[Dict[str, Any]]:
        """
        Fetches all recipes from the external API, handling pagination using limit and offset.
        """
        all_recipes = []
        offset = 0
        limit = 100  # Fetch 100 recipes per page to be efficient
        url = f"{self.settings.defteros_api_url}/recipes"
        logger.info(f"Fetching all recipes from recipes API endpoint...")

        while True:
            try:
                response = await self.http_client.get(
                    f"{url}?limit={limit}&offset={offset}"
                )
                response.raise_for_status()

                data = response.json()
                recipes_on_page = data.get("data", [])

                if not recipes_on_page:
                    break

                all_recipes.extend(recipes_on_page)
                offset += limit

            except httpx.RequestError as e:
                logger.error(
                    f"Failed to fetch recipes from {offset} to {offset + limit}: {e}"
                )
                return []

        logger.info(
            f"Successfully fetched a total of {len(all_recipes)} recipes from the API."
        )
        return all_recipes

    def _get_existing_embedding_ids(self) -> Set[str]:
        """
        Retrieves a set of all recipe_ids that already have embeddings in the database.
        """
        logger.info("Fetching existing recipe embedding IDs from the database...")
        existing_ids = self.db.query(RecipeEmbeddings.recipe_id).all()
        id_set = {item[0] for item in existing_ids}
        logger.info(f"Found {len(id_set)} existing recipe embeddings.")
        return id_set

    async def _create_embeddings_for_recipes(self, recipes: List[Dict[str, Any]]):
        """
        Generates and stores embeddings for a list of new recipes in batches.
        """
        logger.info(f"Creating embeddings for {len(recipes)} new recipes...")
        batch_size = 200  # A reasonable batch size to avoid timeouts

        for i in range(0, len(recipes), batch_size):
            batch_recipes = recipes[i : i + batch_size]
            logger.info(
                f"Processing batch {(i // batch_size) + 1}/{(len(recipes) + batch_size - 1) // batch_size}..."
            )

            summaries = [
                self._generate_recipe_summary(recipe) for recipe in batch_recipes
            ]
            recipe_ids = [recipe.get("id") for recipe in batch_recipes]

            try:
                embedding_response = await aclient.embeddings.create(
                    input=summaries, model="text-embedding-3-small", dimensions=768
                )

                for j, data in enumerate(embedding_response.data):
                    new_embedding = RecipeEmbeddings(
                        recipe_id=recipe_ids[j],
                        recipe_summary=summaries[j],
                        embedding=data.embedding,
                    )
                    self.db.add(new_embedding)

                self.db.commit()
                logger.info(
                    f"Successfully created and stored {len(batch_recipes)} new embeddings for this batch."
                )

            except Exception as e:
                logger.error(
                    f"Failed to create embeddings from OpenAI for a batch: {e}",
                    exc_info=True,
                )
                self.db.rollback()
                raise

    def _generate_recipe_summary(self, recipe_data: Dict[str, Any]) -> str:
        """
        Generates a concise text summary of a recipe for creating the embedding string.
        """
        # This is a simplified summary. It can be enhanced for better search results.
        name = recipe_data.get("name", "N/A")
        description = recipe_data.get("description", "")
        ingredients = ", ".join(
            [ing.get("name", "") for ing in recipe_data.get("ingredients", [])]
        )
        tags_list = recipe_data.get("tags", [])
        tags = ", ".join(tags_list)
        return f"Cocktail name: {name}. Cocktail Description: {description}. Ingredients include {ingredients}. Tags: {tags}."
