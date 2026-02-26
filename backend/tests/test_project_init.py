"""Tests for project initialization flow."""

import os

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    resp = await client.post(
        "/api/auth/register",
        json={"email": "init@test.com", "password": "testpass123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _isolate_config(tmp_path):
    """Isolate registries, project root, and PCT_ROOT to tmp_path."""
    os.environ["PCT_REGISTRIES_DIR"] = str(tmp_path / "registries")
    os.environ["PCT_PROJECT_ROOT"] = str(tmp_path / "project")
    os.environ["PCT_ROOT"] = str(tmp_path / "pct_root")
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


def _save_project(tmp_path):
    """Helper: call save_project_config with a coding project type."""
    from pct.config_models import ProjectConfig
    from pct.settings.service import save_project_config

    cfg = ProjectConfig(
        project_name="Test Project",
        project_type="coding",
    )
    return save_project_config(cfg)


# ---------------------------------------------------------------------------
# TestProjectInitEmpty — empty directory
# ---------------------------------------------------------------------------


class TestProjectInitEmpty:
    def test_init_derives_project_id_from_dir(self, tmp_path):
        cfg = _save_project(tmp_path)
        assert cfg.project_id == "project"

    def test_init_creates_workflow_stages(self, tmp_path):
        cfg = _save_project(tmp_path)
        assert len(cfg.workflow_stages) == 8
        assert cfg.workflow_stages[0].stage == "refine-spec"

    def test_init_creates_user_agent(self, tmp_path):
        cfg = _save_project(tmp_path)
        agent_ids = {a.id for a in cfg.agents}
        assert "user" in agent_ids

    def test_init_discovers_gguf_models(self, tmp_path):
        # Place a .gguf file in project models dir
        models_dir = tmp_path / "project" / "models"
        models_dir.mkdir(parents=True)
        (models_dir / "llama-7b.gguf").write_text("fake model", encoding="utf-8")

        cfg = _save_project(tmp_path)

        # Check model was registered
        from pct.settings.service import list_models
        model_ids = {m.id for m in list_models()}
        assert "llama-7b" in model_ids

        # Check agent was created
        agent_ids = {a.id for a in cfg.agents}
        assert "llama-7b" in agent_ids

    def test_init_discovers_pct_root_models(self, tmp_path):
        # Place a .gguf file in PCT_ROOT/models
        pct_root_models = tmp_path / "pct_root" / "models"
        pct_root_models.mkdir(parents=True)
        (pct_root_models / "mistral-7b.gguf").write_text("fake model", encoding="utf-8")

        cfg = _save_project(tmp_path)

        from pct.settings.service import list_models
        model_ids = {m.id for m in list_models()}
        assert "mistral-7b" in model_ids

        agent_ids = {a.id for a in cfg.agents}
        assert "mistral-7b" in agent_ids

    def test_init_discovers_nested_model_dir(self, tmp_path):
        # Layout: models/qwen2.5-7b/qwen2.5-7b-instruct-q5_k_m-00001-of-00002.gguf
        model_dir = tmp_path / "project" / "models" / "qwen2.5-7b"
        model_dir.mkdir(parents=True)
        (model_dir / "qwen2.5-7b-instruct-q5_k_m-00001-of-00002.gguf").write_text("shard1", encoding="utf-8")
        (model_dir / "qwen2.5-7b-instruct-q5_k_m-00002-of-00002.gguf").write_text("shard2", encoding="utf-8")

        cfg = _save_project(tmp_path)

        from pct.settings.service import list_models
        model_ids = {m.id for m in list_models()}
        assert "qwen2.5-7b" in model_ids

        # model_path should point to the directory, not individual shard
        model = next(m for m in list_models() if m.id == "qwen2.5-7b")
        assert model.model_path == str(model_dir)

        agent_ids = {a.id for a in cfg.agents}
        assert "qwen2.5-7b" in agent_ids

    def test_init_creates_work_index(self, tmp_path):
        _save_project(tmp_path)
        index_path = tmp_path / "project" / "work" / "INDEX.md"
        assert index_path.exists()
        content = index_path.read_text(encoding="utf-8")
        assert "# Work Artifacts Index" in content

    def test_init_creates_initial_feature_and_tasks(self, tmp_path):
        _save_project(tmp_path)
        feature_dir = tmp_path / "project" / ".pct" / "active-features" / "f1-project-setup"
        assert feature_dir.exists()
        tasks_dir = feature_dir / "tasks"
        assert tasks_dir.exists()
        task_files = list(tasks_dir.iterdir())
        assert len(task_files) == 4

    def test_task_artifact_path_uses_work(self, tmp_path):
        _save_project(tmp_path)
        tasks_dir = (
            tmp_path / "project" / ".pct" / "active-features" / "f1-project-setup" / "tasks"
        )
        import frontmatter
        for p in tasks_dir.iterdir():
            if p.suffix == ".md":
                post = frontmatter.load(str(p))
                artifact_path = post.metadata.get("artifact_path", "")
                assert artifact_path.startswith("work/"), f"Expected work/ prefix: {artifact_path}"
                assert not artifact_path.endswith(".md"), f"Expected directory path (no .md): {artifact_path}"


# ---------------------------------------------------------------------------
# TestProjectInitWithExistingWork
# ---------------------------------------------------------------------------


class TestProjectInitWithExistingWork:
    def test_init_indexes_existing_work(self, tmp_path):
        # Create a pre-existing work file
        work_dir = tmp_path / "project" / "work"
        work_dir.mkdir(parents=True)
        (work_dir / "notes.md").write_text("# My Notes\nSome content.", encoding="utf-8")

        _save_project(tmp_path)

        index_path = work_dir / "INDEX.md"
        assert index_path.exists()
        content = index_path.read_text(encoding="utf-8")
        assert "notes.md" in content

    @pytest.mark.anyio
    async def test_reindex_endpoint(self, client, auth_headers, tmp_path):
        # First save a project config
        cfg = {
            "project_name": "Test",
            "project_type": "coding",
        }
        resp = await client.put("/api/config/project", json=cfg, headers=auth_headers)
        assert resp.status_code == 200

        # Create a work file
        work_dir = tmp_path / "project" / "work"
        work_dir.mkdir(parents=True, exist_ok=True)
        (work_dir / "test.md").write_text("# Test\nContent.", encoding="utf-8")

        # Call reindex endpoint
        resp = await client.post("/api/config/project/reindex", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "indexed" in data


# ---------------------------------------------------------------------------
# TestProjectDirectory
# ---------------------------------------------------------------------------


class TestProjectDirectory:
    @pytest.mark.anyio
    async def test_project_status_shows_directory(self, client, auth_headers, tmp_path):
        resp = await client.get("/api/config/project/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "project_directory" in data
        assert data["project_directory"] == str(tmp_path / "project")

    @pytest.mark.anyio
    async def test_project_config_includes_directory(self, client, auth_headers, tmp_path):
        cfg = {
            "project_name": "Dir Test",
            "project_type": "coding",
        }
        resp = await client.put("/api/config/project", json=cfg, headers=auth_headers)
        assert resp.status_code == 200

        resp = await client.get("/api/config/project", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "project_directory" in data
        assert data["project_directory"] == str(tmp_path / "project")
