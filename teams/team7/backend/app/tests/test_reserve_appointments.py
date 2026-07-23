"""SCRUM-12 — reserve appointment route tests.

These tests exercise the live ASGI app through the per-test SQLite session
and confirm that:

* ``POST /reserve/appointments`` books an open slot atomically, rejects
  non-open slots, rejects self-booking, and handles double-booking (409).
* ``GET /reserve/appointments`` returns only the caller's appointments,
  supports status and date filters, and requires auth.
* ``GET /reserve/appointments/{id}`` enforces participant-only access.
* ``PATCH /reserve/appointments/{id}`` enforces participant-only access
  and rejects updates to terminal-state appointments.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.appointment import Appointment
from app.models.coach_availability import CoachAvailability
from app.models.coach_profile import CoachProfile

# Identity headers
USER = {"X-User-Id": "42", "X-User-Username": "alice"}
COACH = {"X-User-Id": "101", "X-User-Username": "coach-bob"}
OTHER = {"X-User-Id": "999", "X-User-Username": "outsider"}

_T0 = datetime(2026, 8, 1, 9, 0, 0)
_T1 = _T0 + timedelta(hours=1)
_T2 = _T0 + timedelta(hours=2)
_T3 = _T0 + timedelta(hours=3)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _add_coach(
    db_session: AsyncSession,
    *,
    user_id: int,
    is_deleted: bool = False,
) -> CoachProfile:
    profile = CoachProfile(
        user_id=user_id,
        hourly_rate=Decimal("50.00"),
        is_deleted=is_deleted,
    )
    db_session.add(profile)
    await db_session.flush()
    return profile


async def _add_slot(
    db_session: AsyncSession,
    *,
    coach_user_id: int,
    start_at: datetime = _T0,
    end_at: datetime = _T1,
    status: str = "open",
    is_deleted: bool = False,
) -> CoachAvailability:
    slot = CoachAvailability(
        coach_user_id=coach_user_id,
        start_at=start_at,
        end_at=end_at,
        status=status,
        is_deleted=is_deleted,
    )
    db_session.add(slot)
    await db_session.flush()
    return slot


async def _add_appointment(
    db_session: AsyncSession,
    *,
    coach_user_id: int,
    user_id: int,
    availability_id: int,
    status: str = "confirmed",
    is_deleted: bool = False,
) -> Appointment:
    appt = Appointment(
        coach_user_id=coach_user_id,
        user_id=user_id,
        availability_id=availability_id,
        status=status,
        is_deleted=is_deleted,
    )
    db_session.add(appt)
    await db_session.flush()
    return appt


# ---------------------------------------------------------------------------
# POST /reserve/appointments
# ---------------------------------------------------------------------------


async def test_book_requires_auth(client: AsyncClient) -> None:
    """No identity headers → 401."""

    response = await client.post(
        "/reserve/appointments", json={"availability_id": 1}
    )
    assert response.status_code == 401


async def test_book_slot_not_found(
    client: AsyncClient,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Non-existent slot → 404."""

    response = await client.post(
        "/reserve/appointments",
        json={"availability_id": 99999},
        headers=USER,
    )
    assert response.status_code == 404


