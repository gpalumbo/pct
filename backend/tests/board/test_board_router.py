"""Tests for the board API router — endpoint status codes, 404/400 handling."""

import os

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def _isolate_board(tmp_path):
    """Isolate project root for each test."""
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
        json={"email": "board@test.com", "password": "testpass123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _setup_workflow_stages(tmp_path_like=None):
    """Set up workflow stages via the settings service."""
    from pct.config_models import ProjectConfig, WorkflowStageConfig
    from pct.settings import service as settings_service

    cfg = ProjectConfig(
        project_id="test",
        project_name="Test",
        workflow_stages=[
            WorkflowStageConfig(stage="refine-spec", enabled=True),
            WorkflowStageConfig(stage="implement", enabled=True),
            WorkflowStageConfig(stage="code-review", enabled=True),
            WorkflowStageConfig(stage="done", enabled=True),
        ],
    )
    settings_service.save_project_config(cfg)


# ---------------------------------------------------------------------------
# Board composite
# ---------------------------------------------------------------------------


class TestBoardEndpoint:
    @pytest.mark.anyio
    async def test_get_board(self, client, auth_headers):
        _setup_workflow_stages()
        resp = await client.get("/api/board/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "features" in data
        assert "backlog" in data
        assert "enabled_stages" in data

    @pytest.mark.anyio
    async def test_unauthenticated(self, client):
        resp = await client.get("/api/board/")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Feature endpoints
# ---------------------------------------------------------------------------


class TestFeatureEndpoints:
    @pytest.mark.anyio
    async def test_create_and_get_feature(self, client, auth_headers):
        req = {"id": "f1", "title": "Feature One", "specification": "# Feature One"}
        resp = await client.post("/api/board/features", json=req, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["id"] == "f1"

        resp = await client.get("/api/board/features/f1", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "Feature One"

    @pytest.mark.anyio
    async def test_list_features(self, client, auth_headers):
        await client.post(
            "/api/board/features",
            json={"id": "a", "title": "A", "specification": "# A"},
            headers=auth_headers,
        )
        resp = await client.get("/api/board/features", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @pytest.mark.anyio
    async def test_duplicate_feature_400(self, client, auth_headers):
        req = {"id": "f1", "title": "F1", "specification": "# F1"}
        await client.post("/api/board/features", json=req, headers=auth_headers)
        resp = await client.post("/api/board/features", json=req, headers=auth_headers)
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_get_feature_404(self, client, auth_headers):
        resp = await client.get("/api/board/features/nope", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_patch_feature(self, client, auth_headers):
        await client.post(
            "/api/board/features",
            json={"id": "f1", "title": "F1", "specification": "# F1"},
            headers=auth_headers,
        )
        resp = await client.patch(
            "/api/board/features/f1",
            json={"lifecycle_stage": "active"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["metadata"]["lifecycle_stage"] == "active"

    @pytest.mark.anyio
    async def test_delete_feature(self, client, auth_headers):
        await client.post(
            "/api/board/features",
            json={"id": "f1", "title": "F1", "specification": "# F1"},
            headers=auth_headers,
        )
        resp = await client.delete("/api/board/features/f1", headers=auth_headers)
        assert resp.status_code == 204

        resp = await client.get("/api/board/features/f1", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_delete_feature_404(self, client, auth_headers):
        resp = await client.delete("/api/board/features/nope", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_suspend_and_resume(self, client, auth_headers):
        await client.post(
            "/api/board/features",
            json={"id": "f1", "title": "F1", "specification": "# F1"},
            headers=auth_headers,
        )
        resp = await client.post("/api/board/features/f1/suspend", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["metadata"]["lifecycle_stage"] == "suspended"

        resp = await client.post("/api/board/features/f1/resume", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["metadata"]["lifecycle_stage"] == "active"


# ---------------------------------------------------------------------------
# Backlog endpoints
# ---------------------------------------------------------------------------


class TestBacklogEndpoints:
    @pytest.mark.anyio
    async def test_list_backlog_empty(self, client, auth_headers):
        resp = await client.get("/api/board/backlog", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_activate_backlog_feature(self, client, auth_headers):
        # Create a backlog feature by writing a file directly
        from pct.board.models import BacklogFeature
        from pct.board import service

        service.create_backlog_feature(
            BacklogFeature(id="b1", title="B1", specification="# B1\nBacklog spec")
        )

        resp = await client.post("/api/board/backlog/b1/activate", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == "b1"

    @pytest.mark.anyio
    async def test_activate_backlog_404(self, client, auth_headers):
        resp = await client.post("/api/board/backlog/nope/activate", headers=auth_headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Task endpoints
# ---------------------------------------------------------------------------


class TestTaskEndpoints:
    @pytest.mark.anyio
    async def test_create_and_get_task(self, client, auth_headers):
        await client.post(
            "/api/board/features",
            json={"id": "f1", "title": "F1", "specification": "# F1"},
            headers=auth_headers,
        )
        resp = await client.post(
            "/api/board/features/f1/tasks",
            json={"title": "My Task"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        task_id = resp.json()["id"]

        resp = await client.get(
            f"/api/board/features/f1/tasks/{task_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "My Task"

    @pytest.mark.anyio
    async def test_list_tasks(self, client, auth_headers):
        await client.post(
            "/api/board/features",
            json={"id": "f1", "title": "F1", "specification": "# F1"},
            headers=auth_headers,
        )
        await client.post(
            "/api/board/features/f1/tasks",
            json={"title": "T1"},
            headers=auth_headers,
        )
        resp = await client.get("/api/board/features/f1/tasks", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @pytest.mark.anyio
    async def test_list_tasks_feature_404(self, client, auth_headers):
        resp = await client.get("/api/board/features/nope/tasks", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_update_task(self, client, auth_headers):
        await client.post(
            "/api/board/features",
            json={"id": "f1", "title": "F1", "specification": "# F1"},
            headers=auth_headers,
        )
        await client.post(
            "/api/board/features/f1/tasks",
            json={"title": "Original"},
            headers=auth_headers,
        )
        resp = await client.put(
            "/api/board/features/f1/tasks/001",
            json={"title": "Updated"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"

    @pytest.mark.anyio
    async def test_update_task_404(self, client, auth_headers):
        await client.post(
            "/api/board/features",
            json={"id": "f1", "title": "F1", "specification": "# F1"},
            headers=auth_headers,
        )
        resp = await client.put(
            "/api/board/features/f1/tasks/999",
            json={"title": "X"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_delete_task(self, client, auth_headers):
        await client.post(
            "/api/board/features",
            json={"id": "f1", "title": "F1", "specification": "# F1"},
            headers=auth_headers,
        )
        await client.post(
            "/api/board/features/f1/tasks",
            json={"title": "T1"},
            headers=auth_headers,
        )
        resp = await client.delete("/api/board/features/f1/tasks/001", headers=auth_headers)
        assert resp.status_code == 204

    @pytest.mark.anyio
    async def test_delete_task_404(self, client, auth_headers):
        await client.post(
            "/api/board/features",
            json={"id": "f1", "title": "F1", "specification": "# F1"},
            headers=auth_headers,
        )
        resp = await client.delete("/api/board/features/f1/tasks/999", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_move_task_adjacent(self, client, auth_headers):
        _setup_workflow_stages()
        await client.post(
            "/api/board/features",
            json={"id": "f1", "title": "F1", "specification": "# F1"},
            headers=auth_headers,
        )
        await client.post(
            "/api/board/features/f1/tasks",
            json={"title": "T1", "status": "refine-spec"},
            headers=auth_headers,
        )
        resp = await client.post(
            "/api/board/features/f1/tasks/001/move",
            json={"new_status": "implement"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "implement"

    @pytest.mark.anyio
    async def test_move_task_skip_400(self, client, auth_headers):
        _setup_workflow_stages()
        await client.post(
            "/api/board/features",
            json={"id": "f1", "title": "F1", "specification": "# F1"},
            headers=auth_headers,
        )
        await client.post(
            "/api/board/features/f1/tasks",
            json={"title": "T1", "status": "refine-spec"},
            headers=auth_headers,
        )
        resp = await client.post(
            "/api/board/features/f1/tasks/001/move",
            json={"new_status": "code-review"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_move_task_skip_with_confirm(self, client, auth_headers):
        _setup_workflow_stages()
        await client.post(
            "/api/board/features",
            json={"id": "f1", "title": "F1", "specification": "# F1"},
            headers=auth_headers,
        )
        await client.post(
            "/api/board/features/f1/tasks",
            json={"title": "T1", "status": "refine-spec"},
            headers=auth_headers,
        )
        resp = await client.post(
            "/api/board/features/f1/tasks/001/move",
            json={"new_status": "code-review", "confirm_skip": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "code-review"
