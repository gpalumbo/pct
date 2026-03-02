"""Tests for project I/O — load/save pct.yaml, init project."""

from pathlib import Path

from pct.models.core import Project
from pct.storage.project_io import init_project, load_project_config, save_project_config


class TestProjectIO:
    def test_load_nonexistent(self, tmp_path: Path):
        assert load_project_config(tmp_path) is None

    def test_save_and_load_round_trip(self, tmp_path: Path):
        project = Project(id="test", name="Test Project", directory=str(tmp_path))
        save_project_config(tmp_path, project)
        loaded = load_project_config(tmp_path)
        assert loaded is not None
        assert loaded.id == "test"
        assert loaded.name == "Test Project"
        assert loaded.max_remote_agents == 2
        assert loaded.font_size == 14

    def test_init_project_creates_dirs(self, tmp_path: Path):
        project = Project(id="new-proj", name="New Project", directory=str(tmp_path))
        init_project(tmp_path, project)

        assert (tmp_path / "pct.yaml").exists()
        assert (tmp_path / "pct-admin" / "active-features").is_dir()
        assert (tmp_path / "pct-admin" / "feature_backlog").is_dir()
        assert (tmp_path / ".pct").is_dir()
        assert (tmp_path / "work").is_dir()
        assert (tmp_path / "pct-admin" / "project_spec.md").exists()
        assert (tmp_path / "work" / "INDEX.md").exists()

    def test_init_project_loads_back(self, tmp_path: Path):
        project = Project(id="round-trip", name="Round Trip", font_size=16)
        init_project(tmp_path, project)
        loaded = load_project_config(tmp_path)
        assert loaded is not None
        assert loaded.id == "round-trip"
        assert loaded.font_size == 16

    def test_save_overwrites(self, tmp_path: Path):
        p1 = Project(id="p", name="V1")
        save_project_config(tmp_path, p1)
        p2 = Project(id="p", name="V2")
        save_project_config(tmp_path, p2)
        loaded = load_project_config(tmp_path)
        assert loaded is not None
        assert loaded.name == "V2"

    def test_init_does_not_overwrite_existing_spec(self, tmp_path: Path):
        spec_path = tmp_path / "pct-admin" / "project_spec.md"
        spec_path.parent.mkdir(parents=True)
        spec_path.write_text("Existing spec", encoding="utf-8")

        project = Project(id="p", name="P")
        init_project(tmp_path, project)
        assert spec_path.read_text(encoding="utf-8") == "Existing spec"
