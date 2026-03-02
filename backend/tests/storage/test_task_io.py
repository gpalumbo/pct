"""Tests for task I/O — frontmatter markdown."""

from pathlib import Path

from pct.models.core import Task
from pct.models.enums import ExecutionStatus
from pct.storage.task_io import delete_task, list_tasks, load_task, load_task_body, save_task


class TestTaskIO:
    def test_save_and_load_round_trip(self, tmp_project_root: Path):
        task = Task(
            id="my-task",
            title="My Task",
            feature_id="f1",
            current_stage_id="implement",
            blocked_by=["[[f1#other-task]]"],
        )
        save_task(tmp_project_root, task, body="# My Task\n\nDo something.")
        loaded = load_task(tmp_project_root, "f1", "my-task")
        assert loaded is not None
        assert loaded.id == "my-task"
        assert loaded.title == "My Task"
        assert loaded.feature_id == "f1"
        assert loaded.blocked_by == ["[[f1#other-task]]"]

    def test_load_nonexistent(self, tmp_project_root: Path):
        assert load_task(tmp_project_root, "f1", "nonexistent") is None

    def test_load_task_body(self, tmp_project_root: Path):
        task = Task(id="t1", title="T", feature_id="f1", current_stage_id="implement")
        save_task(tmp_project_root, task, body="# Task Body\n\nContent here.")
        body = load_task_body(tmp_project_root, "f1", "t1")
        assert "Task Body" in body
        assert "Content here." in body

    def test_load_task_body_nonexistent(self, tmp_project_root: Path):
        assert load_task_body(tmp_project_root, "f1", "nope") == ""

    def test_list_tasks(self, tmp_project_root: Path):
        for i in range(3):
            task = Task(id=f"task-{i}", title=f"Task {i}", feature_id="f1", current_stage_id="implement")
            save_task(tmp_project_root, task)
        tasks = list_tasks(tmp_project_root, "f1")
        assert len(tasks) == 3
        assert {t.id for t in tasks} == {"task-0", "task-1", "task-2"}

    def test_list_tasks_empty(self, tmp_project_root: Path):
        assert list_tasks(tmp_project_root, "nonexistent") == []

    def test_delete_task(self, tmp_project_root: Path):
        task = Task(id="to-delete", title="Delete Me", feature_id="f1", current_stage_id="implement")
        save_task(tmp_project_root, task)
        assert delete_task(tmp_project_root, "f1", "to-delete") is True
        assert load_task(tmp_project_root, "f1", "to-delete") is None

    def test_delete_nonexistent(self, tmp_project_root: Path):
        assert delete_task(tmp_project_root, "f1", "nope") is False

    def test_missing_field_defaults(self, tmp_project_root: Path):
        """Task with only required fields should load with defaults."""
        task = Task(id="minimal", title="Min", feature_id="f1", current_stage_id="refine-spec")
        save_task(tmp_project_root, task)
        loaded = load_task(tmp_project_root, "f1", "minimal")
        assert loaded is not None
        assert loaded.execution_status == ExecutionStatus.idle
        assert loaded.is_bypassed is False
        assert loaded.blocked_by == []
