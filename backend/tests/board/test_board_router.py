"""Tests for board router — HTTP endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from pct.auth.dependencies import set_settings
from pct.auth.service import clear_users
from pct.config import Settings
from pct.main import app
from pct.models.core import Project
from pct.storage.project_io import init_project


@pytest.fixture
def board_settings(tmp_path):
    project = Project(
        id="test",
        name="Test",
        directory=str(tmp_path),
        workflow_stages=[
            {"id": "refine-spec", "label": "Refine Spec", "enabled": True, "sort_order": 0, "auto_run": False},
            {"id": "implement", "label": "Implement", "enabled": True, "sort_order": 1, "auto_run": False},
            {"id": "done", "label": "Done", "enabled": True, "sort_order": 2, "auto_run": False},
        ],
    )
    settings = Settings(project_root=tmp_path, secret_key="test-secret")
    set_settings(settings)
    init_project(tmp_path, project)
    yield settings
    set_settings(None)


@pytest.fixture(autouse=True)
def reset_users():
    clear_users()
    yield
    clear_users()


@pytest.fixture
async def auth_client(board_settings):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/auth/register", json={"email": "u@test.com", "password": "pass"})
        token = resp.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


class TestBoardRouter:
    async def test_get_board(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/board/")
        assert resp.status_code == 200
        data = resp.json()
        assert "features" in data
        assert "workflow_stages" in data

    async def test_feature_crud(self, auth_client: AsyncClient):
        # Create
        resp = await auth_client.post("/api/board/features", json={"id": "f1", "title": "Feature 1"})
        assert resp.status_code == 200
        assert resp.json()["id"] == "f1"

        # Get
        resp = await auth_client.get("/api/board/features/f1")
        assert resp.status_code == 200

        # Update
        resp = await auth_client.patch("/api/board/features/f1", json={"title": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"

        # Delete
        resp = await auth_client.delete("/api/board/features/f1")
        assert resp.status_code == 200

    async def test_task_crud(self, auth_client: AsyncClient):
        await auth_client.post("/api/board/features", json={"id": "f1", "title": "F1"})

        # Create task
        resp = await auth_client.post(
            "/api/board/features/f1/tasks",
            json={"id": "t1", "title": "Task 1"},
        )
        assert resp.status_code == 200

        # Get
        resp = await auth_client.get("/api/board/features/f1/tasks/t1")
        assert resp.status_code == 200

        # Update
        resp = await auth_client.put(
            "/api/board/features/f1/tasks/t1",
            json={"title": "Updated Task"},
        )
        assert resp.status_code == 200

        # Move
        resp = await auth_client.post(
            "/api/board/features/f1/tasks/t1/move",
            json={"target_stage_id": "implement"},
        )
        assert resp.status_code == 200
        assert resp.json()["current_stage_id"] == "implement"

        # Delete
        resp = await auth_client.delete("/api/board/features/f1/tasks/t1")
        assert resp.status_code == 200

    async def test_task_cycle_rejected(self, auth_client: AsyncClient):
        await auth_client.post("/api/board/features", json={"id": "f1", "title": "F1"})
        await auth_client.post("/api/board/features/f1/tasks", json={"id": "a", "title": "A"})
        await auth_client.post(
            "/api/board/features/f1/tasks",
            json={"id": "b", "title": "B", "blocked_by": ["[[f1#a]]"]},
        )
        # Now try to create a cycle: a depends on b
        resp = await auth_client.put(
            "/api/board/features/f1/tasks/a",
            json={"blocked_by": ["[[f1#b]]"]},
        )
        assert resp.status_code == 400

    async def test_suspend_resume(self, auth_client: AsyncClient):
        await auth_client.post("/api/board/features", json={"id": "f1", "title": "F1"})
        # Need to be active first
        await auth_client.patch("/api/board/features/f1", json={"stage": "active"})

        resp = await auth_client.post("/api/board/features/f1/suspend")
        assert resp.status_code == 200
        assert resp.json()["stage"] == "suspended"

        resp = await auth_client.post("/api/board/features/f1/resume")
        assert resp.status_code == 200
        assert resp.json()["stage"] == "active"
