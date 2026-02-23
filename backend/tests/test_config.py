"""Tests for the configuration API — model registry, LoRA registry, agents, workflow stages, project config."""

import os

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register a user and return Bearer auth headers."""
    resp = await client.post(
        "/api/auth/register",
        json={"email": "cfg@test.com", "password": "testpass123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _isolate_config(tmp_path):
    """Isolate registries and project root to tmp_path for each test."""
    os.environ["PCT_REGISTRIES_DIR"] = str(tmp_path / "registries")
    os.environ["PCT_PROJECT_ROOT"] = str(tmp_path / "project")
    # Create .pct dir inside project root
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


# ---------------------------------------------------------------------------
# Model Registry
# ---------------------------------------------------------------------------


class TestModelRegistry:
    @pytest.mark.anyio
    async def test_list_models_empty(self, client, auth_headers):
        resp = await client.get("/api/config/models", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_create_and_get_model(self, client, auth_headers):
        model = {
            "id": "gpt4",
            "provider_type": "remote",
            "model_id": "gpt-4",
            "context_length": 128000,
            "api_base": "https://api.openai.com",
        }
        resp = await client.post("/api/config/models", json=model, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["id"] == "gpt4"

        resp = await client.get("/api/config/models/gpt4", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["model_id"] == "gpt-4"

    @pytest.mark.anyio
    async def test_duplicate_model_returns_400(self, client, auth_headers):
        model = {
            "id": "dup",
            "provider_type": "local",
            "model_id": "llama-7b",
            "context_length": 4096,
            "model_path": "/models/llama-7b.gguf",
        }
        await client.post("/api/config/models", json=model, headers=auth_headers)
        resp = await client.post("/api/config/models", json=model, headers=auth_headers)
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_update_model(self, client, auth_headers):
        model = {
            "id": "m1",
            "provider_type": "remote",
            "model_id": "gpt-3.5",
            "context_length": 4096,
        }
        await client.post("/api/config/models", json=model, headers=auth_headers)

        updated = {**model, "context_length": 16384}
        resp = await client.put("/api/config/models/m1", json=updated, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["context_length"] == 16384

    @pytest.mark.anyio
    async def test_local_model_requires_model_path(self, client, auth_headers):
        model = {
            "id": "no-path",
            "provider_type": "local",
            "model_id": "llama-7b",
            "context_length": 4096,
        }
        resp = await client.post("/api/config/models", json=model, headers=auth_headers)
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_delete_model(self, client, auth_headers):
        model = {
            "id": "todel",
            "provider_type": "local",
            "model_id": "llama-7b",
            "context_length": 4096,
            "model_path": "/models/llama-7b.gguf",
        }
        await client.post("/api/config/models", json=model, headers=auth_headers)
        resp = await client.delete("/api/config/models/todel", headers=auth_headers)
        assert resp.status_code == 204

        resp = await client.get("/api/config/models/todel", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_get_model_404(self, client, auth_headers):
        resp = await client.get("/api/config/models/nope", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_unauthenticated_returns_401(self, client):
        resp = await client.get("/api/config/models")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# LoRA Registry
# ---------------------------------------------------------------------------


class TestLoRARegistry:
    @pytest.mark.anyio
    async def test_lora_crud_lifecycle(self, client, auth_headers):
        lora = {
            "id": "code-lora",
            "base_model": "llama-7b",
            "path": "/models/loras/code.bin",
            "description": "Code generation LoRA",
        }
        # Create
        resp = await client.post("/api/config/loras", json=lora, headers=auth_headers)
        assert resp.status_code == 201

        # List
        resp = await client.get("/api/config/loras", headers=auth_headers)
        assert len(resp.json()) == 1

        # Get
        resp = await client.get("/api/config/loras/code-lora", headers=auth_headers)
        assert resp.json()["description"] == "Code generation LoRA"

        # Update
        updated = {**lora, "description": "Updated description"}
        resp = await client.put("/api/config/loras/code-lora", json=updated, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated description"

        # Delete
        resp = await client.delete("/api/config/loras/code-lora", headers=auth_headers)
        assert resp.status_code == 204

        resp = await client.get("/api/config/loras/code-lora", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_duplicate_lora_returns_400(self, client, auth_headers):
        lora = {
            "id": "dup-lora",
            "base_model": "llama-7b",
            "path": "/path",
        }
        await client.post("/api/config/loras", json=lora, headers=auth_headers)
        resp = await client.post("/api/config/loras", json=lora, headers=auth_headers)
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


class TestAgents:
    @pytest.mark.anyio
    async def test_create_and_list_agents(self, client, auth_headers):
        # Save a project config first so agents have a place to live
        cfg = {
            "project_id": "test-proj",
            "project_name": "Test Project",
            "project_type": "python",
        }
        await client.put("/api/config/project", json=cfg, headers=auth_headers)

        agent = {
            "id": "coder",
            "agent_type": "llm",
            "provider_type": "remote",
            "model": "gpt-4",
        }
        resp = await client.post("/api/config/agents", json=agent, headers=auth_headers)
        assert resp.status_code == 201

        resp = await client.get("/api/config/agents", headers=auth_headers)
        assert len(resp.json()) == 1
        assert resp.json()[0]["id"] == "coder"

    @pytest.mark.anyio
    async def test_duplicate_agent_returns_400(self, client, auth_headers):
        cfg = {"project_id": "p", "project_name": "P", "project_type": "py"}
        await client.put("/api/config/project", json=cfg, headers=auth_headers)

        agent = {
            "id": "dup-agent",
            "agent_type": "llm",
            "provider_type": "local",
            "model": "llama",
        }
        await client.post("/api/config/agents", json=agent, headers=auth_headers)
        resp = await client.post("/api/config/agents", json=agent, headers=auth_headers)
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_update_and_delete_agent(self, client, auth_headers):
        cfg = {"project_id": "p", "project_name": "P", "project_type": "py"}
        await client.put("/api/config/project", json=cfg, headers=auth_headers)

        agent = {
            "id": "a1",
            "agent_type": "llm",
            "provider_type": "remote",
            "model": "gpt-4",
        }
        await client.post("/api/config/agents", json=agent, headers=auth_headers)

        updated = {**agent, "model": "gpt-4o"}
        resp = await client.put("/api/config/agents/a1", json=updated, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["model"] == "gpt-4o"

        resp = await client.delete("/api/config/agents/a1", headers=auth_headers)
        assert resp.status_code == 204

        resp = await client.get("/api/config/agents/a1", headers=auth_headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Workflow Stages
# ---------------------------------------------------------------------------


class TestWorkflowStages:
    @pytest.mark.anyio
    async def test_save_and_get_stages(self, client, auth_headers):
        cfg = {"project_id": "p", "project_name": "P", "project_type": "py"}
        await client.put("/api/config/project", json=cfg, headers=auth_headers)

        stages = [
            {"stage": "implement", "enabled": True, "agent": "coder"},
            {"stage": "code-review", "enabled": True, "agent": "reviewer"},
            {"stage": "merge", "enabled": False},
        ]
        resp = await client.put("/api/config/workflow-stages", json=stages, headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 3

        resp = await client.get("/api/config/workflow-stages", headers=auth_headers)
        assert len(resp.json()) == 3
        assert resp.json()[0]["stage"] == "implement"


# ---------------------------------------------------------------------------
# Project Config
# ---------------------------------------------------------------------------


class TestProjectConfig:
    @pytest.mark.anyio
    async def test_project_config_null_when_missing(self, client, auth_headers, tmp_path):
        # Remove the .pct dir to simulate missing config
        import shutil
        pct_dir = tmp_path / "project" / ".pct"
        if pct_dir.exists():
            shutil.rmtree(pct_dir)
        # Re-create .pct dir but without pct.yaml
        pct_dir.mkdir(parents=True, exist_ok=True)

        resp = await client.get("/api/config/project", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() is None

    @pytest.mark.anyio
    async def test_save_and_get_project_config(self, client, auth_headers):
        cfg = {
            "project_id": "my-proj",
            "project_name": "My Project",
            "project_type": "python",
            "auto_advance": False,
            "concurrency": {"remote_api_limit": 4, "local_gpu_limit": 2},
        }
        resp = await client.put("/api/config/project", json=cfg, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["project_id"] == "my-proj"

        resp = await client.get("/api/config/project", headers=auth_headers)
        data = resp.json()
        assert data["project_name"] == "My Project"
        assert data["auto_advance"] is False
        assert data["concurrency"]["remote_api_limit"] == 4
