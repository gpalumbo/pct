# Tests for training router -- HTTP endpoints.

import pytest
from httpx import ASGITransport, AsyncClient

from pct.auth.dependencies import set_settings
from pct.auth.service import clear_users
from pct.config import Settings
from pct.main import app


@pytest.fixture
def training_settings(tmp_path):
    (tmp_path / ".pct").mkdir()
    settings = Settings(project_root=tmp_path, secret_key="test-secret")
    set_settings(settings)
    yield settings
    set_settings(None)


@pytest.fixture(autouse=True)
def reset_users():
    clear_users()
    yield
    clear_users()


@pytest.fixture
async def auth_client(training_settings):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/auth/register", json={"email": "u@test.com", "password": "pass"})
        token = resp.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


class TestFlagRouter:
    async def test_create_flag(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/training/flags",
            json={"session_ref": "s1", "message_index": 0, "flag_type": "positive"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["flag_type"] == "positive"
        assert data["id"]

    async def test_list_flags(self, auth_client: AsyncClient):
        await auth_client.post(
            "/api/training/flags",
            json={"session_ref": "s1", "message_index": 0, "flag_type": "positive"},
        )
        resp = await auth_client.get("/api/training/flags")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_list_flags_filter(self, auth_client: AsyncClient):
        await auth_client.post(
            "/api/training/flags",
            json={"session_ref": "s1", "message_index": 0, "flag_type": "positive"},
        )
        await auth_client.post(
            "/api/training/flags",
            json={"session_ref": "s2", "message_index": 1, "flag_type": "negative"},
        )
        resp = await auth_client.get("/api/training/flags", params={"flag_type": "positive"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_get_flag(self, auth_client: AsyncClient):
        create_resp = await auth_client.post(
            "/api/training/flags",
            json={"session_ref": "s1", "message_index": 0, "flag_type": "positive"},
        )
        flag_id = create_resp.json()["id"]
        resp = await auth_client.get(f"/api/training/flags/{flag_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == flag_id

    async def test_get_flag_404(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/training/flags/nonexistent")
        assert resp.status_code == 404

    async def test_update_flag(self, auth_client: AsyncClient):
        create_resp = await auth_client.post(
            "/api/training/flags",
            json={"session_ref": "s1", "message_index": 0, "flag_type": "positive"},
        )
        flag_id = create_resp.json()["id"]
        resp = await auth_client.put(
            f"/api/training/flags/{flag_id}",
            json={"curation_status": "curated", "note": "Good example"},
        )
        assert resp.status_code == 200
        assert resp.json()["curation_status"] == "curated"

    async def test_update_flag_404(self, auth_client: AsyncClient):
        resp = await auth_client.put(
            "/api/training/flags/nonexistent",
            json={"note": "x"},
        )
        assert resp.status_code == 404

    async def test_delete_flag(self, auth_client: AsyncClient):
        create_resp = await auth_client.post(
            "/api/training/flags",
            json={"session_ref": "s1", "message_index": 0, "flag_type": "positive"},
        )
        flag_id = create_resp.json()["id"]
        resp = await auth_client.delete(f"/api/training/flags/{flag_id}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    async def test_delete_flag_404(self, auth_client: AsyncClient):
        resp = await auth_client.delete("/api/training/flags/nonexistent")
        assert resp.status_code == 404

class TestDatasetRouter:
    async def test_create_dataset(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/training/datasets",
            json={"name": "DS1", "description": "Test"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "DS1"

    async def test_list_datasets(self, auth_client: AsyncClient):
        await auth_client.post("/api/training/datasets", json={"name": "DS1"})
        resp = await auth_client.get("/api/training/datasets")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_get_dataset(self, auth_client: AsyncClient):
        create_resp = await auth_client.post("/api/training/datasets", json={"name": "DS1"})
        ds_id = create_resp.json()["id"]
        resp = await auth_client.get(f"/api/training/datasets/{ds_id}")
        assert resp.status_code == 200

    async def test_get_dataset_404(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/training/datasets/nonexistent")
        assert resp.status_code == 404

    async def test_update_dataset(self, auth_client: AsyncClient):
        create_resp = await auth_client.post("/api/training/datasets", json={"name": "V1"})
        ds_id = create_resp.json()["id"]
        resp = await auth_client.put(
            f"/api/training/datasets/{ds_id}",
            json={"name": "V2", "entry_ids": ["f1", "f2"]},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "V2"
        assert resp.json()["entries"] == ["f1", "f2"]

    async def test_update_dataset_404(self, auth_client: AsyncClient):
        resp = await auth_client.put(
            "/api/training/datasets/nonexistent", json={"name": "x"}
        )
        assert resp.status_code == 404

    async def test_delete_dataset(self, auth_client: AsyncClient):
        create_resp = await auth_client.post("/api/training/datasets", json={"name": "DS1"})
        ds_id = create_resp.json()["id"]
        resp = await auth_client.delete(f"/api/training/datasets/{ds_id}")
        assert resp.status_code == 200

    async def test_delete_dataset_404(self, auth_client: AsyncClient):
        resp = await auth_client.delete("/api/training/datasets/nonexistent")
        assert resp.status_code == 404


class TestPromptTemplateRouter:
    async def test_create_template(self, auth_client: AsyncClient):
        resp = await auth_client.post(
            "/api/training/prompt-templates",
            json={"name": "T1", "content": "You are helpful."},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "T1"
        assert resp.json()["active_version"] == 1

    async def test_list_templates(self, auth_client: AsyncClient):
        await auth_client.post(
            "/api/training/prompt-templates",
            json={"name": "T1", "content": "c1"},
        )
        resp = await auth_client.get("/api/training/prompt-templates")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_get_template(self, auth_client: AsyncClient):
        create_resp = await auth_client.post(
            "/api/training/prompt-templates",
            json={"name": "T1", "content": "c1"},
        )
        tmpl_id = create_resp.json()["id"]
        resp = await auth_client.get(f"/api/training/prompt-templates/{tmpl_id}")
        assert resp.status_code == 200

    async def test_get_template_404(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/training/prompt-templates/nonexistent")
        assert resp.status_code == 404

    async def test_update_template_creates_version(self, auth_client: AsyncClient):
        create_resp = await auth_client.post(
            "/api/training/prompt-templates",
            json={"name": "T1", "content": "v1"},
        )
        tmpl_id = create_resp.json()["id"]
        resp = await auth_client.put(
            f"/api/training/prompt-templates/{tmpl_id}",
            json={"content": "v2"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_version"] == 2
        assert len(data["versions"]) == 2

    async def test_update_template_404(self, auth_client: AsyncClient):
        resp = await auth_client.put(
            "/api/training/prompt-templates/nonexistent",
            json={"content": "x"},
        )
        assert resp.status_code == 404
