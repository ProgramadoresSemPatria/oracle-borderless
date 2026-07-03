"""Configuração central da aplicação, lida do ambiente (.env) via pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Todas as variáveis de ambiente do Oracle Borderless."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Ambiente ---
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    ENABLE_SCHEDULER: bool = True

    # --- Aplicação ---
    APP_NAME: str = "Oracle Borderless"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # --- Banco de dados ---
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "oracle"
    DB_PASSWORD: str = "oracle"
    DB_NAME: str = "oracle_borderless"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

    # --- Base de conhecimento: Notion via MCP ---
    NOTION_MCP_URL: str | None = None
    NOTION_MCP_TOKEN: str | None = None

    # --- LLM do oráculo (Claude ou GPT, selecionável) ---
    LLM_PROVIDER: Literal["anthropic", "openai"] = "anthropic"
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-opus-4-8"
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o"

    @property
    def database_url_async(self) -> str:
        """URL do engine assíncrono (asyncpg)."""
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def database_url_sync(self) -> str:
        """URL do engine síncrono (psycopg) — usado pelo jobstore do APScheduler."""
        return (
            f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    """Instância única (cacheada) das settings."""
    return Settings()


settings = get_settings()
