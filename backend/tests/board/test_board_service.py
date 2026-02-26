"""Tests for the board service — Feature CRUD, Task CRUD, backlog, move, board assembly."""

import os

import pytest

from pct.board import service
from pct.board.models import (
    CreateFeatureRequest,
    CreateTaskRequest,
    FeatureMetadata,
    FeatureStage,
    MoveTaskRequest,
    UpdateFeatureMetadataRequest,
    UpdateTaskRequest,
)
from pct.config_models import ProjectConfig, WorkflowStageConfig
from pct.settings import service as settings_service


@pytest.fixture(autouse=True)
def _isolate_board(tmp_path):
    """Isolate project root for each test."""
    os.environ["PCT_PROJECT_ROOT"] = str(tmp_path / "project")
    os.environ["PCT_REGISTRIES_DIR"] = str(tmp_path / "registries")
    (tmp_path / "project" / ".pct").mkdir(parents=True)

    from pct import config

    config.settings = config.Settings()
    yield


def _setup_workflow_stages():
    """Set up workflow stages so move_task works."""
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
# Feature CRUD
# ---------------------------------------------------------------------------


class TestFeatureCRUD:
    def test_list_features_empty(self):
        assert service.list_features() == []

    def test_create_feature(self):
        req = CreateFeatureRequest(id="f1", title="Feature One", specification="# Feature One\nDetails here.")
        feature = service.create_feature(req)
        assert feature.id == "f1"
        assert feature.title == "Feature One"
        assert feature.metadata.lifecycle_stage == FeatureStage.PLANNING

    def test_list_features_returns_created(self):
        service.create_feature(CreateFeatureRequest(id="a", title="A", specification="# A"))
        service.create_feature(CreateFeatureRequest(id="b", title="B", specification="# B"))
        features = service.list_features()
        assert len(features) == 2

    def test_get_feature(self):
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        f = service.get_feature("f1")
        assert f is not None
        assert f.id == "f1"

    def test_get_feature_not_found(self):
        assert service.get_feature("nope") is None

    def test_update_feature_metadata(self):
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        updated = service.update_feature_metadata(
            "f1", UpdateFeatureMetadataRequest(lifecycle_stage=FeatureStage.ACTIVE)
        )
        assert updated is not None
        assert updated.metadata.lifecycle_stage == FeatureStage.ACTIVE

    def test_update_feature_metadata_not_found(self):
        assert (
            service.update_feature_metadata("nope", UpdateFeatureMetadataRequest(lifecycle_stage=FeatureStage.ACTIVE))
            is None
        )

    def test_delete_feature(self):
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        assert service.delete_feature("f1") is True
        assert service.get_feature("f1") is None

    def test_delete_feature_not_found(self):
        assert service.delete_feature("nope") is False

    def test_suspend_and_resume(self):
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))

        f = service.suspend_feature("f1")
        assert f is not None
        assert f.metadata.lifecycle_stage == FeatureStage.SUSPENDED

        f = service.resume_feature("f1")
        assert f is not None
        assert f.metadata.lifecycle_stage == FeatureStage.ACTIVE

    def test_create_with_custom_metadata(self):
        meta = FeatureMetadata(lifecycle_stage=FeatureStage.ACTIVE, branch="feat/test")
        req = CreateFeatureRequest(id="f1", title="F1", specification="# F1", metadata=meta)
        feature = service.create_feature(req)
        assert feature.metadata.lifecycle_stage == FeatureStage.ACTIVE
        assert feature.metadata.branch == "feat/test"


# ---------------------------------------------------------------------------
# Backlog CRUD
# ---------------------------------------------------------------------------


class TestBacklogCRUD:
    def test_list_backlog_empty(self):
        assert service.list_backlog() == []

    def test_create_and_list_backlog(self):
        from pct.board.models import BacklogFeature

        service.create_backlog_feature(
            BacklogFeature(id="b1", title="Backlog One", specification="# Backlog One\nTODO")
        )
        backlog = service.list_backlog()
        assert len(backlog) == 1
        assert backlog[0].id == "b1"

    def test_activate_backlog_feature(self):
        from pct.board.models import BacklogFeature

        service.create_backlog_feature(
            BacklogFeature(id="b1", title="Backlog One", specification="# Backlog One\nActivate me")
        )
        feature = service.activate_backlog_feature("b1")
        assert feature is not None
        assert feature.id == "b1"
        assert feature.metadata.lifecycle_stage == FeatureStage.PLANNING

        # Should be gone from backlog
        assert service.list_backlog() == []
        # Should appear in active features
        assert service.get_feature("b1") is not None

    def test_activate_backlog_not_found(self):
        assert service.activate_backlog_feature("nope") is None


