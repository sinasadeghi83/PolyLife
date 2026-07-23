"""SCRUM-9 — reserve availability route tests.

These tests exercise the live ASGI app through the per-test SQLite session
and confirm that:

* ``GET /reserve/coaches/{id}/availability`` returns open slots only,
  respects soft-deletion and date-range filters, and requires auth.
* ``POST /reserve/coaches/me/availability`` creates slots, enforces
  coach-profile presence, rejects invalid time ranges, and returns 201.
* ``PATCH /reserve/availability/{id}`` enforces ownership, rejects
  booked slots, and updates status/times correctly.
* ``DELETE /reserve/availability/{id}`` enforces ownership and
  soft-deletes the slot so it no longer appears in the list.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.coach_availability import CoachAvailability
from app.models.coach_profile import CoachProfile

# Identity headers used throughout
USER = {"X-User-Id": "42", "X-User-Username": "alice"}
COACH = {"X-User-Id": "101", "X-User-Username": "coach-bob"}
OTHER_COACH = {"X-User-Id": "202", "X-User-Username": "coach-carol"}

# Convenient base times
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
    """Insert a ``CoachProfile`` row that satisfies FK constraints."""
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
    """Insert a ``CoachAvailability`` row directly into the test DB."""
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


# ---------------------------------------------------------------------------
# GET /reserve/coaches/{coach_user_id}/availability
# ---------------------------------------------------------------------------


async def test_list_availability_requires_auth(client: AsyncClient) -> None:
    """No forwarded identity headers → 401."""

    response = await client.get("/reserve/coaches/101/availability")
    assert response.status_code == 401


async def test_list_availability_empty_for_new_coach(
    client: AsyncClient,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Authenticated request with no slots returns the empty envelope."""

    response = await client.get("/reserve/coaches/101/availability", headers=USER)
    assert response.status_code == 200
    assert response.json() == {"data": []}


