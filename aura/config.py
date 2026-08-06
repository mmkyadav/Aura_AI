"""
aura/config.py
--------------
Centralized configuration management for Aura using Pydantic Settings.
All LLM models are routed through OpenRouter.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Config
    APP_NAME: str = "Aura AI Assistant"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # API Keys (OpenRouter as primary LLM gateway)
    OPENROUTER_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    SERPAPI_API_KEY: str = ""

    # OpenRouter API Endpoint
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # LLM Settings (OpenRouter model identifiers)
    PRIMARY_MODEL: str = "openai/gpt-4o-mini"
    FALLBACK_MODEL: str = "google/gemini-2.5-flash"
    RETRY_MODEL: str = "deepseek/deepseek-chat"

    # Optional alias mappings for legacy fallback fields
    FALLBACK_MODEL_1: str = ""
    FALLBACK_MODEL_2: str = ""

    # Database Settings
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/aura_db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "aura_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # Memory & Cache Limits
    CONTEXT_WINDOW_LIMIT: int = 4000
    CACHE_SIMILARITY_THRESHOLD: float = 0.92
    FACT_SIMILARITY_THRESHOLD: float = 0.75

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def fallback_1(self) -> str:
        """Return primary fallback model (FALLBACK_MODEL or FALLBACK_MODEL_1)."""
        return self.FALLBACK_MODEL or self.FALLBACK_MODEL_1 or "google/gemini-2.5-flash"

    @property
    def fallback_2(self) -> str:
        """Return secondary retry model (RETRY_MODEL or FALLBACK_MODEL_2)."""
        return self.RETRY_MODEL or self.FALLBACK_MODEL_2 or "deepseek/deepseek-chat"

    @property
    def sync_database_url(self) -> str:
        """Returns standard PostgreSQL connection string for psycopg3 sync connections."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def async_database_url(self) -> str:
        """Returns async PostgreSQL connection string for psycopg3 async connections."""
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
