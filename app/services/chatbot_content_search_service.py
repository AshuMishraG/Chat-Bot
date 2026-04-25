import asyncio
import logging
from typing import List, Tuple

import httpx
from openai import AsyncOpenAI
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db.models import MixlistEmbeddings, RecipeEmbeddings
from app.models.models import Mixlist, Recipe

aclient = AsyncOpenAI()
logger = logging.getLogger(__name__)


class ChatBotContentSearchService:
    """
    Combined service for searching both recipes and mixlists using a single embedding call.
    This replaces the separate VectorSearchService and MixlistSearchService to reduce duplicate
    LLM calls and simplify the chat service.
    """

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    async def search(self, query: str) -> Tuple[List[Recipe], List[Mixlist]]:
        """
        Performs a vector search for both recipes and mixlists based on a query string.
        Makes a single embedding call and searches both tables in parallel.

        Args:
            query: The search query string

        Returns:
            A tuple of (recipes, mixlists) - lists of full Recipe and Mixlist objects
        """
        if not query:
            logger.warning("Search query is empty.")
            return [], []

        logger.debug("ChatBot content search: running for query (length=%s)", len(query))
        try:
            # Single LLM call for embeddings
            embedding_response = await aclient.embeddings.create(
                input=query, model="text-embedding-3-small", dimensions=768
            )
            query_embedding = embedding_response.data[0].embedding

            # Search both recipe and mixlist embeddings in parallel
            recipe_ids, mixlist_ids = await asyncio.gather(
                self._search_recipes(query_embedding),
                self._search_mixlists(query_embedding),
            )

            # Fetch full details for both in parallel
            recipes, mixlists = await asyncio.gather(
                self._fetch_recipes_by_ids(recipe_ids),
                self._fetch_mixlists_by_ids(mixlist_ids),
            )

            logger.debug(
                "ChatBot content search: done, %s recipes, %s mixlists",
                len(recipes),
                len(mixlists),
            )
            return recipes, mixlists

        except Exception as e:
            logger.error(
                f"An error occurred during chatbot content search: {e}", exc_info=True
            )
            return [], []

    async def _search_recipes(self, query_embedding: List[float]) -> List[str]:
        """
        Searches recipe embeddings using the provided query embedding.

        Args:
            query_embedding: The embedding vector to search with

        Returns:
            List of recipe IDs
        """
        try:
            similar_recipes = (
                self.db.query(
                    RecipeEmbeddings,
                    RecipeEmbeddings.embedding.cosine_distance(query_embedding).label(
                        "distance"
                    ),
                )
                .order_by("distance")
                .limit(3)
                .all()
            )

            if similar_recipes:
                recipe_ids = [rec.recipe_id for rec, _ in similar_recipes]
                return recipe_ids
            else:
                logger.debug("ChatBot content search: no similar recipes found.")
                return []

        except Exception as e:
            logger.error(
                f"An error occurred during recipe search: {e}", exc_info=True
            )
            return []

    async def _search_mixlists(self, query_embedding: List[float]) -> List[str]:
        """
        Searches mixlist embeddings using the provided query embedding.

        Args:
            query_embedding: The embedding vector to search with

        Returns:
            List of mixlist IDs
        """
        try:
            similar_mixlists = (
                self.db.query(
                    MixlistEmbeddings,
                    MixlistEmbeddings.embedding.cosine_distance(query_embedding).label(
                        "distance"
                    ),
                )
                .order_by("distance")
                .limit(3)
                .all()
            )

            if similar_mixlists:
                mixlist_ids = [m.mixlist_id for m, _ in similar_mixlists]
                return mixlist_ids
            else:
                logger.debug("ChatBot content search: no similar mixlists found.")
                return []

        except Exception as e:
            logger.error(
                f"An error occurred during mixlist search: {e}", exc_info=True
            )
            return []

    async def _fetch_recipes_by_ids(self, recipe_ids: List[str]) -> List[Recipe]:
        """
        Fetches full recipe details from an external API using a list of recipe IDs.

        Args:
            recipe_ids: List of recipe IDs to fetch

        Returns:
            List of Recipe objects
        """
        if not recipe_ids:
            return []

        recipes = []
        base_url = f"{self.settings.defteros_prod_api_url}/recipes/"

        async with httpx.AsyncClient() as http_client:
            for recipe_id in recipe_ids:
                try:
                    response = await http_client.get(
                        f"{base_url}{recipe_id}", timeout=10
                    )
                    response.raise_for_status()
                    recipe_payload = response.json()

                    recipes.append(Recipe(**recipe_payload))

                except httpx.RequestError as e:
                    logger.error(
                        f"Failed to fetch recipe {recipe_id}: {e}", exc_info=True
                    )
                except ValidationError as e:
                    logger.error(
                        f"Pydantic validation error for recipe {recipe_id}: {e}",
                        exc_info=True,
                    )
                except Exception as e:
                    logger.error(
                        f"Error processing recipe {recipe_id}: {e}", exc_info=True
                    )

        return recipes

    async def _fetch_mixlists_by_ids(self, mixlist_ids: List[str]) -> List[Mixlist]:
        """
        Fetches full mixlist details from an external API using a list of mixlist IDs.

        Args:
            mixlist_ids: List of mixlist IDs to fetch

        Returns:
            List of Mixlist objects
        """
        if not mixlist_ids:
            return []

        mixlists = []
        base_url = f"{self.settings.defteros_prod_api_url}/mixlists/"

        async with httpx.AsyncClient() as http_client:
            for mixlist_id in mixlist_ids:
                try:
                    response = await http_client.get(
                        f"{base_url}{mixlist_id}", timeout=10
                    )
                    response.raise_for_status()
                    mixlist_payload = response.json()

                    mixlists.append(Mixlist(**mixlist_payload))

                except httpx.RequestError as e:
                    logger.error(
                        f"Failed to fetch mixlist {mixlist_id}: {e}", exc_info=True
                    )
                except ValidationError as e:
                    logger.error(
                        f"Pydantic validation error for mixlist {mixlist_id}: {e}",
                        exc_info=True,
                    )
                except Exception as e:
                    logger.error(
                        f"Error processing mixlist {mixlist_id}: {e}", exc_info=True
                    )

        return mixlists

