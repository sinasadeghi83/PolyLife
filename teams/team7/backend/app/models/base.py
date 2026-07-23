"""Shared declarative base and audit columns for every team-7 table.

Every application table defined for SCRUM-6 inherits from :class:`CommonBase`,
which provides the four audit columns mandated by the team's schema design
(see ``teams/team7/.agents/03_database_design.md`` §1):

- ``id``          ``BIGINT`` identity primary key
- ``created_at``  ``TIMESTAMP NOT NULL DEFAULT NOW()``
- ``updated_at``  ``TIMESTAMP`` (nullable; no default)
- ``is_deleted``  ``BOOLEAN  NOT NULL DEFAULT FALSE``

``CommonBase`` is the single source of truth for the ORM schema; Alembic
imports its ``metadata`` attribute as ``target_metadata`` in ``alembic/env.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Production uses PostgreSQL ``BIGINT IDENTITY``. SQLite needs ``INTEGER``
# as the column type plus the special ``INTEGER PRIMARY KEY`` syntax for
# autoincrement; the with_variant below keeps the same model definition
# usable against both backends.
ID_TYPE: Any = BigInteger().with_variant(Integer, "sqlite")


def _utcnow() -> datetime:
    """Timezone-naive UTC ``now()`` matching the DBML ``timestamp`` columns."""

    return datetime.now(UTC).replace(tzinfo=None)


class CommonBase(DeclarativeBase):
    """Declarative base for all team-7 ORM models.

    Subclasses inherit four audit columns from this base. The columns use
    SQLAlchemy 2.x typed mappings (``Mapped[...]`` + ``mapped_column``) so
    IDEs and mypy can infer types directly from the class body.

    Timestamp columns are emitted as PostgreSQL ``TIMESTAMP WITHOUT TIME ZONE``
    (SQLAlchemy ``DateTime`` default), matching the DBML which says
    ``timestamp``, not ``timestamptz``.

    The ``created_at`` default is applied at the Python level so the same
    model works against PostgreSQL and SQLite (the in-memory test backend
    used by SCRUM-8). The production migration keeps the equivalent
    server-side default.
    """

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        default=_utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
