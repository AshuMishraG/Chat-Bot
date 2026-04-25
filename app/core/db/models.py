import datetime as dt
import json
import uuid
from typing import Any, Dict, List

from pgvector.sqlalchemy import Vector  # This provides the 'Vector' type for SQLAlchemy
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from pydantic_core import to_jsonable_python
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.types import JSON, TypeDecorator

from . import Base


class JsonEncodedList(TypeDecorator):
    """
    SQLAlchemy type for storing a list of dictionaries as a JSON string.
    This provides a simple, flexible way to store structured but non-pydantic
    data in a JSON column.
    """

    impl = JSON
    cache_ok = True

    def process_bind_param(self, value: List[Dict[str, Any]], dialect) -> str:
        """
        Takes a List of Dicts and returns a JSON string for storage.
        """
        if value is not None:
            return json.dumps(value, default=str)
        return None

    def process_result_value(self, value: str, dialect) -> List[Dict[str, Any]]:
        """
        Takes a JSON string from the DB and returns a List of Dicts.
        """
        if value is not None:
            return json.loads(value)
        return []


class PydanticModelList(TypeDecorator):
    """
    SQLAlchemy type for storing a list of Pydantic-AI ModelMessage objects as JSON.

    Serializes the list of ModelMessage objects to a JSON string before
    storing it in the database, using the library's native functions.

    Deserializes the JSON string back into a list of ModelMessage objects
    when retrieving it from the database.
    """

    impl = JSON
    cache_ok = True

    def process_bind_param(self, value: List[ModelMessage], dialect) -> str:
        """
        Takes a List[ModelMessage] and returns a JSON string for storage.
        """
        if value is not None:
            # Use the library's function to convert objects to a JSON-safe format
            jsonable_value = to_jsonable_python(value)
            return json.dumps(jsonable_value)
        return None

    def process_result_value(self, value: str, dialect) -> List[ModelMessage]:
        """
        Takes a JSON string from the DB and returns a List[ModelMessage].
        """
        if value is not None:
            # First, parse the JSON string into a Python object (list of dicts)
            python_object = json.loads(value)
            # Use the library's TypeAdapter to validate and convert back to Pydantic objects
            return ModelMessagesTypeAdapter.validate_python(python_object)
        return None


class Messages(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False)
    session_id = Column(String(64), nullable=False)
    message_history = Column(JsonEncodedList, nullable=False)
    created_at = Column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))

    __table_args__ = (
        UniqueConstraint("user_id", "session_id", "id", name="uq_user_session_id"),
        Index("ix_chat_history_user_session", "user_id", "session_id"),
        Index("ix_chat_history_session_time", "session_id", "created_at"),
    )


class ChatHistorySummary(Base):
    __tablename__ = "chat_history_summary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False)
    session_id = Column(String(64), nullable=False)
    summary = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))

    __table_args__ = (
        UniqueConstraint("user_id", "session_id", name="uq_summary_user_session"),
        Index("ix_summary_user_session", "user_id", "session_id"),
    )


class ImageCache(Base):
    """Database model for storing image analysis cache - Simplified to use only perceptual hash"""

    __tablename__ = "image_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    perceptual_hash = Column(String(64), nullable=False, index=True)

    # Image metadata
    image_size = Column(String(20), nullable=False)
    image_format = Column(String(10), nullable=False)
    file_size = Column(Integer, nullable=False)

    # Analysis results
    ingredients = Column(JSON, nullable=True)  # Store as JSON
    analysis_confidence = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))
    last_accessed = Column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))
    access_count = Column(Integer, default=0)

    # Create indexes for faster lookups
    __table_args__ = (
        Index("idx_perceptual_hash", "perceptual_hash"),
        Index("idx_created_at", "created_at"),
        Index("idx_last_accessed", "last_accessed"),
    )


