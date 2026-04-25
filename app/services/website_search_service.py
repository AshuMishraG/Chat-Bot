import logging
from typing import Optional

from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db.models import ChatBotScrapedContent

aclient = AsyncOpenAI()
logger = logging.getLogger(__name__)


class WebsiteSearchService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    async def search(self, query: str, top_k: int = 3) -> Optional[str]:
        """
        Performs a hybrid vector search for ChatBot website content using both
        content and URL embeddings, then returns the most relevant URL based
        purely on similarity scores.

        Args:
            query: The search query
            top_k: Number of top results to retrieve from each embedding type (default: 3)

        Returns the most relevant URL based on similarity search,
        otherwise returns None.
        """
        if not query:
            logger.warning("Website search: empty query.")
            return None

        logger.debug("Website search: running (top_k=%s)", top_k)
        try:
            # Generate embedding for the query
            embedding_response = await aclient.embeddings.create(
                input=query,
                model="text-embedding-3-small",
                dimensions=1536,
                timeout=30.0,
            )
            query_embedding = embedding_response.data[0].embedding

            # Search using content embeddings
            content_results = (
                self.db.query(
                    ChatBotScrapedContent,
                    ChatBotScrapedContent.content_embedding.cosine_distance(
                        query_embedding
                    ).label("distance"),
                )
                .filter(ChatBotScrapedContent.content_embedding.isnot(None))
                .order_by("distance")
                .limit(top_k)
                .all()
            )

            # Search using URL embeddings
            url_results = (
                self.db.query(
                    ChatBotScrapedContent,
                    ChatBotScrapedContent.url_embedding.cosine_distance(
                        query_embedding
                    ).label("distance"),
                )
                .filter(ChatBotScrapedContent.url_embedding.isnot(None))
                .order_by("distance")
                .limit(top_k)
                .all()
            )

            if not content_results and not url_results:
                logger.debug("Website search: no similar content found.")
                return None

            # Select the single best URL purely based on similarity scores
            best_url: Optional[str] = None
            best_similarity: float = -1.0  # similarity = 1 - distance

            # Consider content-based search results
            for content, distance in content_results:
                similarity = 1 - distance
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_url = content.url

            # Consider URL-based search results
            for content, distance in url_results:
                similarity = 1 - distance
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_url = content.url

            if best_url is not None:
                logger.info("Website search: returning URL (similarity=%.2f)", best_similarity)
                return best_url

            logger.debug("Website search: no suitable URL.")
            return None

        except Exception as e:
            logger.error("Website search error: %s", e, exc_info=True)
            return None
