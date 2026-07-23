"""Reserve Coach service layer (SCRUM-9, SCRUM-12).

Pure database functions for the Reserve Coach availability and appointment
endpoints. The HTTP layer in ``app.api.reserve`` depends on these so router
tests can stay focused on request/response shape and authorisation rules.

Availability status lifecycle:
- New slots are created with ``status='open'``.
- A coach may toggle a slot to ``status='blocked'`` (or back to ``open``).
- ``status='booked'`` is set atomically by ``book_slot`` (SCRUM-12) inside
  the same transaction as the appointment insert; the unique constraint on
  ``appointment.availability_id`` is the database-level guard against
  double-booking — a racing second insert raises ``IntegrityError``.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
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


# ---------------------------------------------------------------------------
# Appointment functions (SCRUM-12)
# ---------------------------------------------------------------------------


async def book_slot(
    session: AsyncSession,
    *,
    user_id: int,
    availability_id: int,
    notes: str | None = None,
) -> Appointment:
    """Atomically book an availability slot for a user.

    Flow:
    1. Fetch the slot and validate it is ``open`` and not soft-deleted.
    2. Reject if the caller is the coach who owns the slot.
    3. Insert the ``appointment`` row and flip the slot to ``booked`` in
       one transaction — the unique constraint on ``availability_id``
       guarantees at most one successful booking even under concurrent
       requests. A racing second insert produces ``IntegrityError`` which
       is caught and re-raised as HTTP 409.

    Raises ``HTTPException`` on 404 (slot not found), 409 (already booked
    or just taken by a concurrent request), and 422 (self-booking).
    """

    slot = await get_active_slot(session, availability_id)
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability slot not found.",
        )
    if slot.status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This slot is not available for booking.",
        )
    if slot.coach_user_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You cannot book your own availability slot.",
        )

    appointment = Appointment(
        coach_user_id=slot.coach_user_id,
        user_id=user_id,
        availability_id=availability_id,
        status="confirmed",
        notes=notes,
    )
    session.add(appointment)
    slot.status = "booked"
    slot.updated_at = _utcnow()

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This slot was just booked by someone else.",
        ) from None

    await session.refresh(appointment)
    return appointment


async def list_appointments(
    session: AsyncSession,
    *,
    caller_id: int,
    status_filter: str | None = None,
    from_dt: datetime | None = None,
) -> Sequence[Appointment]:
    """Return active appointments where the caller is a participant.

    A caller participates as either the regular user (``user_id``) or the
    coach (``coach_user_id``). Optional ``status_filter`` narrows by status;
    optional ``from_dt`` excludes appointments created before that datetime.
    Results are ordered by ``created_at`` descending (newest first).
    """

    stmt = (
        select(Appointment)
        .where(
            Appointment.is_deleted.is_(False),
            or_(
                Appointment.user_id == caller_id,
                Appointment.coach_user_id == caller_id,
            ),
        )
        .order_by(Appointment.created_at.desc())
    )
    if status_filter is not None:
        stmt = stmt.where(Appointment.status == status_filter)
    if from_dt is not None:
        stmt = stmt.where(Appointment.created_at >= from_dt)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_appointment(
    session: AsyncSession, appointment_id: int
) -> Appointment | None:
    """Return the appointment by id if it exists and is not soft-deleted."""

    stmt = select(Appointment).where(
        Appointment.id == appointment_id,
        Appointment.is_deleted.is_(False),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_appointment_status(
    session: AsyncSession,
    appointment: Appointment,
    *,
    new_status: str,
) -> Appointment:
    """Update the status of an appointment and persist the change.

    The caller must verify that they are a participant and that the
    transition makes sense before calling this function.
    """

    appointment.status = new_status
    appointment.updated_at = _utcnow()
    await session.commit()
    await session.refresh(appointment)
    return appointment
