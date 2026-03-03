"""Tests for chat router."""

import pytest
from httpx import ASGITransport, AsyncClient

from pct.auth.dependencies import set_settings as set_auth_settings
from pct.auth.service import clear_users
from pct.config import Settings
from pct.config import set_settings as set_config_settings
from pct.main import app
from pct.models.core import Project
from pct.storage.project_io import init_project


@pytest.fixture
def chat_settings(tmp_path):
    project = Project(id="test", name="Test", directory=str(tmp_path))
    settings = Settings(project_root=tmp_path, secret_key="test-secret")
    set_auth_settings(settings)
    set_config_settings(settings)
    init_project(tmp_path, project)
    yield settings
    set_auth_settings(None)
    set_config_settings(Settings())


@pytest.fixture(autouse=True)
def reset_users():
    clear_users()
    yield
    clear_users()


@pytest.fixture
async def auth_client(chat_settings):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/auth/register", json={"email": "u@test.com", "password": "pass"})
        token = resp.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


class TestChatRouter:
    async def test_list_sessions(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/chat/sessions")
        assert resp.status_code == 200

    async def test_default_session(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/chat/sessions/default")
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data

    async def test_create_session(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/chat/sessions",
            json={"title": "Test", "session_id": "test-s"},
        )
        assert resp.status_code == 201
        assert resp.json()["id"] == "test-s"

    async def test_get_messages(self, auth_client: AsyncClient):
        await auth_client.post(
            "/api/chat/sessions", json={"title": "S1", "session_id": "s1"}
        )
        resp = await auth_client.get("/api/chat/sessions/s1/messages")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_send_message_no_agent(self, auth_client: AsyncClient):
        """Without an agent configured, SSE returns error."""
        await auth_client.post(
            "/api/chat/sessions", json={"title": "S1", "session_id": "s1"}
        )
        resp = await auth_client.post(
            "/api/chat/sessions/s1/send",
            json={"content": "Hello"},
        )
        assert resp.status_code == 200
        # SSE response — should contain error about no agent
        text = resp.text
        assert "data:" in text

    async def test_update_message(self, auth_client: AsyncClient):
        """Create a session, manually add a message, then update it."""
        await auth_client.post(
            "/api/chat/sessions", json={"title": "S1", "session_id": "s1"}
        )
        # Manually add a message via the service to get a message ID
        from pct.chat import service
        from pct.chat.models import PlanningMessage

        msg = PlanningMessage(role="user", content="Hi")
        service.append_message("s1", msg)

        resp = await auth_client.put(
            f"/api/chat/sessions/s1/messages/{msg.id}",
            json={"included": False},
        )
        assert resp.status_code == 200

    async def test_delete_message(self, auth_client: AsyncClient):
        await auth_client.post(
            "/api/chat/sessions", json={"title": "S1", "session_id": "s1"}
        )
        from pct.chat import service
        from pct.chat.models import PlanningMessage

        msg = PlanningMessage(role="user", content="Hi")
        service.append_message("s1", msg)

        resp = await auth_client.delete(f"/api/chat/sessions/s1/messages/{msg.id}")
        assert resp.status_code == 204
