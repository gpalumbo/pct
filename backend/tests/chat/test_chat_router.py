"""Tests for the chat API endpoints — session CRUD and message curation."""

import os

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def _isolate_chat(tmp_path):
    """Isolate project root and registries for each test."""
    os.environ["PCT_PROJECT_ROOT"] = str(tmp_path / "project")
    os.environ["PCT_REGISTRIES_DIR"] = str(tmp_path / "registries")
    (tmp_path / "project" / ".pct").mkdir(parents=True)

    from pct import config

    config.settings = config.Settings()
    yield


@pytest.fixture
async def client():
    from pct.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    resp = await client.post(
        "/api/auth/register",
        json={"email": "chat@test.com", "password": "testpass123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestSessionEndpoints:
    async def test_list_sessions_empty(self, client, auth_headers):
        resp = await client.get("/api/chat/sessions", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_session(self, client, auth_headers):
        resp = await client.post(
            "/api/chat/sessions",
            params={"title": "Test Chat"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "planning-001"
        assert data["title"] == "Test Chat"

    async def test_get_default_session_creates(self, client, auth_headers):
        resp = await client.get("/api/chat/sessions/default", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "planning-001"
        assert data["title"] == "Planning"

    async def test_get_default_session_returns_existing(self, client, auth_headers):
        await client.post(
            "/api/chat/sessions",
            params={"title": "Custom"},
            headers=auth_headers,
        )
        resp = await client.get("/api/chat/sessions/default", headers=auth_headers)
        assert resp.json()["title"] == "Custom"

    async def test_unauthenticated_returns_error(self, client):
        resp = await client.get("/api/chat/sessions")
        assert resp.status_code in (401, 403)


class TestMessageEndpoints:
    async def test_get_messages_empty(self, client, auth_headers):
        await client.get("/api/chat/sessions/default", headers=auth_headers)
        resp = await client.get(
            "/api/chat/sessions/planning-001/messages",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_get_messages_session_not_found(self, client, auth_headers):
        resp = await client.get(
            "/api/chat/sessions/nonexistent/messages",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_update_message(self, client, auth_headers):
        # Create session and send a message via the service directly
        from pct.chat import service
        from pct.chat.models import PlanningMessage

        service.create_session("Test")
        msg = PlanningMessage(role="user", content="Hello")
        service.append_message("planning-001", msg)

        resp = await client.put(
            f"/api/chat/sessions/planning-001/messages/{msg.id}",
            json={"content": "Updated content", "included": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "Updated content"
        assert data["included"] is False

    async def test_update_message_not_found(self, client, auth_headers):
        from pct.chat import service

        service.create_session("Test")

        resp = await client.put(
            "/api/chat/sessions/planning-001/messages/nonexistent",
            json={"content": "x"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_update_message_session_not_found(self, client, auth_headers):
        resp = await client.put(
            "/api/chat/sessions/nonexistent/messages/abc",
            json={"content": "x"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_delete_message(self, client, auth_headers):
        from pct.chat import service
        from pct.chat.models import PlanningMessage

        service.create_session("Test")
        msg = PlanningMessage(role="user", content="To delete")
        service.append_message("planning-001", msg)

        resp = await client.delete(
            f"/api/chat/sessions/planning-001/messages/{msg.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204

        resp = await client.get(
            "/api/chat/sessions/planning-001/messages",
            headers=auth_headers,
        )
        assert resp.json() == []

    async def test_delete_message_not_found(self, client, auth_headers):
        from pct.chat import service

        service.create_session("Test")

        resp = await client.delete(
            "/api/chat/sessions/planning-001/messages/nonexistent",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_delete_message_session_not_found(self, client, auth_headers):
        resp = await client.delete(
            "/api/chat/sessions/nonexistent/messages/abc",
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestSendEndpoint:
    async def test_send_no_agent_configured(self, client, auth_headers):
        """When no agents are configured, SSE stream returns an error event."""
        from pct.chat import service

        service.create_session("Test")

        resp = await client.post(
            "/api/chat/sessions/planning-001/send",
            json={"content": "Hello"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        # Body should contain an error event
        body = resp.text
        assert "error" in body
        assert "No agent configured" in body

    async def test_send_session_not_found(self, client, auth_headers):
        resp = await client.post(
            "/api/chat/sessions/nonexistent/send",
            json={"content": "Hello"},
            headers=auth_headers,
        )
        assert resp.status_code == 404
