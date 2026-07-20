"""Auth helpers.

We DO NOT decode JWTs ourselves. The team's Nginx gateway performs
`auth_request` forward-auth against the core service
(`/api/verify`) and forwards the resolved identity as request headers:

    X-User-Id       -> str (numeric user id as a string)
    X-User-Username -> str (username)

Anything reaching `get_current_user` is already authenticated. If the
gateway rejected the request it would never arrive here — Nginx would
have returned 401 upstream. We still validate the headers defensively.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, status


@dataclass(slots=True, frozen=True)
class CurrentUser:
    """Identity of the caller, as forwarded by the team gateway."""

    id: int
    username: str


def get_current_user(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_username: str | None = Header(default=None, alias="X-User-Username"),
) -> CurrentUser:
    """FastAPI dependency returning the authenticated caller.

    Raises 401 if either header is missing — that should never happen
    for requests that passed the gateway's `auth_request`, but we keep
    the check to fail loudly if the gateway is misconfigured.
    """
    if x_user_id is None or x_user_username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing forwarded identity headers from the gateway.",
        )
    try:
        user_id = int(x_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed X-User-Id header (not an integer).",
        ) from exc

    return CurrentUser(id=user_id, username=x_user_username)
