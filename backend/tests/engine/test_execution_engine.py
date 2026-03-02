"""Tests for execution engine — execute_task, dequeue_next."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from pct.agent.models import AgentResult, TaskOutcome
from pct.board.models import FeatureCreate, TaskCreate
from pct.board.service import BoardService
from pct.engine.execution import dequeue_next, execute_task
from pct.models.core import Project
from pct.models.enums import ExecutionStatus
from pct.storage.project_io import init_project
from pct.storage.task_io import load_task, save_task


@pytest.fixture
def project_root(tmp_project_root: Path) -> Path:
    """Initialize a project with workflow stages."""
    project = Project(
        id="test",
        name="Test",
        directory=str(tmp_project_root),
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


class TestExecuteTask:
    @pytest.mark.asyncio
    async def test_execute_task_no_provider_succeeds(
        self, project_root: Path, board_svc: BoardService
    ):
        """When no provider is configured, execute_task returns stub success."""
        board_svc.create_feature(FeatureCreate(id="f1", title="F1"))
        board_svc.create_task("f1", TaskCreate(id="t1", title="Task 1"))

        result = await execute_task(project_root, "f1", "t1")

        assert result.outcome == TaskOutcome.success
        # Task should be advanced to next stage
        task = load_task(project_root, "f1", "t1")
        assert task is not None
        assert task.current_stage_id == "implement"
        assert task.execution_status == ExecutionStatus.idle

    @pytest.mark.asyncio
    async def test_execute_task_not_found(self, project_root: Path):
        """execute_task returns failure for non-existent task."""
        result = await execute_task(project_root, "f1", "nonexistent")
        assert result.outcome == TaskOutcome.failure
        assert "not found" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_execute_task_with_mock_provider(
        self, project_root: Path, board_svc: BoardService
    ):
        """execute_task with a mock provider that returns success."""
        board_svc.create_feature(FeatureCreate(id="f1", title="F1"))
        board_svc.create_task("f1", TaskCreate(id="t1", title="Task 1"))

        mock_result = AgentResult(
            outcome=TaskOutcome.success,
            output="Mock output",
            tokens_input=100,
            tokens_output=50,
            duration_seconds=1.5,
        )

        with patch(
            "pct.engine.execution._resolve_provider"
        ) as mock_resolve, patch(
            "pct.engine.execution.execute_chat_turn",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            mock_provider = AsyncMock()
            mock_resolve.return_value = mock_provider

            result = await execute_task(project_root, "f1", "t1")

        assert result.outcome == TaskOutcome.success
        assert result.output == "Mock output"

        task = load_task(project_root, "f1", "t1")
        assert task is not None
        assert task.current_stage_id == "implement"

    @pytest.mark.asyncio
    async def test_execute_task_failure_sets_error_status(
        self, project_root: Path, board_svc: BoardService
    ):
        """On failure, task gets execution_status=error and error_details."""
        board_svc.create_feature(FeatureCreate(id="f1", title="F1"))
        board_svc.create_task("f1", TaskCreate(id="t1", title="Task 1"))

        mock_result = AgentResult(
            outcome=TaskOutcome.failure,
            error="Something went wrong",
            duration_seconds=0.5,
        )

        with patch(
            "pct.engine.execution._resolve_provider"
        ) as mock_resolve, patch(
            "pct.engine.execution.execute_chat_turn",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            mock_provider = AsyncMock()
            mock_resolve.return_value = mock_provider

            result = await execute_task(project_root, "f1", "t1")

        assert result.outcome == TaskOutcome.failure

        task = load_task(project_root, "f1", "t1")
        assert task is not None
        assert task.execution_status == ExecutionStatus.error
        assert task.error_details is not None
        assert "Something went wrong" in task.error_details.message

    @pytest.mark.asyncio
    async def test_execute_task_writes_attempt(
        self, project_root: Path, board_svc: BoardService
    ):
        """execute_task should write an attempt record."""
        board_svc.create_feature(FeatureCreate(id="f1", title="F1"))
        board_svc.create_task("f1", TaskCreate(id="t1", title="Task 1"))

        await execute_task(project_root, "f1", "t1")

        # Check attempt directory exists
        attempts_dir = project_root / ".pct" / "execution" / "active-tasks" / "t1"
        assert attempts_dir.exists()
        attempt_dirs = list(attempts_dir.glob("attempt-*"))
        assert len(attempt_dirs) >= 1


class TestDequeueNext:
    def test_dequeue_returns_queued_task(
        self, project_root: Path, board_svc: BoardService
    ):
        """dequeue_next returns the first queued, unblocked task."""
        board_svc.create_feature(FeatureCreate(id="f1", title="F1"))
        board_svc.create_task("f1", TaskCreate(id="t1", title="Task 1"))

        # Set task to queued
        task = load_task(project_root, "f1", "t1")
        assert task is not None
        task.execution_status = ExecutionStatus.queued
        save_task(project_root, task)

        result = dequeue_next(project_root)
        assert result is not None
        assert result == ("f1", "t1")

    def test_dequeue_skips_non_queued(
        self, project_root: Path, board_svc: BoardService
    ):
        """dequeue_next skips tasks that are idle or running."""
        board_svc.create_feature(FeatureCreate(id="f1", title="F1"))
        board_svc.create_task("f1", TaskCreate(id="t1", title="Task 1"))

        result = dequeue_next(project_root)
        assert result is None  # Task is idle by default

    def test_dequeue_skips_blocked_task(
        self, project_root: Path, board_svc: BoardService
    ):
        """dequeue_next skips queued tasks whose dependencies are not done."""
        board_svc.create_feature(FeatureCreate(id="f1", title="F1"))
        board_svc.create_task("f1", TaskCreate(id="dep", title="Dependency"))
        board_svc.create_task(
            "f1",
            TaskCreate(id="t1", title="Task 1", blocked_by=["[[f1#dep]]"]),
        )

        # Queue the blocked task
        task = load_task(project_root, "f1", "t1")
        assert task is not None
        task.execution_status = ExecutionStatus.queued
        save_task(project_root, task)

        result = dequeue_next(project_root)
        assert result is None  # Blocked

    def test_dequeue_empty_project(self, project_root: Path):
        """dequeue_next returns None when there are no features/tasks."""
        result = dequeue_next(project_root)
        assert result is None