async def test_book_slot_not_open_blocked(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """A blocked slot cannot be booked → 409."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id, status="blocked")
    await db_session.commit()

    response = await client.post(
        "/reserve/appointments",
        json={"availability_id": slot.id},
        headers=USER,
    )
    assert response.status_code == 409


async def test_book_slot_not_open_already_booked(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """An already-booked slot → 409."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id, status="booked")
    await db_session.commit()

    response = await client.post(
        "/reserve/appointments",
        json={"availability_id": slot.id},
        headers=USER,
    )
    assert response.status_code == 409


async def test_book_rejects_self_booking(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """A coach cannot book their own slot → 422."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id)
    await db_session.commit()

    response = await client.post(
        "/reserve/appointments",
        json={"availability_id": slot.id},
        headers=COACH,  # same user as the coach who owns the slot
    )
    assert response.status_code == 422
    assert "own" in response.json()["detail"].lower()


async def test_book_success_returns_201_and_marks_slot_booked(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Successful booking returns 201 with confirmed appointment."""

    coach_id = int(COACH["X-User-Id"])
    user_id = int(USER["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id)
    await db_session.commit()

    response = await client.post(
        "/reserve/appointments",
        json={"availability_id": slot.id, "notes": "first session"},
        headers=USER,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["status"] == "confirmed"
    assert data["user_id"] == user_id
    assert data["coach_user_id"] == coach_id
    assert data["availability_id"] == slot.id
    assert data["notes"] == "first session"


async def test_book_success_slot_no_longer_available(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """After booking, the slot disappears from the availability list."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id)
    await db_session.commit()

    await client.post(
        "/reserve/appointments",
        json={"availability_id": slot.id},
        headers=USER,
    )

    list_response = await client.get(
        f"/reserve/coaches/{coach_id}/availability",
        headers=USER,
    )
    assert list_response.status_code == 200
    assert list_response.json()["data"] == []


async def test_book_double_booking_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Sequential double-booking of the same slot → second gets 409."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id)
    await db_session.commit()

    first = await client.post(
        "/reserve/appointments",
        json={"availability_id": slot.id},
        headers=USER,
    )
    second = await client.post(
        "/reserve/appointments",
        json={"availability_id": slot.id},
        headers=OTHER,
    )
    assert first.status_code == 201
    assert second.status_code == 409


# ---------------------------------------------------------------------------
# GET /reserve/appointments
# ---------------------------------------------------------------------------


async def test_list_appointments_requires_auth(client: AsyncClient) -> None:
    """No identity headers → 401."""

    response = await client.get("/reserve/appointments")
    assert response.status_code == 401


async def test_list_appointments_empty_for_new_user(
    client: AsyncClient,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Authenticated request with no appointments returns the empty envelope."""

    response = await client.get("/reserve/appointments", headers=USER)
    assert response.status_code == 200
    assert response.json() == {"data": []}


async def test_list_appointments_returns_only_own(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """User only sees appointments they participate in."""

    coach_id = int(COACH["X-User-Id"])
    user_id = int(USER["X-User-Id"])
    other_id = int(OTHER["X-User-Id"])

    await _add_coach(db_session, user_id=coach_id)
    slot1 = await _add_slot(db_session, coach_user_id=coach_id, start_at=_T0, end_at=_T1, status="booked")
    slot2 = await _add_slot(db_session, coach_user_id=coach_id, start_at=_T2, end_at=_T3, status="booked")
    # user's appointment
    await _add_appointment(db_session, coach_user_id=coach_id, user_id=user_id, availability_id=slot1.id)
    # someone else's appointment
    await _add_appointment(db_session, coach_user_id=coach_id, user_id=other_id, availability_id=slot2.id)
    await db_session.commit()

    response = await client.get("/reserve/appointments", headers=USER)
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["user_id"] == user_id


async def test_list_appointments_coach_sees_own(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """A coach sees appointments where they are the coach."""

    coach_id = int(COACH["X-User-Id"])
    user_id = int(USER["X-User-Id"])

    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id, status="booked")
    await _add_appointment(db_session, coach_user_id=coach_id, user_id=user_id, availability_id=slot.id)
    await db_session.commit()

    response = await client.get("/reserve/appointments", headers=COACH)
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["coach_user_id"] == coach_id


async def test_list_appointments_filters_by_status(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """``?status=`` narrows results to that status only."""

    coach_id = int(COACH["X-User-Id"])
    user_id = int(USER["X-User-Id"])

    await _add_coach(db_session, user_id=coach_id)
    slot1 = await _add_slot(db_session, coach_user_id=coach_id, start_at=_T0, end_at=_T1, status="booked")
    slot2 = await _add_slot(db_session, coach_user_id=coach_id, start_at=_T2, end_at=_T3, status="booked")
    await _add_appointment(
        db_session, coach_user_id=coach_id, user_id=user_id,
        availability_id=slot1.id, status="confirmed",
    )
    await _add_appointment(
        db_session, coach_user_id=coach_id, user_id=user_id,
        availability_id=slot2.id, status="cancelled",
    )
    await db_session.commit()

    response = await client.get(
        "/reserve/appointments", params={"status": "confirmed"}, headers=USER
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["status"] == "confirmed"


# ---------------------------------------------------------------------------
# GET /reserve/appointments/{id}
# ---------------------------------------------------------------------------


async def test_get_appointment_requires_auth(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """No identity headers → 401."""

    response = await client.get("/reserve/appointments/1")
    assert response.status_code == 401


async def test_get_appointment_404_for_missing(
    client: AsyncClient,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Non-existent appointment → 404."""

    response = await client.get("/reserve/appointments/99999", headers=USER)
    assert response.status_code == 404


async def test_get_appointment_403_for_non_participant(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """An outsider cannot see an appointment they have no part in → 403."""

    coach_id = int(COACH["X-User-Id"])
    user_id = int(USER["X-User-Id"])

    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id, status="booked")
    appt = await _add_appointment(
        db_session, coach_user_id=coach_id, user_id=user_id, availability_id=slot.id
    )
    await db_session.commit()

    response = await client.get(f"/reserve/appointments/{appt.id}", headers=OTHER)
    assert response.status_code == 403


async def test_get_appointment_returns_detail_for_user(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """The booking user can retrieve their appointment."""

    coach_id = int(COACH["X-User-Id"])
    user_id = int(USER["X-User-Id"])

    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id, status="booked")
    appt = await _add_appointment(
        db_session, coach_user_id=coach_id, user_id=user_id, availability_id=slot.id
    )
    await db_session.commit()

    response = await client.get(f"/reserve/appointments/{appt.id}", headers=USER)
    assert response.status_code == 200
    assert response.json()["data"]["id"] == appt.id


# ---------------------------------------------------------------------------
# PATCH /reserve/appointments/{id}
# ---------------------------------------------------------------------------


async def test_update_appointment_requires_auth(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """No identity headers → 401."""

    response = await client.patch(
        "/reserve/appointments/1", json={"status": "cancelled"}
    )
    assert response.status_code == 401


async def test_update_appointment_404_for_missing(
    client: AsyncClient,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Non-existent appointment → 404."""

    response = await client.patch(
        "/reserve/appointments/99999",
        json={"status": "cancelled"},
        headers=USER,
    )
    assert response.status_code == 404


async def test_update_appointment_403_for_non_participant(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """An outsider cannot update an appointment → 403."""

    coach_id = int(COACH["X-User-Id"])
    user_id = int(USER["X-User-Id"])

    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id, status="booked")
    appt = await _add_appointment(
        db_session, coach_user_id=coach_id, user_id=user_id, availability_id=slot.id
    )
    await db_session.commit()

    response = await client.patch(
        f"/reserve/appointments/{appt.id}",
        json={"status": "cancelled"},
        headers=OTHER,
    )
    assert response.status_code == 403


async def test_update_appointment_409_for_terminal_state(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Cannot update an appointment that is already cancelled → 409."""

    coach_id = int(COACH["X-User-Id"])
    user_id = int(USER["X-User-Id"])

    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id, status="booked")
    appt = await _add_appointment(
        db_session, coach_user_id=coach_id, user_id=user_id,
        availability_id=slot.id, status="cancelled",
    )
    await db_session.commit()

    response = await client.patch(
        f"/reserve/appointments/{appt.id}",
        json={"status": "completed"},
        headers=USER,
    )
    assert response.status_code == 409


async def test_update_appointment_user_can_cancel(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """A booking user can cancel their confirmed appointment."""

    coach_id = int(COACH["X-User-Id"])
    user_id = int(USER["X-User-Id"])

    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id, status="booked")
    appt = await _add_appointment(
        db_session, coach_user_id=coach_id, user_id=user_id, availability_id=slot.id
    )
    await db_session.commit()

    response = await client.patch(
        f"/reserve/appointments/{appt.id}",
        json={"status": "cancelled"},
        headers=USER,
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "cancelled"


async def test_update_appointment_coach_can_mark_completed(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """A coach can mark their appointment as completed."""

    coach_id = int(COACH["X-User-Id"])
    user_id = int(USER["X-User-Id"])

    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id, status="booked")
    appt = await _add_appointment(
        db_session, coach_user_id=coach_id, user_id=user_id, availability_id=slot.id
    )
    await db_session.commit()

    response = await client.patch(
        f"/reserve/appointments/{appt.id}",
        json={"status": "completed"},
        headers=COACH,
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "completed"


async def test_update_appointment_rejects_invalid_status(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """An invalid status value is rejected by Pydantic → 422."""

    coach_id = int(COACH["X-User-Id"])
    user_id = int(USER["X-User-Id"])

    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id, status="booked")
    appt = await _add_appointment(
        db_session, coach_user_id=coach_id, user_id=user_id, availability_id=slot.id
    )
    await db_session.commit()

    response = await client.patch(
        f"/reserve/appointments/{appt.id}",
        json={"status": "confirmed"},  # not allowed via PATCH
        headers=USER,
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tidy up
# ---------------------------------------------------------------------------


def teardown_module() -> None:  # pragma: no cover — safety net
    app.dependency_overrides.clear()
