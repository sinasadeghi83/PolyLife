"""Reserve Coach HTTP router (SCRUM-9, SCRUM-12).

Public, gateway-facing routes are ``/api/reserve/...``; the Nginx layer
prefixes ``/api/`` via ``proxy_pass`` without a URI rewrite, so the
FastAPI router is mounted at ``prefix="/reserve"`` to match the existing
``/chat`` convention. See ``teams/team7/gateway.conf`` and
``app/api/chat.py`` for the precedent.

Endpoints (SCRUM-9 — availability):
  GET    /reserve/coaches/{coach_user_id}/availability  — list open slots
  POST   /reserve/coaches/me/availability               — create slots (coach)
  PATCH  /reserve/availability/{slot_id}               — update slot (coach owner)
  DELETE /reserve/availability/{slot_id}               — soft-delete (coach owner)

Endpoints (SCRUM-12 — appointments):
  POST   /reserve/appointments                         — book a slot (user)
  GET    /reserve/appointments                         — list own appointments
  GET    /reserve/appointments/{appointment_id}        — get appointment detail
  PATCH  /reserve/appointments/{appointment_id}        — update status (participant)
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import CurrentUser, get_current_user
from app.schemas.reserve import (
    AppointmentCreateRequest,
    AppointmentListResponse,
    AppointmentRead,
    AppointmentResponse,
    AppointmentUpdateRequest,
    AvailabilityCreateRequest,
    AvailabilityCreateResponse,
    AvailabilityListResponse,
    AvailabilityRead,
    AvailabilityResponse,
    AvailabilityUpdateRequest,
)
from app.services import reserve as reserve_service

router = APIRouter(prefix="/reserve", tags=["reserve"])


@router.get(
    "/coaches/{coach_user_id}/availability",
    response_model=AvailabilityListResponse,
)
async def list_availability(
    coach_user_id: int,
    from_dt: datetime | None = Query(default=None, alias="from"),  # noqa: B008
    to_dt: datetime | None = Query(default=None, alias="to"),  # noqa: B008
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> AvailabilityListResponse:
    """List open availability slots for a coach.

    Optional query params ``from`` and ``to`` filter by the slot's
    ``start_at >= from`` and ``end_at <= to``.
    """

    rows = await reserve_service.list_availability(
        session, coach_user_id, from_dt=from_dt, to_dt=to_dt
    )
    return AvailabilityListResponse(
        data=[AvailabilityRead.model_validate(r) for r in rows]
    )


@router.post(
    "/coaches/me/availability",
    status_code=status.HTTP_201_CREATED,
    response_model=AvailabilityCreateResponse,
)
async def create_availability(
    payload: AvailabilityCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> AvailabilityCreateResponse:
    """Coach creates one or more availability slots for themselves.

    The caller must have an active ``coach_profile`` row. All created
    slots start with ``status='open'``.
    """

    if not await reserve_service.coach_profile_exists(session, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No coach profile found for the current user.",
        )

    rows = await reserve_service.create_slots(
        session, coach_user_id=current_user.id, slots=payload.slots
    )
    return AvailabilityCreateResponse(
        data=[AvailabilityRead.model_validate(r) for r in rows]
    )


@router.patch(
    "/availability/{slot_id}",
    response_model=AvailabilityResponse,
)
async def update_availability(
    slot_id: int,
    payload: AvailabilityUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> AvailabilityResponse:
    """Coach updates their own availability slot.

    Returns 404 if the slot does not exist or is soft-deleted.
    Returns 403 if the caller is not the slot owner.
    Returns 409 if the slot is already ``booked``.
    """

    slot = await reserve_service.get_active_slot(session, slot_id)
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability slot not found.",
        )
    if slot.coach_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this availability slot.",
        )
    if slot.status == "booked":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot modify a slot that is already booked.",
        )

    try:
        updated = await reserve_service.update_slot(
            session,
            slot,
            status=payload.status,
            start_at=payload.start_at,
            end_at=payload.end_at,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return AvailabilityResponse(data=AvailabilityRead.model_validate(updated))


@router.delete(
    "/availability/{slot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_availability(
    slot_id: int,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> None:
    """Coach soft-deletes their own availability slot.

    Returns 404 if the slot does not exist or is soft-deleted.
    Returns 403 if the caller is not the slot owner.
    """

    slot = await reserve_service.get_active_slot(session, slot_id)
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability slot not found.",
        )
    if slot.coach_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this availability slot.",
        )

    await reserve_service.soft_delete_slot(session, slot)


# ---------------------------------------------------------------------------
# Appointment endpoints (SCRUM-12)
# ---------------------------------------------------------------------------


@router.post(
    "/appointments",
    status_code=status.HTTP_201_CREATED,
    response_model=AppointmentResponse,
)
async def book_appointment(
    payload: AppointmentCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> AppointmentResponse:
    """Book an open availability slot.

    Atomically marks the slot ``booked`` and creates a ``confirmed``
    appointment. Returns 404 if the slot does not exist, 409 if it is
    already taken (including concurrent double-booking), and 422 if the
    caller tries to book their own slot.
    """

    appointment = await reserve_service.book_slot(
        session,
        user_id=current_user.id,
        availability_id=payload.availability_id,
        notes=payload.notes,
    )
    return AppointmentResponse(data=AppointmentRead.model_validate(appointment))


@router.get("/appointments", response_model=AppointmentListResponse)
async def list_appointments(
    status_filter: str | None = Query(default=None, alias="status"),  # noqa: B008
    from_dt: datetime | None = Query(default=None, alias="from"),  # noqa: B008
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> AppointmentListResponse:
    """List appointments where the current user is a participant.

    Optional query params:
    - ``status`` — filter by appointment status (e.g. ``confirmed``).
    - ``from``   — exclude appointments created before this datetime.
    """

    rows = await reserve_service.list_appointments(
        session,
        caller_id=current_user.id,
        status_filter=status_filter,
        from_dt=from_dt,
    )
    return AppointmentListResponse(
        data=[AppointmentRead.model_validate(r) for r in rows]
    )


@router.get("/appointments/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: int,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> AppointmentResponse:
    """Get the detail of a single appointment.

    Returns 404 if the appointment does not exist or is soft-deleted.
    Returns 403 if the caller is not a participant.
    """

    appointment = await reserve_service.get_appointment(session, appointment_id)
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found.",
        )
    if appointment.user_id != current_user.id and appointment.coach_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this appointment.",
        )
    return AppointmentResponse(data=AppointmentRead.model_validate(appointment))


@router.patch("/appointments/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> AppointmentResponse:
    """Update the status of an appointment.

    Allowed target statuses: ``cancelled``, ``completed``, ``no_show``.
    Returns 404 if the appointment does not exist or is soft-deleted.
    Returns 403 if the caller is not a participant.
    Returns 409 if the appointment is already in a terminal state.
    """

    appointment = await reserve_service.get_appointment(session, appointment_id)
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found.",
        )
    if appointment.user_id != current_user.id and appointment.coach_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this appointment.",
        )
    if appointment.status in ("cancelled", "completed", "no_show"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Appointment is already in terminal state '{appointment.status}'.",
        )

    updated = await reserve_service.update_appointment_status(
        session, appointment, new_status=payload.status
    )
    return AppointmentResponse(data=AppointmentRead.model_validate(updated))
