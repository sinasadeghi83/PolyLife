"""Smoke tests for the Sprint-1 backend skeleton."""

from __future__ import annotations

from httpx import AsyncClient


async def test_healthz_returns_ok(client: AsyncClient) -> None:
    """`GET /healthz` returns 200 and `{"status": "ok"}`."""
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
