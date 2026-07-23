"""``chat_message`` ORM model.

A single message inside a ``chat_thread``. ``sender_user_id`` is whichever
party of the thread (user or coach) sent the message; we don't FK it to
``coach_profile.user_id`` because the sender can also be the regular user.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import CommonBase, _utcnow


class ChatMessage(CommonBase):
    """One message in a chat thread."""

    __tablename__ = "chat_message"

    thread_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_thread.id", name="fk_chat_message_thread_id"),
        nullable=False,
    )
    sender_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        default=_utcnow,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_chat_message_thread_id", "thread_id"),
        Index("ix_chat_message_thread_sent", "thread_id", "sent_at"),
        Index("ix_chat_message_sender_user_id", "sender_user_id"),
    )