# ---------------------------------------------------------------------------
# Task CRUD
# ---------------------------------------------------------------------------


class TestTaskCRUD:
    def test_create_task(self):
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        task = service.create_task("f1", CreateTaskRequest(title="My Task"))
        assert task is not None
        assert task.id == "001"
        assert task.title == "My Task"
        assert task.feature == "f1"

    def test_create_task_feature_not_found(self):
        assert service.create_task("nope", CreateTaskRequest(title="X")) is None

    def test_sequential_task_ids(self):
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        t1 = service.create_task("f1", CreateTaskRequest(title="First"))
        t2 = service.create_task("f1", CreateTaskRequest(title="Second"))
        assert t1 is not None and t1.id == "001"
        assert t2 is not None and t2.id == "002"

    def test_get_task(self):
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        service.create_task("f1", CreateTaskRequest(title="Task A"))
        t = service.get_task("f1", "001")
        assert t is not None
        assert t.title == "Task A"

    def test_get_task_not_found(self):
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        assert service.get_task("f1", "999") is None

    def test_list_tasks(self):
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        service.create_task("f1", CreateTaskRequest(title="A"))
        service.create_task("f1", CreateTaskRequest(title="B"))
        tasks = service.list_tasks("f1")
        assert len(tasks) == 2

    def test_update_task(self):
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        service.create_task("f1", CreateTaskRequest(title="Original"))
        updated = service.update_task("f1", "001", UpdateTaskRequest(title="Updated"))
        assert updated is not None
        assert updated.title == "Updated"

        # Verify persisted
        t = service.get_task("f1", "001")
        assert t is not None
        assert t.title == "Updated"

    def test_update_task_not_found(self):
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        assert service.update_task("f1", "999", UpdateTaskRequest(title="X")) is None

    def test_delete_task(self):
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        service.create_task("f1", CreateTaskRequest(title="Task"))
        assert service.delete_task("f1", "001") is True
        assert service.get_task("f1", "001") is None

    def test_delete_task_not_found(self):
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        assert service.delete_task("f1", "999") is False

    def test_task_frontmatter_roundtrip(self):
        """Verify task body and metadata survive a save/load cycle."""
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        service.create_task(
            "f1",
            CreateTaskRequest(
                title="Complex Task",
                status="implement",
                agent="coder",
                depends_on=["002"],
                tags=["backend", "api"],
                priority=5,
                body="## Implementation\n\nDo the thing.\n",
            ),
        )
        t = service.get_task("f1", "001")
        assert t is not None
        assert t.status == "implement"
        assert t.agent == "coder"
        assert t.depends_on == ["002"]
        assert t.tags == ["backend", "api"]
        assert t.priority == 5
        assert "Do the thing." in t.body

    def test_task_slug_generation(self):
        from pct.board.models import Task

        t = Task(id="001", title="My Cool Task!", feature="f1")
        assert t.slug == "my-cool-task"

    def test_create_task_generates_directory_path(self):
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        task = service.create_task("f1", CreateTaskRequest(title="My Task"))
        assert task is not None
        assert task.artifact_path.endswith("/")
        assert not task.artifact_path.endswith(".md")

    def test_read_artifact_directory_model(self, tmp_path):
        """read_artifact reads main.md from directory-based path."""
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        task = service.create_task("f1", CreateTaskRequest(title="Test Read"))
        assert task is not None

        # Write main.md manually into the artifact directory
        from pct.board.service import _project_root

        artifact_dir = _project_root() / task.artifact_path.rstrip("/")
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "main.md").write_text("# Hello", encoding="utf-8")

        result = service.read_artifact("f1", "001")
        assert result["exists"] is True
        assert result["content"] == "# Hello"
        assert result["path"] == task.artifact_path

    def test_write_artifact_directory_model(self, tmp_path):
        """write_artifact creates main.md inside directory-based path."""
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        task = service.create_task("f1", CreateTaskRequest(title="Test Write"))
        assert task is not None

        result = service.write_artifact("f1", "001", "# Written Content")
        assert result["exists"] is True
        assert result["path"] == task.artifact_path

        from pct.board.service import _project_root

        main_file = _project_root() / task.artifact_path.rstrip("/") / "main.md"
        assert main_file.exists()
        assert main_file.read_text(encoding="utf-8") == "# Written Content"

    def test_legacy_md_path_read_write(self, tmp_path):
        """Legacy .md paths still work for read/write."""
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        task = service.create_task(
            "f1",
            CreateTaskRequest(title="Legacy", artifact_path="work/legacy/task.md"),
        )
        assert task is not None

        result = service.write_artifact("f1", "001", "Legacy content")
        assert result["exists"] is True

        from pct.board.service import _project_root

        legacy_file = _project_root() / "work" / "legacy" / "task.md"
        assert legacy_file.exists()
        assert legacy_file.read_text(encoding="utf-8") == "Legacy content"

        result = service.read_artifact("f1", "001")
        assert result["content"] == "Legacy content"
        assert result["exists"] is True

    def test_list_artifact_files_directory(self, tmp_path):
        """list_artifact_files returns files in directory-based artifacts."""
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        task = service.create_task("f1", CreateTaskRequest(title="Files Test"))
        assert task is not None

        from pct.board.service import _project_root

        artifact_dir = _project_root() / task.artifact_path.rstrip("/")
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "main.md").write_text("# Hello", encoding="utf-8")
        images_dir = artifact_dir / "images"
        images_dir.mkdir()
        (images_dir / "test.png").write_text("fake png", encoding="utf-8")

        files = service.list_artifact_files("f1", "001")
        assert len(files) == 2
        names = {f["name"] for f in files}
        assert "main.md" in names
        assert "test.png" in names
        img_file = next(f for f in files if f["name"] == "test.png")
        assert img_file["is_image"] is True
        md_file = next(f for f in files if f["name"] == "main.md")
        assert md_file["is_image"] is False

    def test_list_artifact_files_legacy(self, tmp_path):
        """list_artifact_files works with legacy single-file paths."""
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        task = service.create_task(
            "f1",
            CreateTaskRequest(title="Legacy", artifact_path="work/legacy/file.md"),
        )
        assert task is not None

        from pct.board.service import _project_root

        legacy_file = _project_root() / "work" / "legacy" / "file.md"
        legacy_file.parent.mkdir(parents=True, exist_ok=True)
        legacy_file.write_text("content", encoding="utf-8")

        files = service.list_artifact_files("f1", "001")
        assert len(files) == 1
        assert files[0]["name"] == "file.md"
        assert files[0]["is_image"] is False

    def test_list_artifact_files_task_not_found(self):
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        files = service.list_artifact_files("f1", "999")
        assert files == []


