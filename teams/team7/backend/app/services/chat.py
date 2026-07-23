"""Chat service layer (SCRUM-8).

Pure database functions for the chat with-coach service. The HTTP layer
in ``app.api.chat`` depends on these so router tests can stay focused on
request/response shape and authorisation.

Idempotency / uniqueness contract for ``get_or_create_thread``:

- There is at most one *active* thread per ``(user_id, coach_user_id)``
  pair; the database enforces this with
  ``uq_chat_thread_user_coach`` on ``chat_thread``.
- If an active row exists, it is returned (``created=False``).
- If a *soft-deleted* row already exists for the same pair, the call
  returns ``HTTP 409 Conflict`` and refuses to silently resurrect it.
  Restoring a soft-deleted thread is a separate audit-sensitive
  operation; it is out of scope for SCRUM-8.
- If the pair is genuinely new, a fresh row is inserted. If two parallel
  inserts race, the loser's ``IntegrityError`` is rolled back and the
  surviving row is returned (``created=False``).
"""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_thread import ChatThread
from app.models.coach_profile import CoachProfile


async def coach_profile_exists(session: AsyncSession, coach_user_id: int) -> bool:
    """Return True iff an active ``coach_profile`` row exists for the given id."""

    stmt = select(CoachProfile.user_id).where(
        CoachProfile.user_id == coach_user_id,
        CoachProfile.is_deleted.is_(False),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def list_threads_for_user(
    session: AsyncSession, user_id: int
) -> Sequence[ChatThread]:
    """Return the active threads the user participates in, newest first.

    A user "participates" if they appear as either the regular user
    (``user_id``) or the coach (``coach_user_id``). Soft-deleted rows are
    excluded. Ordering is ``last_message_at DESC NULLS LAST`` with ``id DESC``
    as a deterministic tie-breaker.
    """

    stmt = (
        select(ChatThread)
        .where(
            ChatThread.is_deleted.is_(False),
            or_(
                ChatThread.user_id == user_id,
                ChatThread.coach_user_id == user_id,
            ),
        )
        .order_by(ChatThread.last_message_at.desc().nulls_last(), ChatThread.id.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_or_create_thread(
    session: AsyncSession, *, user_id: int, coach_user_id: int
) -> tuple[ChatThread, bool]:
    """Return the unique active thread for ``(user_id, coach_user_id)``.

    The boolean is ``True`` iff a new row was inserted by this call.

    Raises ``HTTPException(409)`` if an inactive (soft-deleted) thread
    already exists for the same pair, or if a parallel insert lost the
    race against an unrelated unhandled constraint violation.
    """

    # Fast path: active row already exists.
    existing = await _fetch_active_thread(session, user_id, coach_user_id)
    if existing is not None:
        return existing, False

    # Reject rather than resurrect a soft-deleted row.
    soft_deleted = await _fetch_soft_deleted_thread(session, user_id, coach_user_id)
    if soft_deleted is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A previously closed thread for this pair exists; reopen it explicitly.",
        )

    # Insert and handle the unique-constraint race.
    thread = ChatThread(user_id=user_id, coach_user_id=coach_user_id)
    session.add(thread)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raced = await _fetch_active_thread(session, user_id, coach_user_id)
        if raced is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Unexpected constraint violation while creating thread.",
            ) from None
        return raced, False
    await session.refresh(thread)
    return thread, True


async def _fetch_active_thread(
    session: AsyncSession, user_id: int, coach_user_id: int
) -> ChatThread | None:
    stmt = select(ChatThread).where(
        ChatThread.user_id == user_id,
        ChatThread.coach_user_id == coach_user_id,
        ChatThread.is_deleted.is_(False),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _fetch_soft_deleted_thread(
    session: AsyncSession, user_id: int, coach_user_id: int
) -> ChatThread | None:
    stmt = select(ChatThread).where(
        ChatThread.user_id == user_id,
        ChatThread.coach_user_id == coach_user_id,
        ChatThread.is_deleted.is_(True),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
