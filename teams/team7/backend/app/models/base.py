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

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class CommonBase(DeclarativeBase):
    """Declarative base for all team-7 ORM models.

    Subclasses inherit four audit columns from this base. The columns use
    SQLAlchemy 2.x typed mappings (``Mapped[...]`` + ``mapped_column``) so
    IDEs and mypy can infer types directly from the class body.

    Timestamp columns are emitted as PostgreSQL ``TIMESTAMP WITHOUT TIME ZONE``
    (SQLAlchemy ``DateTime`` default), matching the DBML which says
    ``timestamp``, not ``timestamptz``.
    """

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("NOW()"),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
