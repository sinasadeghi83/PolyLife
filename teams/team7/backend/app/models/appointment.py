"""``appointment`` ORM model.

A confirmed booking tying a user to a coach's ``coach_availability`` slot.
The DBML marks ``availability_id`` as ``unique`` so each availability
row can be booked at most once; we enforce both a UNIQUE constraint and
a FK to ``coach_availability.id``.
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import CommonBase


class Appointment(CommonBase):
    """A booking of one availability slot by one user."""

    __tablename__ = "appointment"

    coach_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("coach_profile.user_id", name="fk_appointment_coach_user_id"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    availability_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("coach_availability.id", name="fk_appointment_availability_id"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'confirmed'"),
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'cancelled', 'completed', 'no_show')",
            name="ck_appointment_status",
        ),
        Index("ix_appointment_user_id", "user_id"),
        Index("ix_appointment_coach_user_id", "coach_user_id"),
        Index("ix_appointment_status", "status"),
    )
