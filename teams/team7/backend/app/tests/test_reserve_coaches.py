"""Reserve coach-profile route tests.

Covers the coach directory endpoints:

* ``GET /reserve/coaches``
* ``GET /reserve/coaches/{coach_user_id}``
* ``POST /reserve/coaches/me``
"""

from __future__ import annotations

from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coach_profile import CoachProfile
from app.models.coach_rating import CoachRating

USER = {"X-User-Id": "42", "X-User-Username": "alice"}
COACH1 = {"X-User-Id": "101", "X-User-Username": "coach-a"}
COACH2 = {"X-User-Id": "102", "X-User-Username": "coach-b"}


async def _add_profile(
    db_session: AsyncSession,
    *,
    user_id: int,
    bio: str | None = None,
    specialties: list[str] | None = None,
    hourly_rate: str = "50.00",
    years_experience: int | None = None,
    is_online: bool = False,
    is_deleted: bool = False,
) -> CoachProfile:
    row = CoachProfile(
        user_id=user_id,
        bio=bio,
        specialties=specialties,
        hourly_rate=Decimal(hourly_rate),
        years_experience=years_experience,
        is_online=is_online,
        is_deleted=is_deleted,
    )
    db_session.add(row)
    await db_session.flush()
    return row


async def _add_rating(
    db_session: AsyncSession,
    *,
    coach_user_id: int,
    user_id: int,
    rating: int,
    is_deleted: bool = False,
) -> CoachRating:
    row = CoachRating(
        coach_user_id=coach_user_id,
        user_id=user_id,
        rating=rating,
        is_deleted=is_deleted,
    )
    db_session.add(row)
    await db_session.flush()
    return row


async def test_list_coaches_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/reserve/coaches")
    assert response.status_code == 401


async def test_list_coaches_empty(client: AsyncClient, override_db: AsyncSession) -> None:  # noqa: ARG001
    response = await client.get("/reserve/coaches", headers=USER)
    assert response.status_code == 200
    assert response.json() == {"data": []}


async def test_list_coaches_returns_profiles_with_aggregates(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    await _add_profile(
        db_session,
        user_id=101,
        bio="Coach A",
        specialties=["yoga", "strength"],
        hourly_rate="75.00",
        years_experience=4,
    )
    await _add_rating(db_session, coach_user_id=101, user_id=1, rating=5)
    await _add_rating(db_session, coach_user_id=101, user_id=2, rating=3)
    await db_session.commit()

    response = await client.get("/reserve/coaches", headers=USER)
    assert response.status_code == 200

    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["user_id"] == 101
    assert data[0]["rating_count"] == 2
    assert data[0]["avg_rating"] == 4.0


async def test_list_coaches_filters_by_specialty(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    await _add_profile(db_session, user_id=101, specialties=["yoga"], hourly_rate="60.00")
    await _add_profile(db_session, user_id=102, specialties=["pilates"], hourly_rate="70.00")
    await db_session.commit()

    response = await client.get(
        "/reserve/coaches",
        params={"specialty": "yoga"},
        headers=USER,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["user_id"] == 101


async def test_list_coaches_filters_by_min_rating(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    await _add_profile(db_session, user_id=101, hourly_rate="60.00")
    await _add_profile(db_session, user_id=102, hourly_rate="70.00")
    await _add_rating(db_session, coach_user_id=101, user_id=1, rating=5)
    await _add_rating(db_session, coach_user_id=102, user_id=2, rating=2)
    await db_session.commit()

    response = await client.get(
        "/reserve/coaches",
        params={"min_rating": 4},
        headers=USER,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["user_id"] == 101


async def test_get_coach_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/reserve/coaches/101")
    assert response.status_code == 401


async def test_get_coach_not_found(
    client: AsyncClient,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    response = await client.get("/reserve/coaches/99999", headers=USER)
    assert response.status_code == 404


async def test_get_coach_returns_profile_with_aggregates(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    await _add_profile(db_session, user_id=101, hourly_rate="80.00", specialties=["boxing"])
    await _add_rating(db_session, coach_user_id=101, user_id=1, rating=5)
    await _add_rating(db_session, coach_user_id=101, user_id=2, rating=4)
    await _add_rating(db_session, coach_user_id=101, user_id=3, rating=1, is_deleted=True)
    await db_session.commit()

    response = await client.get("/reserve/coaches/101", headers=USER)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["user_id"] == 101
    assert data["rating_count"] == 2
    assert data["avg_rating"] == 4.5


async def test_upsert_my_coach_profile_create_requires_hourly_rate(
    client: AsyncClient,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    response = await client.post(
        "/reserve/coaches/me",
        json={"bio": "new coach"},
        headers=COACH1,
    )
    assert response.status_code == 422
    assert "hourly_rate" in response.json()["detail"]


async def test_upsert_my_coach_profile_create_then_update(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
) -> None:
    create_response = await client.post(
        "/reserve/coaches/me",
        json={
            "bio": "Coach Alpha",
            "specialties": ["yoga", "mobility"],
            "hourly_rate": "90.00",
            "years_experience": 6,
            "is_online": True,
        },
        headers=COACH1,
    )
    assert create_response.status_code == 200
    created = create_response.json()["data"]
    assert created["user_id"] == int(COACH1["X-User-Id"])
    assert created["hourly_rate"] == "90.00"
    assert created["is_online"] is True

    update_response = await client.post(
        "/reserve/coaches/me",
        json={"bio": "Updated Bio"},
        headers=COACH1,
    )
    assert update_response.status_code == 200
    updated = update_response.json()["data"]
    assert updated["bio"] == "Updated Bio"
    # unchanged from create
    assert updated["hourly_rate"] == "90.00"

    # no duplicate rows were created
    count = (
        await db_session.execute(
            CoachProfile.__table__.select().where(CoachProfile.user_id == int(COACH1["X-User-Id"]))
        )
    ).fetchall()
    assert len(count) == 1
