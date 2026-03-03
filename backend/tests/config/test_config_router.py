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
    pct_root = tmp_path / "pct_root"
    pct_root.mkdir()
    settings = Settings(project_root=tmp_path, secret_key="test-secret", global_config_dir=global_dir, root=pct_root)
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
        # Create a models/ dir with fake .gguf files — top-level and in subdirectories
        models_dir = project_settings.project_root / "models"
        models_dir.mkdir()
        (models_dir / "llama-7b.gguf").write_bytes(b"fake")
        subdir = models_dir / "mistral"
        subdir.mkdir()
        (subdir / "mistral-8b.gguf").write_bytes(b"fake")

        resp = await auth_client.post(
            "/api/config/project/initialize",
            json={"name": "Test Project"},
        )
        assert resp.status_code == 200
        data = resp.json()
        agent_ids = [a["id"] for a in data["agents"]]
        # USER agent + one agent per model (including subdirectory)
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
        # Create models/ in PCT deployment directory ($PCT_ROOT)
        root_models = project_settings.root / "models"
        root_models.mkdir(parents=True)
        (root_models / "global-model.gguf").write_bytes(b"fake")

        resp = await auth_client.post(
            "/api/config/project/initialize",
            json={"name": "Test Project"},
        )
        assert resp.status_code == 200
        data = resp.json()
        agent_ids = [a["id"] for a in data["agents"]]
        assert "agent-global-model" in agent_ids

    async def test_split_gguf_registers_first_shard_only(self, auth_client: AsyncClient, project_settings):
        models_dir = project_settings.project_root / "models"
        models_dir.mkdir()
        # Two shards of the same model — only the first should be registered
        (models_dir / "qwen2.5-7b-instruct-q5_k_m-00001-of-00002.gguf").write_bytes(b"fake")
        (models_dir / "qwen2.5-7b-instruct-q5_k_m-00002-of-00002.gguf").write_bytes(b"fake")

        resp = await auth_client.post(
            "/api/config/project/initialize",
            json={"name": "Test Project"},
        )
        assert resp.status_code == 200
        data = resp.json()
        agent_ids = [a["id"] for a in data["agents"]]
        # Should register one model with the base name (no shard suffix)
        assert "agent-qwen2.5-7b-instruct-q5_k_m" in agent_ids
        # Should NOT have a second entry for the second shard
        model_ids = [a["model_id"] for a in data["agents"] if a["agent_type"] == "llm"]
        assert model_ids.count("qwen2.5-7b-instruct-q5_k_m") == 1

    async def test_discovers_diffusers_safetensor_model(self, auth_client: AsyncClient, project_settings):
        models_dir = project_settings.project_root / "models"
        model_dir = models_dir / "stable-diffusion-xl"
        model_dir.mkdir(parents=True)
        # Diffusers pipeline marker
        (model_dir / "model_index.json").write_text('{"_class_name": "StableDiffusionXLPipeline"}')
        (model_dir / "unet").mkdir()
        (model_dir / "unet" / "diffusion_pytorch_model.safetensors").write_bytes(b"fake")

        resp = await auth_client.post(
            "/api/config/project/initialize",
            json={"name": "Test Project"},
        )
        assert resp.status_code == 200
        data = resp.json()
        agent_ids = [a["id"] for a in data["agents"]]
        assert "agent-stable-diffusion-xl" in agent_ids
        # file_path should point to the directory, not a file
        sdxl_agent = next(a for a in data["agents"] if a["id"] == "agent-stable-diffusion-xl")
        model_id = sdxl_agent["model_id"]
        # Verify via the registry that file_path is the directory
        from pct.storage.registry_io import load_model_registry
        models = load_model_registry(project_settings.global_config_dir)
        sdxl_model = next(m for m in models if m.id == model_id)
        assert sdxl_model.file_path == str(model_dir)

    async def test_discovers_sharded_safetensor_model(self, auth_client: AsyncClient, project_settings):
        models_dir = project_settings.project_root / "models"
        model_dir = models_dir / "Qwen2.5-7B-Instruct"
        model_dir.mkdir(parents=True)
        # Sharded LLM marker
        (model_dir / "model.safetensors.index.json").write_text('{"metadata": {}, "weight_map": {}}')
        (model_dir / "config.json").write_text('{}')
        (model_dir / "model-00001-of-00002.safetensors").write_bytes(b"fake")
        (model_dir / "model-00002-of-00002.safetensors").write_bytes(b"fake")

        resp = await auth_client.post(
            "/api/config/project/initialize",
            json={"name": "Test Project"},
        )
        assert resp.status_code == 200
        data = resp.json()
        agent_ids = [a["id"] for a in data["agents"]]
        assert "agent-qwen2.5-7b-instruct" in agent_ids

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