class RecipeEmbeddings(Base):
    """Database model for storing recipe embeddings for similarity search"""

    __tablename__ = "recipe_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(Text, nullable=False)
    # The full text string that was used to generate the embedding
    recipe_summary = Column(Text, nullable=False)
    embedding = Column(Vector(768), nullable=False)
    created_at = Column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))
    updated_at = Column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))

    __table_args__ = (  # Index on the embedding column for efficient similarity search
        # Use 'vector_cosine_ops' for cosine similarity
        Index(
            "ix_cocktails_embedding",
            embedding,
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class MixlistEmbeddings(Base):
    """Database model for storing mixlist embeddings for similarity search"""

    __tablename__ = "mixlist_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mixlist_id = Column(Text, nullable=False)
    # The full text string that was used to generate the embedding
    mixlist_summary = Column(Text, nullable=False)
    embedding = Column(Vector(768), nullable=False)
    created_at = Column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))
    updated_at = Column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))

    __table_args__ = (  # Index on the embedding column for efficient similarity search
        # Use 'vector_cosine_ops' for cosine similarity
        Index(
            "ix_mixlist_embedding",
            embedding,
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class DeviceDocs(Base):
    """
    Model for storing embeddings from device documentation used by DeviceInfoService
    """

    __tablename__ = "device_docs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String(256), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=False)
    created_at = Column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))

    __table_args__ = (Index("ix_device_docs_source_chunk", "source", "chunk_index"),)


class HomeCardDB(Base):
    __tablename__ = "home_cards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    prompt = Column(Text, nullable=False)
    status = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=dt.datetime.now
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=dt.datetime.now,
        onupdate=dt.datetime.now,
    )


class ConversationMessages(Base):
    __tablename__ = "conversation_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(Text, nullable=False)
    user_id = Column(Text, nullable=False)
    bot_message = Column(Text, nullable=False)
    user_message = Column(Text, nullable=False)
    message_turn_status = Column(Text, nullable=True)
    action_cards = Column(JSONB, nullable=True)
    ai_generated_recipe = Column(JSONB, nullable=True)
    chatbot_recipe = Column(JSONB, nullable=True)
    chatbot_mixlist = Column(JSONB, nullable=True)
    response_time = Column(Integer, nullable=True)
    device_type = Column(Text, nullable=True)
    created_at = Column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=True
    )

    __table_args__ = (
        Index("idx_conversation_messages_session_id", "session_id"),
        Index("idx_conversation_messages_user_id", "user_id"),
        Index("idx_conversation_messages_status", "message_turn_status"),
        Index("idx_conversation_messages_created_at", "created_at"),
    )


class ChatBotScrapedContent(Base):
    """Database model for storing scraped content from ChatBot website"""

    __tablename__ = "chatbot_scraped_content"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(Text, nullable=False, unique=True)
    page_title = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    content_embedding = Column(Vector(1536), nullable=True)  # Content embedding
    url_embedding = Column(Vector(1536), nullable=True)  # URL embedding
    created_at = Column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))
    updated_at = Column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))

    __table_args__ = (
        Index("idx_chatbot_scraped_content_url", "url"),
        Index("idx_chatbot_scraped_content_page_title", "page_title"),
        Index("idx_chatbot_scraped_content_created_at", "created_at"),
        # Index on the content embedding column for efficient similarity search
        # Use 'vector_cosine_ops' for cosine similarity
        Index(
            "idx_chatbot_scraped_content_content_embedding",
            "content_embedding",
            postgresql_using="hnsw",
            postgresql_ops={"content_embedding": "vector_cosine_ops"},
        ),
        # Index on the URL embedding column for efficient similarity search
        Index(
            "idx_chatbot_scraped_content_url_embedding",
            "url_embedding",
            postgresql_using="hnsw",
            postgresql_ops={"url_embedding": "vector_cosine_ops"},
        ),
    )


class ChatBotFeedback(Base):
    """Database model for storing the feedback about the AI responses. Collects feedback from multiple branches."""

    __tablename__ = "chatbot_feedback_01"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    comment = Column(Text)
    session_id = Column(Text, nullable=False)
    user_id = Column(Text, nullable=False)
    rating = Column(Text, nullable=False)
    reason = Column(Text)
    conversation_turn = Column(Text)
    branch = Column(Text)
    locale = Column(Text)
    app_version = Column(Text)
    platform = Column(Text)
    created_at = Column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))

    __table_args__ = (
        Index("idx_chatbot_feedback_session_id", "session_id"),
        Index("idx_chatbot_feedback_user_id", "user_id"),
        Index("idx_chatbot_feedback_rating", "rating"),
        Index("idx_chatbot_feedback_branch", "branch"),
        Index("idx_chatbot_feedback_created_at", "created_at"),
    )
