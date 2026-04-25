import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()


DATABASE_URL = getattr(settings, "database_url", None) or os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is required but not provided")

# Use PostgreSQL or other database
engine = create_engine(DATABASE_URL)

SessionLocal: sessionmaker = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)

Base = declarative_base()

# Embeddings DB (used only by ChatBotContentSearchService)
EMBEDDINGS_DATABASE_URL = getattr(
    settings, "embeddings_database_url", None
) or os.getenv("EMBEDDINGS_DATABASE_URL")

embeddings_engine = (
    create_engine(EMBEDDINGS_DATABASE_URL) if EMBEDDINGS_DATABASE_URL else None
)
EmbeddingsSessionLocal: sessionmaker | None = (
    sessionmaker(autocommit=False, autoflush=False, bind=embeddings_engine)
    if embeddings_engine is not None
    else None
)


def init_db():
    Base.metadata.create_all(bind=engine, checkfirst=True)


init_db()
