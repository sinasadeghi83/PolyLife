"""ORM models for the team-7 backend.

Importing this package populates :data:`Base.metadata` with exactly the
seven application tables defined in ``teams/team7/.agents/03_database_design.md``:

- ``coach_profile``
- ``coach_availability``
- ``appointment``
- ``chat_thread``
- ``chat_message``
- ``message_attachment``
- ``coach_rating``

Alembic imports ``Base.metadata`` as ``target_metadata`` in
``alembic/env.py`` to autogenerate / verify migrations.
"""

from __future__ import annotations

from app.models.appointment import Appointment
from app.models.base import CommonBase
from app.models.chat_message import ChatMessage
from app.models.chat_thread import ChatThread
from app.models.coach_availability import CoachAvailability
from app.models.coach_profile import CoachProfile
from app.models.coach_rating import CoachRating
from app.models.message_attachment import MessageAttachment

Base = CommonBase

__all__ = [
    "Appointment",
    "Base",
    "ChatMessage",
    "ChatThread",
    "CoachAvailability",
    "CoachProfile",
    "CoachRating",
    "MessageAttachment",
]
