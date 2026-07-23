"""SCRUM-13 — coach rating route tests.

These tests exercise the live ASGI app through the per-test SQLite session
and confirm that:

* ``POST /reserve/coaches/{id}/ratings`` creates a rating, rejects
  self-rating, rejects duplicate ratings (409), and validates the 1–5 range.
* ``GET /reserve/coaches/{id}/ratings`` returns all non-deleted ratings
  for a coach, ordered newest first, and requires auth.
"""

from __future__ import annotations

from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.coach_profile import CoachProfile
from app.models.coach_rating import CoachRating

USER = {"X-User-Id": "42", "X-User-Username": "alice"}
USER2 = {"X-User-Id": "55", "X-User-Username": "bob"}
COACH = {"X-User-Id": "101", "X-User-Username": "coach-carol"}


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


async def _add_rating(
    db_session: AsyncSession,
    *,
    coach_user_id: int,
    user_id: int,
    rating: int = 5,
    comment: str | None = None,
    is_deleted: bool = False,
) -> CoachRating:
    row = CoachRating(
        coach_user_id=coach_user_id,
        user_id=user_id,
        rating=rating,
        comment=comment,
        is_deleted=is_deleted,
    )
    db_session.add(row)
    await db_session.flush()
    return row


# ---------------------------------------------------------------------------
# POST /reserve/coaches/{coach_user_id}/ratings
# ---------------------------------------------------------------------------


async def test_create_rating_requires_auth(client: AsyncClient) -> None:
    """No identity headers → 401."""

    response = await client.post(
        "/reserve/coaches/101/ratings", json={"rating": 5}
    )
    assert response.status_code == 401


async def test_create_rating_coach_not_found(
    client: AsyncClient,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Rating a non-existent coach → 404."""

    response = await client.post(
        "/reserve/coaches/99999/ratings",
        json={"rating": 5},
        headers=USER,
    )
    assert response.status_code == 404


async def test_create_rating_rejects_self_rating(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """A coach cannot rate themselves → 422."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    await db_session.commit()

    response = await client.post(
        f"/reserve/coaches/{coach_id}/ratings",
        json={"rating": 5},
        headers=COACH,  # same user as the coach
    )
    assert response.status_code == 422
    assert "yourself" in response.json()["detail"].lower()


async def test_create_rating_rejects_out_of_range(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Ratings outside 1–5 are rejected by Pydantic → 422."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    await db_session.commit()

    for bad_value in (0, 6, -1):
        response = await client.post(
            f"/reserve/coaches/{coach_id}/ratings",
            json={"rating": bad_value},
            headers=USER,
        )
        assert response.status_code == 422, f"Expected 422 for rating={bad_value}"


async def test_create_rating_success(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Valid rating returns 201 with the created rating data."""

    coach_id = int(COACH["X-User-Id"])
    user_id = int(USER["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    await db_session.commit()

    response = await client.post(
        f"/reserve/coaches/{coach_id}/ratings",
        json={"rating": 4, "comment": "Great coach!"},
        headers=USER,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["rating"] == 4
    assert data["comment"] == "Great coach!"
    assert data["coach_user_id"] == coach_id
    assert data["user_id"] == user_id


async def test_create_rating_duplicate_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """A second rating from the same user for the same coach → 409."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    await db_session.commit()

    first = await client.post(
        f"/reserve/coaches/{coach_id}/ratings",
        json={"rating": 5},
        headers=USER,
    )
    second = await client.post(
        f"/reserve/coaches/{coach_id}/ratings",
        json={"rating": 3},
        headers=USER,
    )
    assert first.status_code == 201
    assert second.status_code == 409
    assert "already rated" in second.json()["detail"].lower()


async def test_create_rating_different_users_allowed(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Two different users can each leave one rating for the same coach."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    await db_session.commit()

    r1 = await client.post(
        f"/reserve/coaches/{coach_id}/ratings",
        json={"rating": 5},
        headers=USER,
    )
    r2 = await client.post(
        f"/reserve/coaches/{coach_id}/ratings",
        json={"rating": 3},
        headers=USER2,
    )
    assert r1.status_code == 201
    assert r2.status_code == 201


# ---------------------------------------------------------------------------
# GET /reserve/coaches/{coach_user_id}/ratings
# ---------------------------------------------------------------------------


async def test_list_ratings_requires_auth(client: AsyncClient) -> None:
    """No identity headers → 401."""

    response = await client.get("/reserve/coaches/101/ratings")
    assert response.status_code == 401


async def test_list_ratings_empty_for_new_coach(
    client: AsyncClient,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Coach with no ratings returns the empty envelope."""

    response = await client.get("/reserve/coaches/101/ratings", headers=USER)
    assert response.status_code == 200
    assert response.json() == {"data": []}


async def test_list_ratings_returns_all_for_coach(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """All active ratings for a coach are returned."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    await _add_rating(db_session, coach_user_id=coach_id, user_id=int(USER["X-User-Id"]), rating=5)
    await _add_rating(db_session, coach_user_id=coach_id, user_id=int(USER2["X-User-Id"]), rating=3)
    await db_session.commit()

    response = await client.get(f"/reserve/coaches/{coach_id}/ratings", headers=USER)
    assert response.status_code == 200
    assert len(response.json()["data"]) == 2


async def test_list_ratings_excludes_soft_deleted(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Soft-deleted ratings are not returned."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    await _add_rating(db_session, coach_user_id=coach_id, user_id=int(USER["X-User-Id"]), rating=5)
    await _add_rating(
        db_session, coach_user_id=coach_id, user_id=int(USER2["X-User-Id"]),
        rating=1, is_deleted=True,
    )
    await db_session.commit()

    response = await client.get(f"/reserve/coaches/{coach_id}/ratings", headers=USER)
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["rating"] == 5


async def test_list_ratings_ordered_newest_first(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    """Ratings are ordered by ``created_at`` descending."""

    coach_id = int(COACH["X-User-Id"])
    await _add_coach(db_session, user_id=coach_id)
    r1 = await _add_rating(db_session, coach_user_id=coach_id, user_id=int(USER["X-User-Id"]), rating=5)
    r2 = await _add_rating(db_session, coach_user_id=coach_id, user_id=int(USER2["X-User-Id"]), rating=3)
    await db_session.commit()

    response = await client.get(f"/reserve/coaches/{coach_id}/ratings", headers=USER)
    assert response.status_code == 200
    ids = [row["id"] for row in response.json()["data"]]
    # r2 was inserted after r1, so it should appear first
    assert ids == [r2.id, r1.id]


# ---------------------------------------------------------------------------
# Tidy up
# ---------------------------------------------------------------------------


def teardown_module() -> None:  # pragma: no cover — safety net
    app.dependency_overrides.clear()
