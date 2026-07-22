"""``chat_thread`` ORM model.

One-to-one conversation between a regular user and a coach. A pair
``(user_id, coach_user_id)`` is unique — there is at most one thread per
``user <-> coach`` pair.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import CommonBase


class ChatThread(CommonBase):
    """A 1-to-1 chat thread between a user and a coach."""

    __tablename__ = "chat_thread"

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    coach_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("coach_profile.user_id", name="fk_chat_thread_coach_user_id"),
        nullable=False,
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "coach_user_id", name="uq_chat_thread_user_coach"),
        Index("ix_chat_thread_coach_user_id", "coach_user_id"),
        Index("ix_chat_thread_last_message_at", "last_message_at"),
    )
