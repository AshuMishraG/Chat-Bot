import logging
import re
from typing import Any, Dict, List, Set

import httpx
from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db.models import MixlistEmbeddings

logger = logging.getLogger(__name__)

aclient = AsyncOpenAI()

# This file is for automatic creation and syncing of mixlist embeddings.
# Because of this service the embeddings will be up to date with the mixlists.
# IMPORTANT: Currently, It runs only on application startup.


class MixlistEmbeddingService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def sync_embeddings(self):
        """
        Main method to synchronize embeddings. It fetches all mixlists,
        finds which ones are missing embeddings, and creates them.
        """
        logger.info("Starting mixlist embedding synchronization process...")
        try:
            all_mixlists = await self._fetch_all_mixlists()
            if not all_mixlists:
                logger.warning(
                    "No mixlists found from the external API. Aborting sync."
                )
                return

            existing_mixlist_ids = self._get_existing_embedding_ids()

            new_mixlists = [
                mixlist
                for mixlist in all_mixlists
                if mixlist.get("id") not in existing_mixlist_ids
            ]

            if not new_mixlists:
                logger.info(
                    "All mixlists are already up-to-date. No new embeddings needed."
                )
                return

            logger.info(f"Found {len(new_mixlists)} new mixlists that need embeddings.")

            await self._create_embeddings_for_mixlists(new_mixlists)

            logger.info(
                "Mixlist embedding synchronization process completed successfully."
            )

        except Exception as e:
            logger.error(
                f"An error occurred during mixlist embedding synchronization: {e}",
                exc_info=True,
            )
        finally:
            await self.http_client.aclose()

    async def _fetch_all_mixlists(self) -> List[Dict[str, Any]]:
        """
        Fetches all mixlists from the external API, handling pagination using limit and offset.
        """
        all_mixlists = []
        offset = 0
        limit = 100  # Fetch 100 mixlists per page to be efficient
        url = f"{self.settings.defteros_api_url}/mixlists"
        logger.info(f"Fetching all mixlists from mixlists API endpoint...")

        while True:
            try:
                response = await self.http_client.get(
                    f"{url}?limit={limit}&offset={offset}"
                )
                response.raise_for_status()

                data = response.json()
                mixlists_on_page = data.get("data", [])

                if not mixlists_on_page:
                    break

                all_mixlists.extend(mixlists_on_page)
                offset += limit

            except httpx.RequestError as e:
                logger.error(
                    f"Failed to fetch mixlists from {offset} to {offset + limit}: {e}"
                )
                return []

        # logger.info(
        #     f"Successfully fetched a total of {len(all_mixlists)} mixlists from the API."
        # )
        return all_mixlists

    def _get_existing_embedding_ids(self) -> Set[str]:
        """
        Retrieves a set of all mixlist_ids that already have embeddings in the database.
        """
        logger.info("Fetching existing mixlist embedding IDs from the database...")
        existing_ids = self.db.query(MixlistEmbeddings.mixlist_id).all()
        id_set = {item[0] for item in existing_ids}
        logger.info(f"Found {len(id_set)} existing mixlist embeddings.")
        return id_set

    async def _create_embeddings_for_mixlists(self, mixlists: List[Dict[str, Any]]):
        """
        Generates and stores embeddings for a list of new mixlists in batches.
        """
        logger.info(f"Creating embeddings for {len(mixlists)} new mixlists...")
        batch_size = 200  # A reasonable batch size to avoid timeouts

        for i in range(0, len(mixlists), batch_size):
            batch_mixlists = mixlists[i : i + batch_size]
            logger.info(
                f"Processing batch {(i // batch_size) + 1}/{(len(mixlists) + batch_size - 1) // batch_size}..."
            )

            summaries = [
                self._generate_mixlist_summary(mixlist) for mixlist in batch_mixlists
            ]
            mixlist_ids = [mixlist.get("id") for mixlist in batch_mixlists]

            try:
                embedding_response = await aclient.embeddings.create(
                    input=summaries, model="text-embedding-3-small", dimensions=768
                )

                for j, data in enumerate(embedding_response.data):
                    new_embedding = MixlistEmbeddings(
                        mixlist_id=mixlist_ids[j],
                        mixlist_summary=summaries[j],
                        embedding=data.embedding,
                    )
                    self.db.add(new_embedding)

                self.db.commit()
                logger.info(
                    f"Successfully created and stored {len(batch_mixlists)} new embeddings for this batch."
                )

            except Exception as e:
                logger.error(
                    f"Failed to create embeddings from OpenAI for a batch: {e}",
                    exc_info=True,
                )
                self.db.rollback()
                raise

    def _generate_mixlist_summary(self, mixlist_data: Dict[str, Any]) -> str:
        """
        Generates a concise text summary of a mixlist for creating the embedding string.
        """
        name = mixlist_data.get("name", "N/A")
        description_html = mixlist_data.get("description", "")
        # Remove HTML tags from description
        description = re.sub(r"<[^>]+>", "", description_html or "").strip()

        # Correctly access the list of recipes using the 'recipes' key
        recipes_list = mixlist_data.get("recipes", [])
        cocktails = ", ".join(
            [recipe.get("name", "") for recipe in recipes_list if recipe.get("name")]
        )

        # Combine mixlist tags and tags from all recipes within it
        mixlist_tags = mixlist_data.get("tags", [])
        recipe_tags = []
        all_ingredients = set()
        for recipe in recipes_list:
            recipe_tags.extend(recipe.get("tags", []))
            for ingredient in recipe.get("ingredients", []):
                if ingredient_name := ingredient.get("name"):
                    all_ingredients.add(ingredient_name)

        # Get unique tags
        all_tags = sorted(list(set(mixlist_tags + recipe_tags)))
        tags = ", ".join(all_tags)

        # Get unique ingredients
        ingredients = ", ".join(sorted(list(all_ingredients)))

        return f"Mixlist name: {name}. Mixlist Description: {description}. Cocktails included: {cocktails}. Ingredients include: {ingredients}. Tags: {tags}."
