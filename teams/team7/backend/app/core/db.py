"""Async SQLAlchemy engine + session factory.

`get_db` is the FastAPI dependency that yields an `AsyncSession` bound
to the team's `DATABASE_URL`. Sessions are short-lived and scoped to a
single request.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding an `AsyncSession` per request."""
    async with AsyncSessionLocal() as session:
        yield session
