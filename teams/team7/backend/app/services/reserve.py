"""Reserve Coach service layer (SCRUM-9, SCRUM-12, SCRUM-13).

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
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.base import _utcnow
from app.models.coach_availability import CoachAvailability
from app.models.coach_profile import CoachProfile
from app.models.coach_rating import CoachRating
from app.schemas.reserve import CoachProfileUpsertRequest, SlotInput

# ---------------------------------------------------------------------------
# Coach-profile functions (SCRUM-9)
# ---------------------------------------------------------------------------


def _coach_profile_payload_from_row(row: dict) -> dict:
    """Convert a SQLAlchemy mapping row to the public coach-profile payload."""

    avg_rating = row.get("avg_rating")
    rating_count = row.get("rating_count")

    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "bio": row["bio"],
        "specialties": row["specialties"],
        "hourly_rate": row["hourly_rate"],
        "years_experience": row["years_experience"],
        "is_online": row["is_online"],
        "avg_rating": float(avg_rating) if avg_rating is not None else None,
        "rating_count": int(rating_count or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


async def list_coach_profiles(
    session: AsyncSession,
    *,
    specialty: str | None = None,
    min_rating: float | None = None,
) -> list[dict]:
    """List active coach profiles with optional specialty/min-rating filters."""

    stmt = (
        select(
            CoachProfile.id,
            CoachProfile.user_id,
            CoachProfile.bio,
            CoachProfile.specialties,
            CoachProfile.hourly_rate,
            CoachProfile.years_experience,
            CoachProfile.is_online,
            CoachProfile.created_at,
            CoachProfile.updated_at,
            func.avg(CoachRating.rating).label("avg_rating"),
            func.count(CoachRating.id).label("rating_count"),
        )
        .outerjoin(
            CoachRating,
            (CoachRating.coach_user_id == CoachProfile.user_id)
            & (CoachRating.is_deleted.is_(False)),
        )
        .where(CoachProfile.is_deleted.is_(False))
        .group_by(
            CoachProfile.id,
            CoachProfile.user_id,
            CoachProfile.bio,
            CoachProfile.specialties,
            CoachProfile.hourly_rate,
            CoachProfile.years_experience,
            CoachProfile.is_online,
            CoachProfile.created_at,
            CoachProfile.updated_at,
        )
        .order_by(CoachProfile.id.asc())
    )

    result = await session.execute(stmt)
    rows = [
        _coach_profile_payload_from_row(dict(r))
        for r in result.mappings().all()
    ]

    if specialty is not None:
        wanted = specialty.strip().lower()
        rows = [
            row
            for row in rows
            if row["specialties"]
            and any(s.lower() == wanted for s in row["specialties"])
        ]

    if min_rating is not None:
        rows = [
            row for row in rows if row["avg_rating"] is not None and row["avg_rating"] >= min_rating
        ]

    return rows


async def get_coach_profile(session: AsyncSession, coach_user_id: int) -> dict | None:
    """Return one active coach profile with rating aggregates or ``None``."""

    rows = await list_coach_profiles(session)
    for row in rows:
        if row["user_id"] == coach_user_id:
            return row
    return None


async def upsert_coach_profile(
    session: AsyncSession,
    *,
    coach_user_id: int,
    payload: CoachProfileUpsertRequest,
) -> dict:
    """Create or update the coach profile for ``coach_user_id``."""

    stmt = select(CoachProfile).where(CoachProfile.user_id == coach_user_id)
    existing = (await session.execute(stmt)).scalar_one_or_none()

    if existing is None:
        if payload.hourly_rate is None:
            raise ValueError("hourly_rate is required when creating a coach profile")

        existing = CoachProfile(
            user_id=coach_user_id,
            bio=payload.bio,
            specialties=payload.specialties,
            hourly_rate=payload.hourly_rate,
            years_experience=payload.years_experience,
            is_online=payload.is_online if payload.is_online is not None else False,
            is_deleted=False,
        )
        session.add(existing)
    else:
        existing.is_deleted = False
        if payload.bio is not None:
            existing.bio = payload.bio
        if payload.specialties is not None:
            existing.specialties = payload.specialties
        if payload.hourly_rate is not None:
            existing.hourly_rate = payload.hourly_rate
        if payload.years_experience is not None:
            existing.years_experience = payload.years_experience
        if payload.is_online is not None:
            existing.is_online = payload.is_online
        existing.updated_at = _utcnow()

    await session.commit()

    row = await get_coach_profile(session, coach_user_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load coach profile after upsert.",
        )
    return row


# ---------------------------------------------------------------------------
# Availability functions (SCRUM-9)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Rating functions (SCRUM-13)
# ---------------------------------------------------------------------------


async def create_rating(
    session: AsyncSession,
    *,
    coach_user_id: int,
    user_id: int,
    rating: int,
    comment: str | None = None,
) -> CoachRating:
    """Create a rating for a coach left by a user.

    Raises ``HTTPException(409)`` if the user has already rated this coach
    (unique constraint on ``(coach_user_id, user_id)``) or if the coach
    profile does not exist (404). The caller is responsible for ensuring
    the user is not rating themselves before calling this function.
    """

    if not await coach_profile_exists(session, coach_user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coach not found.",
        )

    row = CoachRating(
        coach_user_id=coach_user_id,
        user_id=user_id,
        rating=rating,
        comment=comment,
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already rated this coach.",
        ) from None

    await session.refresh(row)
    return row


async def list_ratings(
    session: AsyncSession,
    coach_user_id: int,
) -> Sequence[CoachRating]:
    """Return all active ratings for a coach, newest first.

    Soft-deleted ratings are excluded.
    """

    stmt = (
        select(CoachRating)
        .where(
            CoachRating.coach_user_id == coach_user_id,
            CoachRating.is_deleted.is_(False),
        )
        .order_by(CoachRating.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