async def test_list_availability_returns_open_slots_only(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Only ``status='open'`` slots are returned; booked/blocked are excluded."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    await _add_slot(db_session, coach_user_id=coach_id, start_at=_T0, end_at=_T1, status="open")
    await _add_slot(db_session, coach_user_id=coach_id, start_at=_T1, end_at=_T2, status="booked")
    await _add_slot(db_session, coach_user_id=coach_id, start_at=_T2, end_at=_T3, status="blocked")
    await db_session.commit()

    response = await client.get(f"/reserve/coaches/{coach_id}/availability", headers=USER)
    assert response.status_code == 200
    payload = response.json()["data"]
    assert len(payload) == 1
    assert payload[0]["status"] == "open"


async def test_list_availability_excludes_soft_deleted(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Soft-deleted slots are filtered out of the list response."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    await _add_slot(db_session, coach_user_id=coach_id, start_at=_T0, end_at=_T1)
    await _add_slot(db_session, coach_user_id=coach_id, start_at=_T1, end_at=_T2, is_deleted=True)
    await db_session.commit()

    response = await client.get(f"/reserve/coaches/{coach_id}/availability", headers=USER)
    assert response.status_code == 200
    payload = response.json()["data"]
    assert len(payload) == 1


async def test_list_availability_ordered_by_start_at(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Slots are returned in ascending ``start_at`` order."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    await _add_slot(db_session, coach_user_id=coach_id, start_at=_T2, end_at=_T3)
    await _add_slot(db_session, coach_user_id=coach_id, start_at=_T0, end_at=_T1)
    await _add_slot(db_session, coach_user_id=coach_id, start_at=_T1, end_at=_T2)
    await db_session.commit()

    response = await client.get(f"/reserve/coaches/{coach_id}/availability", headers=USER)
    assert response.status_code == 200
    starts = [row["start_at"] for row in response.json()["data"]]
    assert starts == sorted(starts)


async def test_list_availability_filters_by_from(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """``?from=`` filters out slots starting before the given datetime."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    await _add_slot(db_session, coach_user_id=coach_id, start_at=_T0, end_at=_T1)
    await _add_slot(db_session, coach_user_id=coach_id, start_at=_T2, end_at=_T3)
    await db_session.commit()

    # Only the second slot starts at or after _T2
    response = await client.get(
        f"/reserve/coaches/{coach_id}/availability",
        params={"from": _T2.isoformat()},
        headers=USER,
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert len(payload) == 1
    assert payload[0]["start_at"] == _T2.isoformat()


async def test_list_availability_filters_by_to(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """``?to=`` filters out slots ending after the given datetime."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    await _add_slot(db_session, coach_user_id=coach_id, start_at=_T0, end_at=_T1)
    await _add_slot(db_session, coach_user_id=coach_id, start_at=_T2, end_at=_T3)
    await db_session.commit()

    # Only the first slot ends at or before _T1
    response = await client.get(
        f"/reserve/coaches/{coach_id}/availability",
        params={"to": _T1.isoformat()},
        headers=USER,
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert len(payload) == 1
    assert payload[0]["end_at"] == _T1.isoformat()


# ---------------------------------------------------------------------------
# POST /reserve/coaches/me/availability
# ---------------------------------------------------------------------------


async def test_create_availability_requires_auth(client: AsyncClient) -> None:
    """No identity headers → 401."""

    response = await client.post(
        "/reserve/coaches/me/availability",
        json={"slots": [{"start_at": _T0.isoformat(), "end_at": _T1.isoformat()}]},
    )
    assert response.status_code == 401


async def test_create_availability_requires_coach_profile(
    client: AsyncClient,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """A user without a coach profile gets 422."""

    response = await client.post(
        "/reserve/coaches/me/availability",
        json={"slots": [{"start_at": _T0.isoformat(), "end_at": _T1.isoformat()}]},
        headers=COACH,
    )
    assert response.status_code == 422
    assert "coach profile" in response.json()["detail"].lower()


async def test_create_availability_creates_slots(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Coach with a profile can create multiple slots; returns 201."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    await db_session.commit()

    payload = {
        "slots": [
            {"start_at": _T0.isoformat(), "end_at": _T1.isoformat()},
            {"start_at": _T2.isoformat(), "end_at": _T3.isoformat()},
        ]
    }
    response = await client.post(
        "/reserve/coaches/me/availability",
        json=payload,
        headers=COACH,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert len(data) == 2
    assert all(row["status"] == "open" for row in data)
    assert all(row["coach_user_id"] == coach_id for row in data)


async def test_create_availability_rejects_empty_slots(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """An empty ``slots`` list is rejected with 422."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    await db_session.commit()

    response = await client.post(
        "/reserve/coaches/me/availability",
        json={"slots": []},
        headers=COACH,
    )
    assert response.status_code == 422


async def test_create_availability_rejects_inverted_times(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """A slot where ``end_at <= start_at`` is rejected with 422."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    await db_session.commit()

    response = await client.post(
        "/reserve/coaches/me/availability",
        json={"slots": [{"start_at": _T1.isoformat(), "end_at": _T0.isoformat()}]},
        headers=COACH,
    )
    assert response.status_code == 422

    # Equal start/end should also be rejected
    response_eq = await client.post(
        "/reserve/coaches/me/availability",
        json={"slots": [{"start_at": _T0.isoformat(), "end_at": _T0.isoformat()}]},
        headers=COACH,
    )
    assert response_eq.status_code == 422


async def test_create_availability_slots_appear_in_list(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Slots created via POST are immediately visible in the GET list."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    await db_session.commit()

    await client.post(
        "/reserve/coaches/me/availability",
        json={"slots": [{"start_at": _T0.isoformat(), "end_at": _T1.isoformat()}]},
        headers=COACH,
    )

    list_response = await client.get(
        f"/reserve/coaches/{coach_id}/availability", headers=USER
    )
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 1


# ---------------------------------------------------------------------------
# PATCH /reserve/availability/{slot_id}
# ---------------------------------------------------------------------------


async def test_update_availability_requires_auth(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """No identity headers → 401."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id)
    await db_session.commit()

    response = await client.patch(
        f"/reserve/availability/{slot.id}",
        json={"status": "blocked"},
    )
    assert response.status_code == 401


async def test_update_availability_404_for_missing(
    client: AsyncClient,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Non-existent slot id → 404."""

    response = await client.patch(
        "/reserve/availability/99999",
        json={"status": "blocked"},
        headers=COACH,
    )
    assert response.status_code == 404


async def test_update_availability_403_for_wrong_owner(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """A coach cannot modify another coach's slot → 403."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id)
    await db_session.commit()

    response = await client.patch(
        f"/reserve/availability/{slot.id}",
        json={"status": "blocked"},
        headers=OTHER_COACH,  # different coach
    )
    assert response.status_code == 403


async def test_update_availability_409_for_booked_slot(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """A booked slot cannot be updated → 409."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id, status="booked")
    await db_session.commit()

    response = await client.patch(
        f"/reserve/availability/{slot.id}",
        json={"status": "open"},
        headers=COACH,
    )
    assert response.status_code == 409


async def test_update_availability_blocks_slot(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Coach can mark their own open slot as blocked; response reflects change."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id)
    await db_session.commit()

    response = await client.patch(
        f"/reserve/availability/{slot.id}",
        json={"status": "blocked"},
        headers=COACH,
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "blocked"


async def test_update_availability_rejects_empty_payload(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """A PATCH body with no fields → 422."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id)
    await db_session.commit()

    response = await client.patch(
        f"/reserve/availability/{slot.id}",
        json={},
        headers=COACH,
    )
    assert response.status_code == 422


async def test_update_availability_rejects_inverted_times(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Updating times so that end_at <= start_at → 422."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id, start_at=_T0, end_at=_T1)
    await db_session.commit()

    response = await client.patch(
        f"/reserve/availability/{slot.id}",
        json={"start_at": _T2.isoformat(), "end_at": _T1.isoformat()},
        headers=COACH,
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /reserve/availability/{slot_id}
# ---------------------------------------------------------------------------


async def test_delete_availability_requires_auth(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """No identity headers → 401."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id)
    await db_session.commit()

    response = await client.delete(f"/reserve/availability/{slot.id}")
    assert response.status_code == 401


async def test_delete_availability_404_for_missing(
    client: AsyncClient,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Non-existent slot id → 404."""

    response = await client.delete("/reserve/availability/99999", headers=COACH)
    assert response.status_code == 404


async def test_delete_availability_403_for_wrong_owner(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """A coach cannot delete another coach's slot → 403."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id)
    await db_session.commit()

    response = await client.delete(
        f"/reserve/availability/{slot.id}",
        headers=OTHER_COACH,
    )
    assert response.status_code == 403


async def test_delete_availability_soft_deletes(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """DELETE returns 204 and the slot no longer appears in the list."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id)
    await db_session.commit()

    delete_response = await client.delete(
        f"/reserve/availability/{slot.id}",
        headers=COACH,
    )
    assert delete_response.status_code == 204

    list_response = await client.get(
        f"/reserve/coaches/{coach_id}/availability",
        headers=USER,
    )
    assert list_response.status_code == 200
    assert list_response.json()["data"] == []


async def test_delete_already_deleted_slot_returns_404(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Deleting a soft-deleted slot is treated as 404 (idempotent externally)."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    slot = await _add_slot(db_session, coach_user_id=coach_id, is_deleted=True)
    await db_session.commit()

    response = await client.delete(f"/reserve/availability/{slot.id}", headers=COACH)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tidy up
# ---------------------------------------------------------------------------


def teardown_module() -> None:  # pragma: no cover — safety net
    app.dependency_overrides.clear()
