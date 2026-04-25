# the embeddings creation part for this service is done outside of the application.
from typing import List, Tuple

from app.core.config import get_settings
from app.core.db.models import DeviceDocs
from openai import OpenAI
from sqlalchemy.orm import Session


class DeviceInfoService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key)

    def get_query_embedding(self, query: str) -> List[float]:
        response = self.client.embeddings.create(
            input=[query], model="text-embedding-3-small"
        )
        return response.data[0].embedding

    def search_faq(self, query: str, top_k: int = 3) -> List[Tuple[str, str, int]]:
        embedding = self.get_query_embedding(query)
        # Used pgvector cosine_distance for similarity search
        results = (
            self.db.query(DeviceDocs)
            .order_by(DeviceDocs.embedding.cosine_distance(embedding))
            .limit(top_k)
            .all()
        )
        return [(doc.text, doc.source, doc.chunk_index) for doc in results]
