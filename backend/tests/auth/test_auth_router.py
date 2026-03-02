"""Tests for auth router — HTTP endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from pct.auth.service import clear_users, set_users_file
from pct.main import app


@pytest.fixture(autouse=True)
def reset_users():
    set_users_file(None)
    clear_users()
    yield
    clear_users()
    set_users_file(None)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


class TestAuthRouter:
    async def test_register(self, client: AsyncClient):
        resp = await client.post("/api/auth/register", json={"email": "new@test.com", "password": "pass123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_duplicate(self, client: AsyncClient):
        await client.post("/api/auth/register", json={"email": "dup@test.com", "password": "pass"})
        resp = await client.post("/api/auth/register", json={"email": "dup@test.com", "password": "pass2"})
        assert resp.status_code == 400

    async def test_login(self, client: AsyncClient):
        await client.post("/api/auth/register", json={"email": "user@test.com", "password": "mypass"})
        resp = await client.post("/api/auth/login", json={"email": "user@test.com", "password": "mypass"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_login_invalid(self, client: AsyncClient):
        resp = await client.post("/api/auth/login", json={"email": "nobody@test.com", "password": "nope"})
        assert resp.status_code == 401

    async def test_me_authenticated(self, client: AsyncClient):
        reg_resp = await client.post("/api/auth/register", json={"email": "me@test.com", "password": "pass"})
        token = reg_resp.json()["access_token"]
        resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["email"] == "me@test.com"

    async def test_me_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    async def test_me_invalid_token(self, client: AsyncClient):
        resp = await client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401
