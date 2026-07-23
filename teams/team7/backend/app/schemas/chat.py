"""Schemas for the chat with-coach service (SCRUM-8).

These Pydantic models define the public request/response shape for
``/api/chat/threads``. They are intentionally separate from the SQLAlchemy
ORM models so the wire contract can evolve independently of the schema.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatThreadRead(BaseModel):
    """Public shape of a single chat thread."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    coach_user_id: int
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime | None


class ChatThreadCreateRequest(BaseModel):
    """POST body for opening (or returning) a thread with a coach."""

    coach_user_id: int = Field(gt=0, description="``X-User-Id`` of the coach.")


class ChatThreadListResponse(BaseModel):
    """Envelope for ``GET /api/chat/threads``."""

    data: list[ChatThreadRead]


class ChatThreadResponse(BaseModel):
    """Envelope for ``POST /api/chat/threads``."""

    data: ChatThreadRead
