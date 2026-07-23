"""``coach_profile`` ORM model.

Extended information about a coach (the regular user record lives in the
PolyLife core service; we only store the id here as ``user_id``). The id
has no FK to Core because Core lives in a separate database — the DBML
explicitly says so.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, Numeric, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import CommonBase

# The ``specialties`` column stores an array of strings. In production we
# use the real PostgreSQL ``JSONB`` type; in tests (SQLite) we fall back to
# the dialect-agnostic ``JSON`` so the same ORM model can be created
# without spinning up a Postgres container. The wire format is identical.
SpecialtyJSON: Any = JSON().with_variant(JSONB(), "postgresql")


class CoachProfile(CommonBase):
    """Per-coach profile data — bio, specialties, hourly rate, presence flag."""

    __tablename__ = "coach_profile"

    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    specialties: Mapped[list[str] | None] = mapped_column(SpecialtyJSON, nullable=True)
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    years_experience: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    is_online: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        index=True,
    )
