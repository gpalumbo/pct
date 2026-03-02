"""Integration tests -- multi-step API workflows end-to-end."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from pct.auth.dependencies import set_settings
from pct.auth.service import clear_users
from pct.config import Settings
from pct.main import app
from pct.models.core import Project
from pct.notifications.service import get_notification_service
from pct.storage.project_io import init_project


# -- Fixtures --


@pytest.fixture
def integration_settings(tmp_path):
    """Create a fully initialized project with workflow stages."""
    project = Project(
        id="integ-project",
        name="Integration Test Project",
        directory=str(tmp_path),
        workflow_stages=[
            {"id": "refine-spec", "label": "Refine Spec", "enabled": True, "sort_order": 0, "auto_run": False},
            {"id": "implement", "label": "Implement", "enabled": True, "sort_order": 1, "auto_run": False},
            {"id": "done", "label": "Done", "enabled": True, "sort_order": 2, "auto_run": False},
        ],
        artifact_types=[{"id": "text", "label": "Text"}],
    )
    settings = Settings(project_root=tmp_path, secret_key="test-secret")
    set_settings(settings)
    init_project(tmp_path, project)
    yield settings
    set_settings(None)


@pytest.fixture(autouse=True)
def reset_users():
    """Clear in-memory user store between tests."""
    clear_users()
    yield
    clear_users()


@pytest.fixture(autouse=True)
def reset_notifications():
    """Clear notification events between tests."""
    svc = get_notification_service()
    svc.clear_all()
    yield
    svc.clear_all()


@pytest.fixture
async def client(integration_settings):
    """Unauthenticated HTTP client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def register_and_login(client: AsyncClient) -> dict:
    """Register a user and return headers with JWT token."""
    await client.post("/api/auth/register", json={"email": "test@example.com", "password": "testpass123"})
    resp = await client.post("/api/auth/login", json={"email": "test@example.com", "password": "testpass123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def auth_client(integration_settings):
    """Authenticated HTTP client with a registered user."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await register_and_login(c)
        c.headers.update(headers)
        yield c
