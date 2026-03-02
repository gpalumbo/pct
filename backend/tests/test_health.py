"""Tests for health endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from pct.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


class TestHealth:
    async def test_health_returns_200(self, client: AsyncClient):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_health_no_auth_required(self, client: AsyncClient):
        # No Authorization header
        resp = await client.get("/api/health")
        assert resp.status_code == 200
