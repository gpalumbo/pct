"""Tests for todo tools: TodoReadTool, TodoCreateTool, TodoEditTool."""

from __future__ import annotations

import json

import frontmatter
import pytest

from pct.agent.tools.todo_tools import TodoCreateTool, TodoEditTool, TodoReadTool


def _setup_feature(tmp_path, feature_id="001-test-feature"):
    """Create a .pct/active-features/<feature>/tasks/ structure."""
    tasks_dir = tmp_path / ".pct" / "active-features" / feature_id / "tasks"
    tasks_dir.mkdir(parents=True)
    return tasks_dir


def _create_task_file(tasks_dir, task_id, title, status="refine-spec", body="Task body."):
    """Write a task markdown file with frontmatter."""
    slug = title.lower().replace(" ", "-")
    metadata = {
        "id": task_id,
        "title": title,
        "feature": tasks_dir.parent.name,
        "status": status,
        "depends_on": [],
        "tags": [],
        "priority": 0,
        "created": "2026-01-01T00:00:00+00:00",
        "updated": "2026-01-01T00:00:00+00:00",
    }
    post = frontmatter.Post(body, **metadata)
    filepath = tasks_dir / f"{task_id}-{slug}.md"
    filepath.write_text(frontmatter.dumps(post), encoding="utf-8")
    return filepath


class TestTodoReadTool:
    async def test_list_tasks(self, tmp_path):
        tasks_dir = _setup_feature(tmp_path)
        _create_task_file(tasks_dir, "001", "First task")
        _create_task_file(tasks_dir, "002", "Second task", status="implement")

        tool = TodoReadTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({"feature_id": "001-test-feature"})
        )
        assert "001" in result
        assert "002" in result
        assert "First task" in result
        assert "Second task" in result

    async def test_read_single_task(self, tmp_path):
        tasks_dir = _setup_feature(tmp_path)
        _create_task_file(tasks_dir, "001", "My task", body="Detailed spec here.")

        tool = TodoReadTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({"feature_id": "001-test-feature", "task_id": "001"})
        )
        data = json.loads(result)
        assert data["id"] == "001"
        assert data["title"] == "My task"
        assert "Detailed spec" in data["body"]

    async def test_read_missing_feature(self, tmp_path):
        tool = TodoReadTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({"feature_id": "nonexistent"})
        )
        assert "No tasks directory" in result

    async def test_read_missing_task(self, tmp_path):
        _setup_feature(tmp_path)
        tool = TodoReadTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({"feature_id": "001-test-feature", "task_id": "999"})
        )
        assert "[error]" in result

    def test_definition_schema(self, tmp_path):
        tool = TodoReadTool(root_dir=tmp_path)
        defn = tool.definition
        assert defn["function"]["name"] == "todo_read"
        assert "feature_id" in defn["function"]["parameters"]["required"]


class TestTodoCreateTool:
    async def test_create_first_task(self, tmp_path):
        # Pre-create the feature dir but not the tasks dir
        (tmp_path / ".pct" / "active-features" / "001-feat").mkdir(parents=True)

        tool = TodoCreateTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({
                "feature_id": "001-feat",
                "title": "Build the widget",
                "body": "## Spec\nBuild it well.",
                "priority": 2,
                "tags": ["backend"],
            })
        )
        assert "Created task 001" in result

        # Verify file was created
        tasks_dir = tmp_path / ".pct" / "active-features" / "001-feat" / "tasks"
        files = list(tasks_dir.glob("001-*.md"))
        assert len(files) == 1
        post = frontmatter.load(str(files[0]))
        assert post.metadata["title"] == "Build the widget"
        assert post.metadata["priority"] == 2
        assert post.metadata["tags"] == ["backend"]
        assert post.metadata["status"] == "refine-spec"

    async def test_create_auto_increments_id(self, tmp_path):
        tasks_dir = _setup_feature(tmp_path)
        _create_task_file(tasks_dir, "001", "First")
        _create_task_file(tasks_dir, "002", "Second")

        tool = TodoCreateTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({
                "feature_id": "001-test-feature",
                "title": "Third task",
                "body": "Body.",
            })
        )
        assert "Created task 003" in result

    def test_definition_schema(self, tmp_path):
        tool = TodoCreateTool(root_dir=tmp_path)
        defn = tool.definition
        assert defn["function"]["name"] == "todo_create"


class TestTodoEditTool:
    async def test_edit_status(self, tmp_path):
        tasks_dir = _setup_feature(tmp_path)
        _create_task_file(tasks_dir, "001", "Task one", status="refine-spec")

        tool = TodoEditTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({
                "feature_id": "001-test-feature",
                "task_id": "001",
                "status": "implement",
            })
        )
        assert "Updated task 001" in result

        # Verify
        filepath = list(tasks_dir.glob("001-*.md"))[0]
        post = frontmatter.load(str(filepath))
        assert post.metadata["status"] == "implement"

    async def test_edit_updates_timestamp(self, tmp_path):
        tasks_dir = _setup_feature(tmp_path)
        _create_task_file(tasks_dir, "001", "Task one")

        tool = TodoEditTool(root_dir=tmp_path)
        await tool.execute(
            json.dumps({
                "feature_id": "001-test-feature",
                "task_id": "001",
                "title": "Renamed",
            })
        )

        filepath = list(tasks_dir.glob("001-*.md"))[0]
        post = frontmatter.load(str(filepath))
        assert post.metadata["title"] == "Renamed"
        # Updated timestamp should differ from original
        assert post.metadata["updated"] != "2026-01-01T00:00:00+00:00"

    async def test_edit_body(self, tmp_path):
        tasks_dir = _setup_feature(tmp_path)
        _create_task_file(tasks_dir, "001", "Task one", body="Old body.")

        tool = TodoEditTool(root_dir=tmp_path)
        await tool.execute(
            json.dumps({
                "feature_id": "001-test-feature",
                "task_id": "001",
                "body": "New body content.",
            })
        )

        filepath = list(tasks_dir.glob("001-*.md"))[0]
        post = frontmatter.load(str(filepath))
        assert post.content == "New body content."

    async def test_edit_missing_task(self, tmp_path):
        _setup_feature(tmp_path)
        tool = TodoEditTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({
                "feature_id": "001-test-feature",
                "task_id": "999",
            })
        )
        assert "[error]" in result

    def test_definition_schema(self, tmp_path):
        tool = TodoEditTool(root_dir=tmp_path)
        defn = tool.definition
        assert defn["function"]["name"] == "todo_edit"