# ---------------------------------------------------------------------------
# Move task
# ---------------------------------------------------------------------------


class TestMoveTask:
    def test_move_adjacent(self):
        _setup_workflow_stages()
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        service.create_task("f1", CreateTaskRequest(title="T", status="refine-spec"))

        t = service.move_task("f1", "001", MoveTaskRequest(new_status="implement"))
        assert t is not None
        assert t.status == "implement"

    def test_move_skip_requires_confirm(self):
        _setup_workflow_stages()
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        service.create_task("f1", CreateTaskRequest(title="T", status="refine-spec"))

        with pytest.raises(ValueError, match="confirm_skip"):
            service.move_task("f1", "001", MoveTaskRequest(new_status="code-review"))

    def test_move_skip_with_confirm(self):
        _setup_workflow_stages()
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        service.create_task("f1", CreateTaskRequest(title="T", status="refine-spec"))

        t = service.move_task("f1", "001", MoveTaskRequest(new_status="code-review", confirm_skip=True))
        assert t is not None
        assert t.status == "code-review"

    def test_move_to_disabled_stage(self):
        _setup_workflow_stages()
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        service.create_task("f1", CreateTaskRequest(title="T", status="refine-spec"))

        with pytest.raises(ValueError, match="not enabled"):
            service.move_task("f1", "001", MoveTaskRequest(new_status="merge"))

    def test_move_task_not_found(self):
        _setup_workflow_stages()
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        assert service.move_task("f1", "999", MoveTaskRequest(new_status="implement")) is None


# ---------------------------------------------------------------------------
# Board assembly
# ---------------------------------------------------------------------------


class TestBoardAssembly:
    def test_empty_board(self):
        _setup_workflow_stages()
        board = service.get_board()
        assert board.features == []
        assert board.backlog == []
        assert len(board.enabled_stages) == 4

    def test_board_includes_features_and_backlog(self):
        _setup_workflow_stages()
        service.create_feature(CreateFeatureRequest(id="f1", title="F1", specification="# F1"))
        service.create_task("f1", CreateTaskRequest(title="T1"))

        from pct.board.models import BacklogFeature

        service.create_backlog_feature(BacklogFeature(id="b1", title="B1", specification="# B1"))

        board = service.get_board()
        assert len(board.features) == 1
        assert len(board.features[0].tasks) == 1
        assert len(board.backlog) == 1
        assert "refine-spec" in board.enabled_stages
