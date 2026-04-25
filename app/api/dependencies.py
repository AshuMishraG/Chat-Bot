from app.core.db import EmbeddingsSessionLocal, SessionLocal


def get_db():
    """
    FastAPI dependency that provides a SQLAlchemy database session per request.

    This function uses a generator to create a new session for each request,
    yields it to the endpoint, and ensures the session is closed in a `finally`
    block, even if errors occur during the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_embeddings_db():
    """
    FastAPI dependency that provides a SQLAlchemy session for the embeddings DB.
    Used only by ChatBotContentSearchService.
    """
    if EmbeddingsSessionLocal is None:
        raise RuntimeError(
            "Embeddings DB is not configured. Set EMBEDDINGS_DATABASE_URL in .env"
        )
    db = EmbeddingsSessionLocal()
    try:
        yield db
    finally:
        db.close()
