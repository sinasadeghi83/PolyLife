"""``coach_availability`` ORM model.

A coach's bookable time slot. The slot is either ``open``, ``booked`` by an
``appointment``, or ``blocked`` by the coach. ``coach_user_id`` is a real FK
to ``coach_profile.user_id`` inside Team 7's database (Core is a separate
DB and we have no FK there).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import CommonBase


class CoachAvailability(CommonBase):
    """A bookable time slot offered by a coach."""

    __tablename__ = "coach_availability"

    coach_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("coach_profile.user_id", name="fk_coach_availability_coach_user_id"),
        nullable=False,
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'open'"),
    )

    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ck_coach_availability_end_after_start"),
        CheckConstraint(
            "status IN ('open', 'booked', 'blocked')",
            name="ck_coach_availability_status",
        ),
        Index("ix_coach_availability_coach_start", "coach_user_id", "start_at"),
        Index("ix_coach_availability_status", "status"),
    )
