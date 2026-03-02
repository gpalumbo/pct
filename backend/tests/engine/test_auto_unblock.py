"""Tests for auto-unblock — completion triggers downstream unblock."""

from __future__ import annotations

from pathlib import Path

import pytest

from pct.board.models import FeatureCreate, TaskCreate, TaskMove
from pct.board.service import BoardService
from pct.engine.auto_unblock import check_unblocked
from pct.models.core import Project
from pct.models.enums import ExecutionStatus
from pct.storage.project_io import init_project
from pct.storage.task_io import load_task, save_task


@pytest.fixture
def project_root(tmp_project_root: Path) -> Path:
    """Initialize project with auto_run stages."""
    project = Project(
        id="test",
        name="Test",
        directory=str(tmp_project_root),
        workflow_stages=[
            {
                "id": "refine-spec",
                "label": "Refine Spec",
                "enabled": True,
                "auto_run": True,
                "sort_order": 0,
            },
            {
                "id": "implement",
                "label": "Implement",
                "enabled": True,
                "auto_run": True,
                "sort_order": 1,
            },
            {
                "id": "done",
                "label": "Done",
                "enabled": True,
                "auto_run": False,
                "sort_order": 2,
            },
        ],
    )
    init_project(tmp_project_root, project)
    return tmp_project_root


@pytest.fixture
def board_svc(project_root: Path) -> BoardService:
    return BoardService(project_root)


class TestCheckUnblocked:
    def test_downstream_task_queued_on_dependency_completion(
        self, project_root: Path, board_svc: BoardService
    ):
        """When a dependency completes, downstream task gets queued."""
        board_svc.create_feature(FeatureCreate(id="f1", title="F1"))
        board_svc.create_task("f1", TaskCreate(id="dep", title="Dependency"))
        board_svc.create_task(
            "f1",
            TaskCreate(id="t1", title="Task 1", blocked_by=["[[f1#dep]]"]),
        )

        # Move dep to done
        board_svc.move_task("f1", "dep", TaskMove(target_stage_id="done"))

        # Check unblocked
        newly_queued = check_unblocked(project_root, "f1", "dep")

        assert len(newly_queued) == 1
        assert newly_queued[0] == ("f1", "t1")

        # Verify task is now queued
        task = load_task(project_root, "f1", "t1")
        assert task is not None
        assert task.execution_status == ExecutionStatus.queued

    def test_no_unblock_when_other_deps_pending(
        self, project_root: Path, board_svc: BoardService
    ):
        """Task stays blocked if only one of multiple deps completes."""
        board_svc.create_feature(FeatureCreate(id="f1", title="F1"))
        board_svc.create_task("f1", TaskCreate(id="dep1", title="Dep 1"))
        board_svc.create_task("f1", TaskCreate(id="dep2", title="Dep 2"))
        board_svc.create_task(
            "f1",
            TaskCreate(
                id="t1",
                title="Task 1",
                blocked_by=["[[f1#dep1]]", "[[f1#dep2]]"],
            ),
        )

        # Only complete dep1
        board_svc.move_task("f1", "dep1", TaskMove(target_stage_id="done"))

        newly_queued = check_unblocked(project_root, "f1", "dep1")
        assert len(newly_queued) == 0

        # Task should still be idle
        task = load_task(project_root, "f1", "t1")
        assert task is not None
        assert task.execution_status == ExecutionStatus.idle

    def test_unblock_after_all_deps_complete(
        self, project_root: Path, board_svc: BoardService
    ):
        """Task gets queued when all dependencies are done."""
        board_svc.create_feature(FeatureCreate(id="f1", title="F1"))
        board_svc.create_task("f1", TaskCreate(id="dep1", title="Dep 1"))
        board_svc.create_task("f1", TaskCreate(id="dep2", title="Dep 2"))
        board_svc.create_task(
            "f1",
            TaskCreate(
                id="t1",
                title="Task 1",
                blocked_by=["[[f1#dep1]]", "[[f1#dep2]]"],
            ),
        )

        # Complete both deps
        board_svc.move_task("f1", "dep1", TaskMove(target_stage_id="done"))
        board_svc.move_task("f1", "dep2", TaskMove(target_stage_id="done"))

        newly_queued = check_unblocked(project_root, "f1", "dep2")
        assert len(newly_queued) == 1
        assert newly_queued[0] == ("f1", "t1")

    def test_no_unblock_on_non_auto_run_stage(
        self, project_root: Path, board_svc: BoardService
    ):
        """Tasks at non-auto_run stages don't get auto-queued."""
        # Reconfigure project with non-auto_run stages
        project = Project(
            id="test",
            name="Test",
            directory=str(project_root),
            workflow_stages=[
                {
                    "id": "refine-spec",
                    "label": "Refine Spec",
                    "enabled": True,
                    "auto_run": False,
                    "sort_order": 0,
                },
                {
                    "id": "implement",
                    "label": "Implement",
                    "enabled": True,
                    "auto_run": False,
                    "sort_order": 1,
                },
                {
                    "id": "done",
                    "label": "Done",
                    "enabled": True,
                    "auto_run": False,
                    "sort_order": 2,
                },
            ],
        )
        from pct.storage.project_io import save_project_config

        save_project_config(project_root, project)

        board_svc = BoardService(project_root)
        board_svc.create_feature(FeatureCreate(id="f2", title="F2"))
        board_svc.create_task("f2", TaskCreate(id="dep", title="Dependency"))
        board_svc.create_task(
            "f2",
            TaskCreate(id="t1", title="Task 1", blocked_by=["[[f2#dep]]"]),
        )

        board_svc.move_task("f2", "dep", TaskMove(target_stage_id="done"))

        newly_queued = check_unblocked(project_root, "f2", "dep")
        assert len(newly_queued) == 0

    def test_cross_feature_unblock(
        self, project_root: Path, board_svc: BoardService
    ):
        """Tasks in different features can unblock each other."""
        board_svc.create_feature(FeatureCreate(id="f1", title="F1"))
        board_svc.create_feature(FeatureCreate(id="f2", title="F2"))
        board_svc.create_task("f1", TaskCreate(id="dep", title="Dep in F1"))
        board_svc.create_task(
            "f2",
            TaskCreate(id="t1", title="Task in F2", blocked_by=["[[f1#dep]]"]),
        )

        # Complete dep in f1
        board_svc.move_task("f1", "dep", TaskMove(target_stage_id="done"))

        newly_queued = check_unblocked(project_root, "f1", "dep")
        assert len(newly_queued) == 1
        assert newly_queued[0] == ("f2", "t1")

    def test_no_double_queue(
        self, project_root: Path, board_svc: BoardService
    ):
        """Already-queued tasks don't get re-queued."""
        board_svc.create_feature(FeatureCreate(id="f1", title="F1"))
        board_svc.create_task("f1", TaskCreate(id="dep", title="Dependency"))
        board_svc.create_task(
            "f1",
            TaskCreate(id="t1", title="Task 1", blocked_by=["[[f1#dep]]"]),
        )

        # Pre-queue the task
        task = load_task(project_root, "f1", "t1")
        assert task is not None
        task.execution_status = ExecutionStatus.queued
        save_task(project_root, task)

        board_svc.move_task("f1", "dep", TaskMove(target_stage_id="done"))

        newly_queued = check_unblocked(project_root, "f1", "dep")
        assert len(newly_queued) == 0  # Already queued
