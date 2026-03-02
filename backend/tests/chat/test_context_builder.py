"""Tests for context builder."""

from pathlib import Path

from pct.board.models import FeatureCreate, TaskCreate
from pct.board.service import BoardService
from pct.chat.context_builder import expand_template, resolve_task_context
from pct.models.core import Project
from pct.storage.project_io import init_project


class TestExpandTemplate:
    def test_basic_expansion(self):
        result = expand_template("Hello {{name}}", {"name": "World"})
        assert result == "Hello World"

    def test_missing_variable_left_as_is(self):
        result = expand_template("Hello {{unknown}}", {})
        assert result == "Hello {{unknown}}"

    def test_multiple_variables(self):
        result = expand_template("{{a}} and {{b}}", {"a": "X", "b": "Y"})
        assert result == "X and Y"

    def test_no_variables(self):
        result = expand_template("No variables here", {"a": "X"})
        assert result == "No variables here"


class TestResolveTaskContext:
    def test_basic_context(self, tmp_project_root: Path):
        project = Project(
            id="test",
            name="Test",
            workflow_stages=[
                {"id": "refine-spec", "label": "Refine Spec", "enabled": True, "sort_order": 0, "auto_run": False},
                {"id": "done", "label": "Done", "enabled": True, "sort_order": 1, "auto_run": False},
            ],
        )
        init_project(tmp_project_root, project)

        svc = BoardService(tmp_project_root)
        svc.create_feature(FeatureCreate(id="f1", title="Feature 1"))
        svc.create_task("f1", TaskCreate(id="t1", title="Task 1"))

        ctx = resolve_task_context(tmp_project_root, "f1", "t1")
        assert ctx["task_title"] == "Task 1"
        assert "f1/t1/" in ctx["artifact_work_dir"]

    def test_nonexistent_task(self, tmp_project_root: Path):
        ctx = resolve_task_context(tmp_project_root, "f1", "nope")
        assert ctx == {}

    def test_custom_variables(self, tmp_project_root: Path):
        project = Project(
            id="test",
            name="Test",
            workflow_stages=[
                {"id": "refine-spec", "label": "RS", "enabled": True, "sort_order": 0, "auto_run": False},
                {"id": "done", "label": "Done", "enabled": True, "sort_order": 1, "auto_run": False},
            ],
        )
        init_project(tmp_project_root, project)
        svc = BoardService(tmp_project_root)
        svc.create_feature(FeatureCreate(id="f1", title="F1"))
        svc.create_task("f1", TaskCreate(id="t1", title="T1"))

        ctx = resolve_task_context(
            tmp_project_root, "f1", "t1", custom_variables={"genre": "Fantasy"}
        )
        assert ctx["genre"] == "Fantasy"
        # Built-in should not be overridden by custom
        assert ctx["task_title"] == "T1"
