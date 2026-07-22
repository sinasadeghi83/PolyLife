"""Application settings.

Reads configuration from environment variables (and an optional `.env`
file in `teams/team7/`, mirrored from `teams/team7/.env.example` by
`run.sh`). All secrets and URLs MUST come from here — never hardcode.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the team-7 backend."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(
        default="postgres://team7_user:***@db:5432/team7",
        description=(
            "Full SQLAlchemy connection string. Async runtimes (Alembic, "
            "the FastAPI app) consume ``database_url_async`` so the "
            "asyncpg driver prefix is added automatically."
        ),
    )

    @property
    def database_url_async(self) -> str:
        """Return ``database_url`` coerced to ``postgresql+asyncpg://``.

        SQLAlchemy's async engine refuses bare ``postgres://`` /
        ``postgresql://`` URLs because it cannot infer the driver. The
        async runtime (Alembic + FastAPI) must use this property instead
        of ``database_url`` directly.
        """
        url = self.database_url
        if url.startswith("postgresql+asyncpg://"):
            return url
        if url.startswith("postgres://"):
            return "postgresql+asyncpg://" + url[len("postgres://") :]
        if url.startswith("postgresql://"):
            return "postgresql+asyncpg://" + url[len("postgresql://") :]
        return url

    core_base_url: str = Field(
        default="http://core:8000",
        description="Base URL of the PolyLife core service (used for forward-auth).",
    )

    url_redis: str = Field(
        default="redis://redis:6379/0",
        description="Redis connection URL used by the chat fan-out and rate limiter.",
    )

    log_level: str = Field(
        default="info",
        description="Application log level (debug/info/warning/error).",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor (FastAPI dependency-friendly)."""
    return Settings()


settings = get_settings()
