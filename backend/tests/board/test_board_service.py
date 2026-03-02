"""Tests for board service — feature/task CRUD, movement."""

from pathlib import Path

import pytest

from pct.board.dag_validation import CycleError
from pct.board.models import FeatureCreate, FeatureUpdate, TaskCreate, TaskMove, TaskUpdate
from pct.board.service import BoardService
from pct.models.core import Project
from pct.models.enums import ExecutionStatus, FeatureStage
from pct.storage.project_io import init_project


@pytest.fixture
def board_service(tmp_project_root: Path) -> BoardService:
    project = Project(
        id="test",
        name="Test",
        directory=str(tmp_project_root),
        workflow_stages=[
            {"id": "refine-spec", "label": "Refine Spec", "enabled": True, "sort_order": 0, "auto_run": False},
            {"id": "implement", "label": "Implement", "enabled": True, "sort_order": 1, "auto_run": False},
            {"id": "done", "label": "Done", "enabled": True, "sort_order": 2, "auto_run": False},
        ],
    )
    init_project(tmp_project_root, project)
    return BoardService(tmp_project_root)


class TestFeatureCRUD:
    def test_create_feature(self, board_service: BoardService):
        f = board_service.create_feature(FeatureCreate(id="f1", title="Feature 1"))
        assert f.id == "f1"
        assert f.stage == FeatureStage.planning

    def test_create_feature_creates_refine_task(self, board_service: BoardService):
        board_service.create_feature(FeatureCreate(id="f1", title="Feature 1"))
        task = board_service.get_task("f1", "refine-feature")
        assert task is not None
        assert task.current_stage_id == "refine-spec"

    def test_get_feature(self, board_service: BoardService):
        board_service.create_feature(FeatureCreate(id="f1", title="F1"))
        f = board_service.get_feature("f1")
        assert f is not None
        assert f.title == "F1"

    def test_get_nonexistent(self, board_service: BoardService):
        assert board_service.get_feature("nope") is None

    def test_update_feature(self, board_service: BoardService):
        board_service.create_feature(FeatureCreate(id="f1", title="V1"))
        f = board_service.update_feature("f1", FeatureUpdate(title="V2"))
        assert f is not None
        assert f.title == "V2"

    def test_delete_feature(self, board_service: BoardService):
        board_service.create_feature(FeatureCreate(id="f1", title="F1"))
        assert board_service.delete_feature("f1") is True
        assert board_service.get_feature("f1") is None

    def test_suspend_resume(self, board_service: BoardService):
        board_service.create_feature(FeatureCreate(id="f1", title="F1"))
        board_service.update_feature("f1", FeatureUpdate(stage=FeatureStage.active))
        f = board_service.suspend_feature("f1")
        assert f.stage == FeatureStage.suspended
        f = board_service.resume_feature("f1")
        assert f.stage == FeatureStage.active


class TestTaskCRUD:
    def test_create_task(self, board_service: BoardService):
        board_service.create_feature(FeatureCreate(id="f1", title="F1"))
        t = board_service.create_task("f1", TaskCreate(id="t1", title="Task 1"))
        assert t.id == "t1"
        assert t.current_stage_id == "refine-spec"

    def test_get_task(self, board_service: BoardService):
        board_service.create_feature(FeatureCreate(id="f1", title="F1"))
        board_service.create_task("f1", TaskCreate(id="t1", title="Task 1"))
        t = board_service.get_task("f1", "t1")
        assert t is not None
        assert t.title == "Task 1"

    def test_update_task(self, board_service: BoardService):
        board_service.create_feature(FeatureCreate(id="f1", title="F1"))
        board_service.create_task("f1", TaskCreate(id="t1", title="V1"))
        t = board_service.update_task("f1", "t1", TaskUpdate(title="V2"))
        assert t is not None
        assert t.title == "V2"

    def test_delete_task(self, board_service: BoardService):
        board_service.create_feature(FeatureCreate(id="f1", title="F1"))
        board_service.create_task("f1", TaskCreate(id="t1", title="T1"))
        assert board_service.delete_task_by_id("f1", "t1") is True

    def test_create_task_with_cycle_rejected(self, board_service: BoardService):
        board_service.create_feature(FeatureCreate(id="f1", title="F1"))
        board_service.create_task("f1", TaskCreate(id="a", title="A"))
        board_service.create_task("f1", TaskCreate(id="b", title="B", blocked_by=["[[f1#a]]"]))
        with pytest.raises(CycleError):
            board_service.create_task("f1", TaskCreate(id="c", title="C", blocked_by=["[[f1#b]]"]))
            board_service.update_task("f1", "a", TaskUpdate(blocked_by=["[[f1#c]]"]))


class TestTaskMovement:
    def test_advance_task(self, board_service: BoardService):
        board_service.create_feature(FeatureCreate(id="f1", title="F1"))
        board_service.create_task("f1", TaskCreate(id="t1", title="T1"))
        t = board_service.move_task("f1", "t1", TaskMove(target_stage_id="implement"))
        assert t is not None
        assert t.current_stage_id == "implement"
        assert t.execution_status == ExecutionStatus.idle

    def test_move_blocked_task_fails(self, board_service: BoardService):
        board_service.create_feature(FeatureCreate(id="f1", title="F1"))
        board_service.create_task("f1", TaskCreate(id="dep", title="Dep"))
        board_service.create_task("f1", TaskCreate(id="t1", title="T1", blocked_by=["[[f1#dep]]"]))
        t = board_service.move_task("f1", "t1", TaskMove(target_stage_id="implement"))
        assert t is None  # Blocked

    def test_bypass_blocked(self, board_service: BoardService):
        board_service.create_feature(FeatureCreate(id="f1", title="F1"))
        board_service.create_task("f1", TaskCreate(id="dep", title="Dep"))
        board_service.create_task("f1", TaskCreate(id="t1", title="T1", blocked_by=["[[f1#dep]]"]))
        t = board_service.move_task("f1", "t1", TaskMove(target_stage_id="implement", bypass=True))
        assert t is not None
        assert t.is_bypassed is True


class TestBoardState:
    def test_get_board_state(self, board_service: BoardService):
        board_service.create_feature(FeatureCreate(id="f1", title="F1"))
        state = board_service.get_board_state()
        assert "features" in state
        assert "workflow_stages" in state
        assert len(state["features"]) == 1
        assert len(state["workflow_stages"]) == 3
