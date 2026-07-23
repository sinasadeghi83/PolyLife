"""Shared pytest fixtures.

The ``client`` fixture serves the in-process ASGI app through httpx for
fast HTTP-level tests. ``db_session`` + ``db_engine`` fixtures create a
per-test in-memory SQLite database backed by the SQLAlchemy ``Base``
metadata so route tests can exercise persistence without a real
PostgreSQL container. ``make_coach`` is a small helper that inserts a
``CoachProfile`` for FK targets; ``override_db`` installs the per-test
session as the FastAPI ``get_db`` dependency.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Awaitable, Callable
from decimal import Decimal

# Point the app at an in-memory SQLite before any of the application's
# modules import `app.core.config` / `app.core.db` (both create their
# engine at import time using ``settings.database_url``).
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("URL_REDIS", "redis://localhost:6379/0")
os.environ.setdefault("CORE_BASE_URL", "http://core:8000")
os.environ.setdefault("LOG_LEVEL", "info")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.db import get_db
from app.main import app
from app.models import Base
from app.models.coach_profile import CoachProfile


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """HTTPX async client bound to the in-process FastAPI app."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_engine() -> AsyncIterator:
    """Per-test in-memory SQLite engine with the team-7 metadata created."""

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncIterator[AsyncSession]:  # type: ignore[no-untyped-def]
    """Function-scoped async session rolled back at the end of the test."""

    session_factory = async_sessionmaker(
        bind=db_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def make_coach(
    db_session: AsyncSession,
) -> Callable[..., Awaitable[CoachProfile]]:  # type: ignore[no-untyped-def]
    """Factory that inserts a ``CoachProfile`` row for use as an FK target."""

    counter = {"n": 0}

    async def _factory(*, user_id: int | None = None, is_deleted: bool = False) -> CoachProfile:
        counter["n"] += 1
        if user_id is None:
            user_id = 1000 + counter["n"]
        profile = CoachProfile(
            user_id=user_id,
            hourly_rate=Decimal("0"),
            is_deleted=is_deleted,
        )
        db_session.add(profile)
        await db_session.flush()
        return profile

    return _factory


@pytest_asyncio.fixture
async def override_db(db_session: AsyncSession) -> AsyncIterator[AsyncSession]:
    """Install the per-test session as the FastAPI ``get_db`` dependency."""

    async def _override() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override
    try:
        yield db_session
    finally:
        app.dependency_overrides.pop(get_db, None)
