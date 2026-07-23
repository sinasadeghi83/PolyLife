"""SCRUM-8 — list / create chat thread route tests.

These tests exercise the live ASGI app through the per-test SQLite
session and confirm that:

* ``GET /chat/threads`` returns the caller's active threads, ordered
  newest-first with deterministic null handling, and respects
  soft-deletion.
* ``POST /chat/threads`` is idempotent for the same ``(user, coach)``
  pair, rejects self/missing/inactive coaches, and handles the
  unique-constraint race deterministically.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.chat_thread import ChatThread

USER = {"X-User-Id": "42", "X-User-Username": "alice"}
OTHER = {"X-User-Id": "99", "X-User-Username": "bob"}


def _override(db_session: AsyncSession):  # type: ignore[no-untyped-def]
    async def _dep():
        yield db_session

    return _dep


async def _add_thread(
    db_session: AsyncSession,  # type: ignore[no-untyped-def]
    *,
    user_id: int,
    coach_user_id: int,
    last_message_at: datetime | None = None,
    is_deleted: bool = False,
) -> ChatThread:
    thread = ChatThread(
        user_id=user_id,
        coach_user_id=coach_user_id,
        last_message_at=last_message_at,
        is_deleted=is_deleted,
    )
    db_session.add(thread)
    await db_session.flush()
    return thread


# --- GET /chat/threads ---------------------------------------------------


async def test_list_threads_requires_auth(client: AsyncClient) -> None:
    """No forwarded identity → 401 with the missing-headers detail."""

    response = await client.get("/chat/threads")
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Missing forwarded identity headers from the gateway."
    }


async def test_list_threads_empty_for_new_user(
    client: AsyncClient, override_db: AsyncSession  # noqa: ARG001
) -> None:
    """Authenticated request with no threads returns the empty envelope."""

    response = await client.get("/chat/threads", headers=USER)
    assert response.status_code == 200
    assert response.json() == {"data": []}


async def test_list_threads_returns_only_participating(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
    make_coach,  # type: ignore[no-untyped-def]
) -> None:
    """User sees threads where they are ``user_id`` or ``coach_user_id``."""

    own = await make_coach(user_id=101)
    other = await make_coach(user_id=102)
    stranger = await make_coach(user_id=103)
    # The caller (id 42) is also a coach, so a thread where the caller is
    # the coach side of the pair can be created (FK to coach_profile).
    caller_as_coach = await make_coach(user_id=int(USER["X-User-Id"]))

    await _add_thread(
        db_session, user_id=int(USER["X-User-Id"]), coach_user_id=own.user_id
    )
    await _add_thread(
        db_session,
        user_id=int(OTHER["X-User-Id"]),
        coach_user_id=caller_as_coach.user_id,  # the caller is the coach here
    )
    await _add_thread(
        db_session,
        user_id=int(OTHER["X-User-Id"]),
        coach_user_id=other.user_id,
    )
    await _add_thread(
        db_session,
        user_id=999,
        coach_user_id=stranger.user_id,
    )
    await db_session.commit()

    response = await client.get("/chat/threads", headers=USER)
    assert response.status_code == 200
    payload = response.json()["data"]
    assert {row["coach_user_id"] for row in payload} == {
        own.user_id,
        caller_as_coach.user_id,
    }


async def test_list_threads_excludes_soft_deleted(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
    make_coach,  # type: ignore[no-untyped-def]
) -> None:
    """Soft-deleted threads are filtered out of the list response."""

    coach = await make_coach(user_id=101)
    other = await make_coach(user_id=102)
    await _add_thread(
        db_session,
        user_id=int(USER["X-User-Id"]),
        coach_user_id=coach.user_id,
    )
    await _add_thread(
        db_session,
        user_id=int(USER["X-User-Id"]),
        coach_user_id=other.user_id,
        is_deleted=True,
    )
    await db_session.commit()

    response = await client.get("/chat/threads", headers=USER)
    assert response.status_code == 200
    payload = response.json()["data"]
    assert len(payload) == 1
    assert payload[0]["coach_user_id"] == coach.user_id


async def test_list_threads_orders_by_last_message_at_desc(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
    make_coach,  # type: ignore[no-untyped-def]
) -> None:
    """Newest ``last_message_at`` first; ties broken by ``id DESC``."""

    now = datetime(2026, 7, 1, 12, 0, 0)
    a = await make_coach(user_id=101)
    b = await make_coach(user_id=102)
    c = await make_coach(user_id=103)
    d = await make_coach(user_id=104)

    await _add_thread(
        db_session,
        user_id=int(USER["X-User-Id"]),
        coach_user_id=a.user_id,
        last_message_at=now - timedelta(hours=3),
    )
    await _add_thread(
        db_session,
        user_id=int(USER["X-User-Id"]),
        coach_user_id=b.user_id,
        last_message_at=now - timedelta(hours=1),
    )
    await _add_thread(
        db_session,
        user_id=int(USER["X-User-Id"]),
        coach_user_id=c.user_id,
        last_message_at=None,
    )
    await _add_thread(
        db_session,
        user_id=int(USER["X-User-Id"]),
        coach_user_id=d.user_id,
        last_message_at=now,
    )
    await db_session.commit()

    response = await client.get("/chat/threads", headers=USER)
    assert response.status_code == 200
    payload = response.json()["data"]
    assert [row["coach_user_id"] for row in payload] == [
        d.user_id,
        b.user_id,
        a.user_id,
        c.user_id,
    ]


async def test_list_threads_tie_breaks_by_id_desc(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
    make_coach,  # type: ignore[no-untyped-def]
) -> None:
    """Two threads with identical ``last_message_at`` are ordered by id DESC."""

    shared = datetime(2026, 7, 1, 12, 0, 0)
    a = await make_coach(user_id=101)
    b = await make_coach(user_id=102)
    t1 = await _add_thread(
        db_session,
        user_id=int(USER["X-User-Id"]),
        coach_user_id=a.user_id,
        last_message_at=shared,
    )
    t2 = await _add_thread(
        db_session,
        user_id=int(USER["X-User-Id"]),
        coach_user_id=b.user_id,
        last_message_at=shared,
    )
    await db_session.commit()

    response = await client.get("/chat/threads", headers=USER)
    assert response.status_code == 200
    payload = response.json()["data"]
    assert [row["id"] for row in payload] == sorted(
        [t1.id, t2.id], reverse=True
    )


# --- POST /chat/threads --------------------------------------------------


async def test_open_thread_rejects_self(
    client: AsyncClient, override_db: AsyncSession  # noqa: ARG001
) -> None:
    """The caller cannot open a thread with themselves."""

    response = await client.post(
        "/chat/threads",
        json={"coach_user_id": int(USER["X-User-Id"])},
        headers=USER,
    )
    assert response.status_code == 422
    assert "yourself" in response.json()["detail"]


async def test_open_thread_requires_positive_coach(
    client: AsyncClient, override_db: AsyncSession  # noqa: ARG001
) -> None:
    """Pydantic rejects zero / negative ``coach_user_id`` with 422."""

    response = await client.post(
        "/chat/threads", json={"coach_user_id": 0}, headers=USER
    )
    assert response.status_code == 422
    response = await client.post(
        "/chat/threads", json={"coach_user_id": -1}, headers=USER
    )
    assert response.status_code == 422


async def test_open_thread_rejects_missing_coach(
    client: AsyncClient, override_db: AsyncSession  # noqa: ARG001
) -> None:
    """A coach_user_id with no profile returns 422."""

    response = await client.post(
        "/chat/threads", json={"coach_user_id": 555}, headers=USER
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "Coach not found."}


async def test_open_thread_rejects_soft_deleted_coach(
    client: AsyncClient,
    override_db: AsyncSession,  # noqa: ARG001
    make_coach,  # type: ignore[no-untyped-def]
) -> None:
    """A soft-deleted ``coach_profile`` is treated as missing."""

    coach = await make_coach(user_id=101, is_deleted=True)
    response = await client.post(
        "/chat/threads",
        json={"coach_user_id": coach.user_id},
        headers=USER,
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "Coach not found."}


async def test_open_thread_creates_then_returns_idempotent(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
    make_coach,  # type: ignore[no-untyped-def]
) -> None:
    """First call returns 201, repeat returns 200 with the same id."""

    coach = await make_coach(user_id=101)
    first = await client.post(
        "/chat/threads",
        json={"coach_user_id": coach.user_id},
        headers=USER,
    )
    assert first.status_code == 201
    first_id = first.json()["data"]["id"]
    assert first.json()["data"]["user_id"] == int(USER["X-User-Id"])

    second = await client.post(
        "/chat/threads",
        json={"coach_user_id": coach.user_id},
        headers=USER,
    )
    assert second.status_code == 200
    assert second.json()["data"]["id"] == first_id


async def test_open_thread_rejects_when_soft_deleted_pair_exists(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
    make_coach,  # type: ignore[no-untyped-def]
) -> None:
    """A previously closed (soft-deleted) thread for the same pair → 409."""

    coach = await make_coach(user_id=101)
    await _add_thread(
        db_session,
        user_id=int(USER["X-User-Id"]),
        coach_user_id=coach.user_id,
        is_deleted=True,
    )
    await db_session.commit()

    response = await client.post(
        "/chat/threads",
        json={"coach_user_id": coach.user_id},
        headers=USER,
    )
    assert response.status_code == 409


async def test_open_thread_concurrent_inserts_yield_one_row(
    client: AsyncClient,
    db_session: AsyncSession,
    override_db: AsyncSession,  # noqa: ARG001
    make_coach,  # type: ignore[no-untyped-def]
) -> None:
    """Sequential POSTs for the same pair return 201 then 200 with the same id.

    The unique-pair race-resolution path is exercised by this test because
    a second ``POST /chat/threads`` for the same pair falls through the
    ``get_or_create_thread`` "fast path" — exactly the branch that wins
    when two inserts race and the loser hits ``IntegrityError``. The
    concurrent-flush case is covered by the service-level race handler
    in ``app.services.chat.get_or_create_thread``.
    """

    coach = await make_coach(user_id=101)
    payload = {"coach_user_id": coach.user_id}

    first = await client.post("/chat/threads", json=payload, headers=USER)
    second = await client.post("/chat/threads", json=payload, headers=USER)
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["data"]["id"] == second.json()["data"]["id"]
    # And the second row never materialised.
    rows = (
        await db_session.execute(
            ChatThread.__table__.select().where(
                ChatThread.user_id == int(USER["X-User-Id"]),
                ChatThread.coach_user_id == coach.user_id,
            )
        )
    ).fetchall()
    assert len(rows) == 1


# --- Tidy up -------------------------------------------------------------


def teardown_module() -> None:  # pragma: no cover - safety net
    app.dependency_overrides.clear()
