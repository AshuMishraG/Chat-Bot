from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = Field("development", description="Environment: dev/staging/prod")
    debug: bool = Field(False, description="Enable debug mode")
    openai_api_key: str = Field(..., description="OpenAI API Key")

    # Image cache settings
    image_cache_enabled: bool = Field(
        False, description="Enable image analysis caching"
    )
    hash_threshold: int = Field(
        22, description="Perceptual hash similarity threshold (0-64)"
    )

    # Database settings
    database_url: str = Field(..., description="Database URL for PostgreSQL")

    postgres_db: str = Field("chatbotdb", description="PostgreSQL database name")
    postgres_user: str = Field("chatbotuser", description="PostgreSQL username")
    postgres_password: str = Field("chatbotpassword", description="PostgreSQL password")
    postgres_host: str = Field("postgres", description="PostgreSQL host")
    postgres_port: int = Field(5432, description="PostgreSQL port")

    # API settings
    defteros_api_url: str = Field(..., description="Defteros API base URL")
    shop_url: str = Field("https://chatbot.com/products", description="ChatBot Shop URL")

    # cors settings
    cors_allowed_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8000",
            "https://ci.chatbot.com",
            "https://darktheme-chatbot.visionsdemo.com",
            "https://visions.ngrok.io/",
            "https://chatbot.com",
            "https://thechatbot-qa.visionsdemo.com/",
        ],
        description="Allowed CORS origins",
    )
    cors_allowed_methods: list[str] = Field(
        default=["GET", "POST", "DELETE", "OPTIONS"], description="Allowed CORS methods"
    )

    # temp settings to pull data from prod:
    embeddings_database_url: str = Field(
        ...,
        description="Database URL for embeddings DB (used by ChatBotContentSearchService)"
    )
    defteros_prod_api_url: str = Field(..., description="To pull recipes/mixlist from prod.")

    # embeddings syncing and cleanup related config
    sync_embeddings: bool = Field(default=False, description="embedding sync status")
    cleanup_embeddings: bool = Field(default=False, description="embedding sync status")
    create_device_docs_embeddings: bool = Field(
        default=False, description="run device docs embeddings creation scripts"
    )
    scrap_chatbot_website: bool = Field(
        default=False, description="scrape ChatBot website on startup"
    )

    class Config:
        env_file = ".env"
        extra = "ignore"  # Prevent crashing on unused env vars


@lru_cache
def get_settings() -> Settings:
    return Settings.model_validate({})
