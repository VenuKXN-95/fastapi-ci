"""
Application configuration via Pydantic Settings.

All runtime secrets are injected from environment variables (GitHub Secrets in CI).
No secret is ever hardcoded in this file.
"""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------------------------------------------------------------------------
    # Application
    # ---------------------------------------------------------------------------
    APP_NAME: str = Field(default="FastAPI CI Service")
    APP_VERSION: str = Field(default="1.0.0")
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    ALLOWED_ORIGINS: List[str] = Field(default=["*"])

    # ---------------------------------------------------------------------------
    # Security  (injected via GitHub Secrets in CI)
    # ---------------------------------------------------------------------------
    SECRET_KEY: str = Field(default="changeme-in-production")
    JWT_SECRET: str = Field(default="changeme-in-production")
    API_KEY: str = Field(default="changeme-in-production")

    # ---------------------------------------------------------------------------
    # External Services  (injected via GitHub Secrets in CI)
    # ---------------------------------------------------------------------------
    DATABASE_URL: str = Field(default="sqlite:///./test.db")
    POSTGRES_URI: str = Field(default="")
    MONGODB_URI: str = Field(default="")
    OPENAI_API_KEY: str = Field(default="")

    # ---------------------------------------------------------------------------
    # Server
    # ---------------------------------------------------------------------------
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    WORKERS: int = Field(default=1)


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


settings: Settings = get_settings()