class TestModelRegistry:
    async def test_list_empty(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/config/models")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_model(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/config/models", json={
            "name": "GPT-4o",
            "provider_type": "remote_api",
            "model_identifier": "gpt-4o",
            "context_length": 128000,
            "api_base_url": "https://api.openai.com/v1",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "GPT-4o"
        assert data["provider_type"] == "remote_api"
        assert data["model_identifier"] == "gpt-4o"
        assert data["context_length"] == 128000
        assert data["api_base_url"] == "https://api.openai.com/v1"
        assert "id" in data

    async def test_create_then_list(self, auth_client: AsyncClient):
        await auth_client.post("/api/config/models", json={
            "name": "Llama 3",
            "provider_type": "local",
            "model_identifier": "llama-3",
            "context_length": 8192,
        })
        resp = await auth_client.get("/api/config/models")
        assert resp.status_code == 200
        models = resp.json()
        assert len(models) == 1
        assert models[0]["name"] == "Llama 3"

    async def test_update_model(self, auth_client: AsyncClient):
        create_resp = await auth_client.post("/api/config/models", json={
            "name": "Old Name",
            "provider_type": "local",
            "model_identifier": "old-id",
            "context_length": 4096,
        })
        model_id = create_resp.json()["id"]

        resp = await auth_client.put(f"/api/config/models/{model_id}", json={
            "name": "New Name",
            "context_length": 8192,
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"
        assert resp.json()["context_length"] == 8192
        # Unchanged fields preserved
        assert resp.json()["provider_type"] == "local"
        assert resp.json()["model_identifier"] == "old-id"

    async def test_update_not_found(self, auth_client: AsyncClient):
        resp = await auth_client.put("/api/config/models/nonexistent", json={
            "name": "X",
        })
        assert resp.status_code == 404

    async def test_delete_model(self, auth_client: AsyncClient):
        create_resp = await auth_client.post("/api/config/models", json={
            "name": "Doomed",
            "provider_type": "local",
            "model_identifier": "doomed",
            "context_length": 4096,
        })
        model_id = create_resp.json()["id"]

        resp = await auth_client.delete(f"/api/config/models/{model_id}")
        assert resp.status_code == 204

        # Verify it's gone
        list_resp = await auth_client.get("/api/config/models")
        assert len(list_resp.json()) == 0

    async def test_delete_not_found(self, auth_client: AsyncClient):
        resp = await auth_client.delete("/api/config/models/nonexistent")
        assert resp.status_code == 404

    async def test_persists_across_requests(self, auth_client: AsyncClient):
        """Verify data survives across multiple requests (file-backed)."""
        await auth_client.post("/api/config/models", json={
            "name": "Model A",
            "provider_type": "remote_api",
            "model_identifier": "a",
            "context_length": 4096,
        })
        await auth_client.post("/api/config/models", json={
            "name": "Model B",
            "provider_type": "local",
            "model_identifier": "b",
            "context_length": 8192,
        })
        resp = await auth_client.get("/api/config/models")
        assert len(resp.json()) == 2
        names = {m["name"] for m in resp.json()}
        assert names == {"Model A", "Model B"}


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
