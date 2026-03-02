"""Tests for directory manager."""

from pathlib import Path

from pct.storage.directory_manager import (
    create_feature_dir,
    create_task_work_dir,
    ensure_global_config_dir,
    ensure_project_dirs,
)


class TestDirectoryManager:
    def test_ensure_project_dirs(self, tmp_path: Path):
        ensure_project_dirs(tmp_path)
        assert (tmp_path / "pct-admin" / "active-features").is_dir()
        assert (tmp_path / "pct-admin" / "feature_backlog").is_dir()
        assert (tmp_path / ".pct" / "execution" / "active-tasks").is_dir()
        assert (tmp_path / ".pct" / "execution" / "completed-tasks").is_dir()
        assert (tmp_path / ".pct" / "chat_history").is_dir()
        assert (tmp_path / ".pct" / "rag").is_dir()
        assert (tmp_path / ".pct" / "kanban_snapshots").is_dir()
        assert (tmp_path / "work").is_dir()

    def test_ensure_project_dirs_idempotent(self, tmp_path: Path):
        ensure_project_dirs(tmp_path)
        ensure_project_dirs(tmp_path)  # Should not raise
        assert (tmp_path / "work").is_dir()

    def test_create_feature_dir(self, tmp_project_root: Path):
        work_dir = create_feature_dir(tmp_project_root, "f1-core")
        assert work_dir == tmp_project_root / "work" / "f1-core"
        assert work_dir.is_dir()
        assert (tmp_project_root / "pct-admin" / "active-features" / "f1-core" / "tasks").is_dir()

    def test_create_task_work_dir(self, tmp_project_root: Path):
        task_dir = create_task_work_dir(tmp_project_root, "f1", "define-models")
        assert task_dir == tmp_project_root / "work" / "f1" / "define-models"
        assert task_dir.is_dir()
        assert (task_dir / "images").is_dir()

    def test_ensure_global_config_dir(self, tmp_path: Path):
        ensure_global_config_dir(tmp_path)
        assert (tmp_path / "registries").is_dir()

    def test_ensure_global_config_dir_idempotent(self, tmp_path: Path):
        ensure_global_config_dir(tmp_path)
        ensure_global_config_dir(tmp_path)
        assert (tmp_path / "registries").is_dir()
