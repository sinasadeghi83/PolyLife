"""``message_attachment`` ORM model.

Optional binary file (image, PDF, plan) attached to a ``chat_message``.
We store the URL only — the bytes live in object storage or a local volume.
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import CommonBase


class MessageAttachment(CommonBase):
    """An attachment linked to a single chat message."""

    __tablename__ = "message_attachment"

    message_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_message.id", name="fk_message_attachment_message_id"),
        nullable=False,
    )
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (Index("ix_message_attachment_message_id", "message_id"),)
