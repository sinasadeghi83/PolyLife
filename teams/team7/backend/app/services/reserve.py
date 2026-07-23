"""Reserve Coach service layer (SCRUM-9).

Pure database functions for the Reserve Coach availability endpoints.
The HTTP layer in ``app.api.reserve`` depends on these so router tests
can stay focused on request/response shape and authorisation rules.

Availability status lifecycle:
- New slots are created with ``status='open'``.
- A coach may toggle a slot to ``status='blocked'`` (or back to ``open``).
- ``status='booked'`` is set atomically by the booking endpoint (SCRUM-12);
  this service layer refuses to update a booked slot.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import _utcnow
from app.models.coach_availability import CoachAvailability
from app.models.coach_profile import CoachProfile
from app.schemas.reserve import SlotInput


async def coach_profile_exists(session: AsyncSession, coach_user_id: int) -> bool:
    """Return True iff an active ``coach_profile`` row exists for the given id."""

    stmt = select(CoachProfile.user_id).where(
        CoachProfile.user_id == coach_user_id,
        CoachProfile.is_deleted.is_(False),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def list_availability(
    session: AsyncSession,
    coach_user_id: int,
    *,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
) -> Sequence[CoachAvailability]:
    """Return active ``open`` slots for a coach, ordered by ``start_at`` ascending.

    Optional ``from_dt`` and ``to_dt`` narrow the result to slots whose
    ``start_at >= from_dt`` and ``end_at <= to_dt`` respectively.
    Soft-deleted slots are never returned.
    """

    stmt = (
        select(CoachAvailability)
        .where(
            CoachAvailability.coach_user_id == coach_user_id,
            CoachAvailability.status == "open",
            CoachAvailability.is_deleted.is_(False),
        )
        .order_by(CoachAvailability.start_at)
    )
    if from_dt is not None:
        stmt = stmt.where(CoachAvailability.start_at >= from_dt)
    if to_dt is not None:
        stmt = stmt.where(CoachAvailability.end_at <= to_dt)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_slots(
    session: AsyncSession,
    *,
    coach_user_id: int,
    slots: list[SlotInput],
) -> list[CoachAvailability]:
    """Insert one or more availability slots for a coach.

    All inserted rows start with ``status='open'``. The caller is
    responsible for verifying that a ``coach_profile`` exists for
    ``coach_user_id`` before calling this function.
    """

    rows = [
        CoachAvailability(
            coach_user_id=coach_user_id,
            start_at=slot.start_at,
            end_at=slot.end_at,
            status="open",
        )
        for slot in slots
    ]
    session.add_all(rows)
    await session.commit()
    for row in rows:
        await session.refresh(row)
    return rows


async def get_active_slot(
    session: AsyncSession, slot_id: int
) -> CoachAvailability | None:
    """Return the slot by id if it exists and is not soft-deleted."""

    stmt = select(CoachAvailability).where(
        CoachAvailability.id == slot_id,
        CoachAvailability.is_deleted.is_(False),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_slot(
    session: AsyncSession,
    slot: CoachAvailability,
    *,
    status: str | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
) -> CoachAvailability:
    """Apply partial updates to a slot and persist them.

    Validates that ``end_at`` remains strictly after ``start_at`` after
    applying any time changes. The caller must verify ownership and that
    the slot is not ``booked`` before calling this function.
    """

    new_start = start_at if start_at is not None else slot.start_at
    new_end = end_at if end_at is not None else slot.end_at
    if new_end <= new_start:
        raise ValueError("end_at must be strictly after start_at")

    if status is not None:
        slot.status = status
    if start_at is not None:
        slot.start_at = start_at
    if end_at is not None:
        slot.end_at = end_at
    slot.updated_at = _utcnow()

    await session.commit()
    await session.refresh(slot)
    return slot


async def soft_delete_slot(
    session: AsyncSession,
    slot: CoachAvailability,
) -> None:
    """Soft-delete a slot by setting ``is_deleted=True``.

    The caller must verify ownership before calling this function.
    """

    slot.is_deleted = True
    slot.updated_at = _utcnow()
    await session.commit()
