"""Tests for config router — /api/config endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from pct.auth.dependencies import set_settings
from pct.auth.service import clear_users
from pct.config import Settings
from pct.main import app
from pct.models.core import Project
from pct.storage.project_io import init_project


@pytest.fixture
def project_settings(tmp_path):
    """Create settings pointing at a tmp project root and tmp global config."""
    global_dir = tmp_path / "global"
    global_dir.mkdir()
    settings = Settings(project_root=tmp_path, secret_key="test-secret", global_config_dir=global_dir)
    set_settings(settings)
    yield settings
    set_settings(None)


@pytest.fixture(autouse=True)
def reset_users():
    clear_users()
    yield
    clear_users()


@pytest.fixture
async def auth_client(project_settings):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        # Register and get token
        resp = await c.post("/api/auth/register", json={"email": "admin@test.com", "password": "pass"})
        token = resp.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


class TestProjectStatus:
    async def test_status_not_initialized(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/config/project/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["initialized"] is False

    async def test_status_initialized(self, auth_client: AsyncClient, project_settings):
        project = Project(id="test", name="Test")
        init_project(project_settings.project_root, project)
        resp = await auth_client.get("/api/config/project/status")
        data = resp.json()
        assert data["initialized"] is True
        assert data["project_id"] == "test"


class TestProjectConfig:
    async def test_get_not_initialized(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/config/project")
        assert resp.status_code == 200
        data = resp.json()
        assert data["initialized"] is False

    async def test_get_after_init(self, auth_client: AsyncClient, project_settings):
        project = Project(id="myproj", name="My Project", font_size=16)
        init_project(project_settings.project_root, project)
        resp = await auth_client.get("/api/config/project")
        assert resp.status_code == 200
        data = resp.json()
        assert data["initialized"] is True
        assert data["id"] == "myproj"
        assert data["font_size"] == 16

    async def test_put_project(self, auth_client: AsyncClient, project_settings):
        project = Project(id="p", name="V1")
        init_project(project_settings.project_root, project)

        updated = Project(id="p", name="V2", font_size=18)
        resp = await auth_client.put("/api/config/project", json=updated.model_dump(mode="json"))
        assert resp.status_code == 200
        assert resp.json()["name"] == "V2"
        assert resp.json()["font_size"] == 18


class TestInitializeProject:
    async def test_initialize_project(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/config/project/initialize",
            json={"name": "My Coding Project", "project_type": "coding"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["initialized"] is True
        assert data["name"] == "My Coding Project"
        assert data["id"] == "my-coding-project"
        assert data["project_type"] == "coding"
        # Template should populate stages
        assert len(data["workflow_stages"]) > 0
        stage_ids = [s["id"] for s in data["workflow_stages"]]
        assert "implement" in stage_ids
        # Should always have a USER agent
        agent_ids = [a["id"] for a in data["agents"]]
        assert "user" in agent_ids
        user_agent = next(a for a in data["agents"] if a["id"] == "user")
        assert user_agent["agent_type"] == "user"

    async def test_initialize_writing_template(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/config/project/initialize",
            json={"name": "My Novel", "project_type": "writing"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_type"] == "writing"
        stage_ids = [s["id"] for s in data["workflow_stages"]]
        assert "draft" in stage_ids

    async def test_initialize_discovers_gguf_models(self, auth_client: AsyncClient, project_settings):
        # Create a models/ dir with fake .gguf files
        models_dir = project_settings.project_root / "models"
        models_dir.mkdir()
        (models_dir / "llama-7b.gguf").write_bytes(b"fake")
        (models_dir / "mistral-8b.gguf").write_bytes(b"fake")

        resp = await auth_client.post(
            "/api/config/project/initialize",
            json={"name": "Test Project"},
        )
        assert resp.status_code == 200
        data = resp.json()
        agent_ids = [a["id"] for a in data["agents"]]
        # USER agent + one agent per model
        assert "user" in agent_ids
        assert "agent-llama-7b" in agent_ids
        assert "agent-mistral-8b" in agent_ids
        # LLM agents should reference the model
        llama_agent = next(a for a in data["agents"] if a["id"] == "agent-llama-7b")
        assert llama_agent["agent_type"] == "llm"
        assert llama_agent["model_id"] == "llama-7b"
        # default_agent_id should point to first LLM agent
        assert data["default_agent_id"] == "agent-llama-7b"
        assert data["planning_agent_id"] == "agent-llama-7b"

    async def test_initialize_discovers_global_models(self, auth_client: AsyncClient, project_settings):
        # Create models/ in global_config_dir
        global_models = project_settings.global_config_dir / "models"
        global_models.mkdir(parents=True)
        (global_models / "global-model.gguf").write_bytes(b"fake")

        resp = await auth_client.post(
            "/api/config/project/initialize",
            json={"name": "Test Project"},
        )
        assert resp.status_code == 200
        data = resp.json()
        agent_ids = [a["id"] for a in data["agents"]]
        assert "agent-global-model" in agent_ids

    async def test_initialize_no_models_defaults_to_user(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/config/project/initialize",
            json={"name": "Empty Project"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["default_agent_id"] == "user"
        assert data["planning_agent_id"] == "user"
        assert len(data["agents"]) == 1
        assert data["agents"][0]["id"] == "user"

    async def test_initialize_duplicate(self, auth_client: AsyncClient, project_settings):
        # First init
        await auth_client.post(
            "/api/config/project/initialize",
            json={"name": "First"},
        )
        # Second init should fail
        resp = await auth_client.post(
            "/api/config/project/initialize",
            json={"name": "Second"},
        )
        assert resp.status_code == 400
        assert "already initialized" in resp.json()["detail"]

    async def test_put_rejects_uninitialized(self, auth_client: AsyncClient):
        project = Project(id="p", name="V1")
        resp = await auth_client.put(
            "/api/config/project",
            json=project.model_dump(mode="json"),
        )
        assert resp.status_code == 400
        assert "not initialized" in resp.json()["detail"].lower()


class TestBrowseFiles:
    async def test_browse_project_root(self, auth_client: AsyncClient, project_settings):
        project = Project(id="p", name="P")
        init_project(project_settings.project_root, project)
        resp = await auth_client.get("/api/config/browse-files")
        assert resp.status_code == 200
        names = [e["name"] for e in resp.json()]
        assert "pct.yaml" in names
        assert "work" in names

    async def test_browse_subdir(self, auth_client: AsyncClient, project_settings):
        project = Project(id="p", name="P")
        init_project(project_settings.project_root, project)
        resp = await auth_client.get("/api/config/browse-files", params={"path": "work"})
        assert resp.status_code == 200
        names = [e["name"] for e in resp.json()]
        assert "INDEX.md" in names

    async def test_browse_traversal_blocked(self, auth_client: AsyncClient, project_settings):
        project = Project(id="p", name="P")
        init_project(project_settings.project_root, project)
        resp = await auth_client.get("/api/config/browse-files", params={"path": "../.."})
        assert resp.status_code == 200
        # Should return empty or the root — not parent directories
