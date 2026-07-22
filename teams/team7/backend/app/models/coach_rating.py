"""``coach_rating`` ORM model.

A 1-5 rating + optional comment left by a user on a coach. The pair
``(coach_user_id, user_id)`` is unique — one rating per rater per coach —
and ``rating`` is constrained to 1..5 at the database level.
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    SmallInteger,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import CommonBase


class CoachRating(CommonBase):
    """A user's rating (1-5) of a coach."""

    __tablename__ = "coach_rating"

    coach_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("coach_profile.user_id", name="fk_coach_rating_coach_user_id"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_coach_rating_range"),
        UniqueConstraint(
            "coach_user_id", "user_id", name="uq_coach_rating_coach_user"
        ),
        Index("ix_coach_rating_coach_user_id", "coach_user_id"),
    )
