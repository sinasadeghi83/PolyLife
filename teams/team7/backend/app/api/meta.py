"""Meta router — health/identity smoke endpoints.

These exist so the auth dependency has a real HTTP surface to exercise
end-to-end and so future chat/reserve endpoints have a model to copy.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import CurrentUser, get_current_user

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/auth-smoke")
async def auth_smoke(current_user: CurrentUser = Depends(get_current_user)) -> dict[str, dict[str, int | str]]:  # noqa: B008
    """Echo the identity forwarded by the team gateway."""
    return {"data": {"id": current_user.id, "username": current_user.username}}