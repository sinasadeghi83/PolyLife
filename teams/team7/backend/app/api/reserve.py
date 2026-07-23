"""Reserve Coach HTTP router (SCRUM-9).

Public, gateway-facing routes are ``/api/reserve/...``; the Nginx layer
prefixes ``/api/`` via ``proxy_pass`` without a URI rewrite, so the
FastAPI router is mounted at ``prefix="/reserve"`` to match the existing
``/chat`` convention. See ``teams/team7/gateway.conf`` and
``app/api/chat.py`` for the precedent.

This router covers the availability management endpoints defined in
SCRUM-9. Appointment booking (SCRUM-12) and ratings (SCRUM-13) belong
to later tickets.

Endpoints:
  GET    /reserve/coaches/{coach_user_id}/availability  — list open slots
  POST   /reserve/coaches/me/availability               — create slots (coach)
  PATCH  /reserve/availability/{slot_id}               — update slot (coach owner)
  DELETE /reserve/availability/{slot_id}               — soft-delete (coach owner)
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import CurrentUser, get_current_user
from app.schemas.reserve import (
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
