"""SCRUM-7 — auth smoke tests for the `X-User-Id` / `X-User-Username` flow.

These tests exercise the live ASGI app through the existing async
``client`` fixture from ``conftest.py`` and confirm that
``app.core.security.get_current_user`` (consumed by ``GET /meta/auth-smoke``)
correctly accepts a well-formed forwarded identity and rejects each of
the three failure modes documented in ``security.py``.

We deliberately do NOT mock the dependency — the contract we care about
is the HTTP-level behaviour of the dependency as wired into FastAPI.
"""

from __future__ import annotations

from httpx import AsyncClient

PATH = "/meta/auth-smoke"


async def test_auth_smoke_returns_current_user(client: AsyncClient) -> None:
    """A request carrying both forwarded headers echoes the identity back as JSON."""
    response = await client.get(
        PATH,
        headers={"X-User-Id": "42", "X-User-Username": "alice"},
    )
    assert response.status_code == 200
    assert response.json() == {"data": {"id": 42, "username": "alice"}}


async def test_auth_smoke_rejects_missing_user_id(client: AsyncClient) -> None:
    """Only ``X-User-Username`` is sent → 401 with the missing-headers detail."""
    response = await client.get(
        PATH,
        headers={"X-User-Username": "alice"},
    )
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Missing forwarded identity headers from the gateway."
    }


async def test_auth_smoke_rejects_missing_username(client: AsyncClient) -> None:
    """Only ``X-User-Id`` is sent → 401 with the same missing-headers detail."""
    response = await client.get(
        PATH,
        headers={"X-User-Id": "42"},
    )
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Missing forwarded identity headers from the gateway."
    }


async def test_auth_smoke_rejects_malformed_user_id(client: AsyncClient) -> None:
    """``X-User-Id`` is non-numeric → 401 with the malformed-id detail."""
    response = await client.get(
        PATH,
        headers={"X-User-Id": "not-an-integer", "X-User-Username": "alice"},
    )
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Malformed X-User-Id header (not an integer)."
    }
