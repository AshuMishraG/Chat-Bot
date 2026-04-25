import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict

import logfire
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.api import api, conv
from app.core.config import Settings, get_settings
from app.core.db import SessionLocal, engine, init_db
from app.core.json_response import PrettyJSONResponse
from app.services.embedding_service import EmbeddingService
from app.services.embedding_service_mixlists import MixlistEmbeddingService
from scripts.cleanup_embeddings import cleanup_embeddings
from scripts.scrap_chatbot_website import (
    create_vector_embeddings_of_scraped_content,
    scrape_chatbot_website,
)

logger = logging.getLogger(__name__)


def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        # Let the user exit gracefully with Ctrl+C
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_uncaught_exception

init_db()

# <====== Embedding Service Startup Event ======>


async def sync_recipe_embeddings():
    """
    A background task to synchronize recipe embeddings on startup.
    It creates its own database session.
    """
    logger.info("Background task started: Synchronizing recipe embeddings.")
    db = SessionLocal()
    try:
        embedding_service = EmbeddingService(db)
        await embedding_service.sync_embeddings()
    finally:
        db.close()
        logger.info(
            "Background task finished: Recipe embedding synchronization complete."
        )


async def sync_mixlist_embeddings():
    """
    A background task to synchronize mixlist embeddings on startup.
    It creates its own database session.
    """
    logger.info("Background task started: Synchronizing mixlist embeddings.")
    db = SessionLocal()
    try:
        mixlist_embedding_service = MixlistEmbeddingService(db)
        await mixlist_embedding_service.sync_embeddings()
    finally:
        db.close()
        logger.info(
            "Background task finished: Mixlist embedding synchronization complete."
        )


async def run_chatbot_website_scraper():
    """
    A background task to scrape the ChatBot website and generate embeddings on startup.
    This runs as a synchronous operation wrapped in an async function.
    """
    logger.info("Background task started: Scraping ChatBot website.")
    try:
        # Run the scraping (synchronous function)
        await asyncio.to_thread(scrape_chatbot_website)
        # Generate embeddings for the scraped content
        await asyncio.to_thread(create_vector_embeddings_of_scraped_content)
    finally:
        logger.info("Background task finished: ChatBot website scraping complete.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager. This is the recommended way to handle
    startup and shutdown events in modern FastAPI.
    """
    # Conditionally configure and instrument Logfire if a token is present : https://logfire.pydantic.dev/
    # Generate a key with write access
    if os.getenv("LOGFIRE_TOKEN"):
        logger.info("LOGFIRE_TOKEN found, initializing Logfire...")
        # Logfire configuration and instrumentations
        logfire.configure(
            token=os.getenv("LOGFIRE_TOKEN"),
            service_name="chatbot-api",
            scrubbing=False,
        )
        logfire.instrument_fastapi(app, capture_headers=True)
        logfire.instrument_sqlalchemy(engine)
        logfire.instrument_openai()
        logfire.instrument_pydantic()
        logfire.instrument_pydantic_ai()
        logfire.instrument_requests()
        logfire.instrument_httpx()
    else:
        logger.info("LOGFIRE_TOKEN not set. Skipping Logfire initialization.")

    if settings.sync_embeddings:
        logger.info(
            "Application startup: triggering embedding synchronization in the background."
        )
        task = asyncio.create_task(sync_recipe_embeddings())
        task.add_done_callback(
            lambda t: (
                logger.exception(
                    "sync_recipe_embeddings failed", exc_info=t.exception()
                )
                if t.exception()
                else None
            )
        )
        task = asyncio.create_task(sync_mixlist_embeddings())
        task.add_done_callback(
            lambda t: (
                logger.exception(
                    "sync_mixlist_embeddings failed", exc_info=t.exception()
                )
                if t.exception()
                else None
            )
        )

    if settings.cleanup_embeddings:
        logger.info(
            "Application startup: triggering embedding cleanup in the background."
        )
        task = asyncio.create_task(cleanup_embeddings())
        task.add_done_callback(
            lambda t: (
                logger.exception("cleanup_embeddings failed", exc_info=t.exception())
                if t.exception()
                else None
            )
        )

    if settings.scrap_chatbot_website:
        logger.info(
            "Application startup: triggering ChatBot website scraping in the background."
        )
        task = asyncio.create_task(run_chatbot_website_scraper())
        task.add_done_callback(
            lambda t: (
                logger.exception(
                    "run_chatbot_website_scraper failed", exc_info=t.exception()
                )
                if t.exception()
                else None
            )
        )

    yield
    logger.info("Application shutdown.")


# <====== End of Embedding Service Startup Event ======>


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

settings = get_settings()

app = FastAPI(
    debug=settings.debug,
    default_response_class=PrettyJSONResponse,
    lifespan=lifespan,
)

# read origins and methods from the env variable
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=settings.cors_allowed_methods,
    allow_headers=["*"],
)

app.mount(
    "/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static"
)
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app.include_router(api.router, prefix="/api")
app.include_router(conv.router, prefix="/api/conv")


# --- Demo UI Route ---
@app.get("/ui", response_class=HTMLResponse)
async def get_chat_ui(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


# --- Demo Cache UI Route ---
@app.get("/cache", response_class=HTMLResponse)
async def get_cache_ui(request: Request):
    return templates.TemplateResponse("cache.html", {"request": request})


# --- Feedback Management UI Route ---
@app.get("/feedback", response_class=HTMLResponse)
async def get_feedback_ui(request: Request):
    return templates.TemplateResponse("feedback.html", {"request": request})


# --- Admin UI Route ---
@app.get("/set-home-cards", response_class=HTMLResponse)
async def get_admin_ui(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


# --- Settings Debug Route ---


class SafeSettingsResponse(BaseModel):
    """
    A Pydantic model to define the structure of the sanitized settings response,
    ensuring sensitive fields are correctly represented.
    """

    environment: str
    debug: bool
    image_cache_enabled: bool
    hash_threshold: int
    postgres_db: str
    postgres_user: str
    postgres_host: str
    postgres_port: int
    # Masked fields
    openai_api_key: str
    database_url: str
    postgres_password: str


@app.get("/env-test", response_model=SafeSettingsResponse)
def get_safe_settings(settings: Settings = Depends(get_settings)):
    """
    Returns a sanitized version of the application settings for debugging,
    masking sensitive values like passwords and API keys.
    """
    # Define which keys are sensitive and should be masked
    SENSITIVE_KEYS = {
        "openai_api_key",
        "postgres_db",
        "postgres_host",
        "postgres_user",
        "postgres_password",
        "database_url",
    }

    # Get settings as a dictionary
    settings_dict = settings.model_dump()

    safe_settings: Dict[str, Any] = {}

    for key, value in settings_dict.items():
        if key in SENSITIVE_KEYS:
            # For sensitive keys, check for presence and replace value
            safe_settings[key] = "present" if value else "missing"
        else:
            # For non-sensitive keys, keep them as they are
            safe_settings[key] = value

    return safe_settings
