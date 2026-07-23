"""Schemas for the Reserve Coach service (SCRUM-9, SCRUM-12, SCRUM-13).

These Pydantic models define the public request/response shape for
``/api/reserve/coaches/.../availability``, ``/api/reserve/appointments``,
and ``/api/reserve/coaches/.../ratings``. They are intentionally separate
from the SQLAlchemy ORM models so the wire contract can evolve independently
of the schema.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Availability schemas (SCRUM-9)
# ---------------------------------------------------------------------------

class AvailabilityRead(BaseModel):
    """Public shape of a single availability slot."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    coach_user_id: int
    start_at: datetime
    end_at: datetime
    status: str
    created_at: datetime
    updated_at: datetime | None


class SlotInput(BaseModel):
    """One slot item inside a create-availability request."""

    start_at: datetime
    end_at: datetime

    @model_validator(mode="after")
    def end_after_start(self) -> SlotInput:
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be strictly after start_at")
        return self


class AvailabilityCreateRequest(BaseModel):
    """POST body for creating one or more availability slots."""

    slots: list[SlotInput] = Field(min_length=1, description="At least one slot required.")


class AvailabilityCreateResponse(BaseModel):
    """Envelope for ``POST /api/reserve/coaches/me/availability``."""

    data: list[AvailabilityRead]


class AvailabilityListResponse(BaseModel):
    """Envelope for ``GET /api/reserve/coaches/{coach_user_id}/availability``."""

    data: list[AvailabilityRead]


class AvailabilityUpdateRequest(BaseModel):
    """PATCH body for updating a slot.

    All fields are optional; at least one must be provided. A coach may
    toggle the slot's status between ``open`` and ``blocked``. Setting
    status to ``booked`` is not allowed here — that happens atomically
    through the booking endpoint (SCRUM-12).
    """

    status: Literal["open", "blocked"] | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> AvailabilityUpdateRequest:
        if self.status is None and self.start_at is None and self.end_at is None:
            raise ValueError("At least one of status, start_at, or end_at must be provided.")
        return self


class AvailabilityResponse(BaseModel):
    """Envelope for a single-slot response (PATCH)."""

    data: AvailabilityRead


# ---------------------------------------------------------------------------
# Appointment schemas (SCRUM-12)
# ---------------------------------------------------------------------------


class AppointmentRead(BaseModel):
    """Public shape of a single appointment."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    coach_user_id: int
    user_id: int
    availability_id: int
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime | None


class AppointmentCreateRequest(BaseModel):
    """POST body for booking an availability slot."""

    availability_id: int = Field(gt=0, description="ID of the open slot to book.")
    notes: str | None = None


class AppointmentResponse(BaseModel):
    """Envelope for a single appointment response."""

    data: AppointmentRead


class AppointmentListResponse(BaseModel):
    """Envelope for ``GET /api/reserve/appointments``."""

    data: list[AppointmentRead]


class AppointmentUpdateRequest(BaseModel):
    """PATCH body for updating an appointment status.

    Only terminal or rescheduled states are accepted here. ``confirmed``
    is the initial state set at booking time and cannot be re-applied.
    """

    status: Literal["cancelled", "completed", "no_show"]


# ---------------------------------------------------------------------------
# Rating schemas (SCRUM-13)
# ---------------------------------------------------------------------------


class RatingRead(BaseModel):
    """Public shape of a single coach rating."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    coach_user_id: int
    user_id: int
    rating: int
    comment: str | None
    created_at: datetime
    updated_at: datetime | None


class RatingCreateRequest(BaseModel):
    """POST body for leaving a rating on a coach."""

    rating: int = Field(ge=1, le=5, description="Rating value between 1 and 5.")
    comment: str | None = None


class RatingResponse(BaseModel):
    """Envelope for a single rating response."""

    data: RatingRead


class RatingListResponse(BaseModel):
    """Envelope for ``GET /api/reserve/coaches/{coach_user_id}/ratings``."""

    data: list[RatingRead]
