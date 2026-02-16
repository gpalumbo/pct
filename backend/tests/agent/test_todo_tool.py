"""Tests for TodoTool: list, get, create, edit, delete actions."""

from __future__ import annotations

import json

import frontmatter
import pytest

from pct.agent.tools.todo_tool import TodoTool


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


class TestTodoToolList:
    async def test_list_tasks(self, tmp_path):
        tasks_dir = _setup_feature(tmp_path)
        _create_task_file(tasks_dir, "001", "First task")
        _create_task_file(tasks_dir, "002", "Second task", status="implement")

        tool = TodoTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({"action": "list", "feature_id": "001-test-feature"})
        )
        assert "001" in result
        assert "002" in result
        assert "First task" in result
        assert "Second task" in result

    async def test_list_missing_feature(self, tmp_path):
        tool = TodoTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({"action": "list", "feature_id": "nonexistent"})
        )
        assert "No tasks directory" in result

    async def test_list_empty_tasks(self, tmp_path):
        _setup_feature(tmp_path)
        tool = TodoTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({"action": "list", "feature_id": "001-test-feature"})
        )
        assert "No tasks found" in result


class TestTodoToolGet:
    async def test_get_single_task(self, tmp_path):
        tasks_dir = _setup_feature(tmp_path)
        _create_task_file(tasks_dir, "001", "My task", body="Detailed spec here.")

        tool = TodoTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({"action": "get", "feature_id": "001-test-feature", "task_id": "001"})
        )
        data = json.loads(result)
        assert data["id"] == "001"
        assert data["title"] == "My task"
        assert "Detailed spec" in data["body"]

    async def test_get_missing_task(self, tmp_path):
        _setup_feature(tmp_path)
        tool = TodoTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({"action": "get", "feature_id": "001-test-feature", "task_id": "999"})
        )
        assert "[error]" in result

    async def test_get_missing_task_id_param(self, tmp_path):
        _setup_feature(tmp_path)
        tool = TodoTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({"action": "get", "feature_id": "001-test-feature"})
        )
        assert "[error]" in result
        assert "task_id" in result


class TestTodoToolCreate:
    async def test_create_first_task(self, tmp_path):
        (tmp_path / ".pct" / "active-features" / "001-feat").mkdir(parents=True)

        tool = TodoTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({
                "action": "create",
                "feature_id": "001-feat",
                "title": "Build the widget",
                "body": "## Spec\nBuild it well.",
                "priority": 2,
                "tags": ["backend"],
            })
        )
        assert "Created task 001" in result

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

        tool = TodoTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({
                "action": "create",
                "feature_id": "001-test-feature",
                "title": "Third task",
                "body": "Body.",
            })
        )
        assert "Created task 003" in result

    async def test_create_missing_title(self, tmp_path):
        _setup_feature(tmp_path)
        tool = TodoTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({
                "action": "create",
                "feature_id": "001-test-feature",
                "body": "Body.",
            })
        )
        assert "[error]" in result
        assert "title" in result

    async def test_create_missing_body(self, tmp_path):
        _setup_feature(tmp_path)
        tool = TodoTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({
                "action": "create",
                "feature_id": "001-test-feature",
                "title": "A task",
            })
        )
        assert "[error]" in result
        assert "body" in result


class TestTodoToolEdit:
    async def test_edit_status(self, tmp_path):
        tasks_dir = _setup_feature(tmp_path)
        _create_task_file(tasks_dir, "001", "Task one", status="refine-spec")

        tool = TodoTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({
                "action": "edit",
                "feature_id": "001-test-feature",
                "task_id": "001",
                "status": "implement",
            })
        )
        assert "Updated task 001" in result

        filepath = list(tasks_dir.glob("001-*.md"))[0]
        post = frontmatter.load(str(filepath))
        assert post.metadata["status"] == "implement"

    async def test_edit_updates_timestamp(self, tmp_path):
        tasks_dir = _setup_feature(tmp_path)
        _create_task_file(tasks_dir, "001", "Task one")

        tool = TodoTool(root_dir=tmp_path)
        await tool.execute(
            json.dumps({
                "action": "edit",
                "feature_id": "001-test-feature",
                "task_id": "001",
                "title": "Renamed",
            })
        )

        filepath = list(tasks_dir.glob("001-*.md"))[0]
        post = frontmatter.load(str(filepath))
        assert post.metadata["title"] == "Renamed"
        assert post.metadata["updated"] != "2026-01-01T00:00:00+00:00"

    async def test_edit_body(self, tmp_path):
        tasks_dir = _setup_feature(tmp_path)
        _create_task_file(tasks_dir, "001", "Task one", body="Old body.")

        tool = TodoTool(root_dir=tmp_path)
        await tool.execute(
            json.dumps({
                "action": "edit",
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
        tool = TodoTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({
                "action": "edit",
                "feature_id": "001-test-feature",
                "task_id": "999",
            })
        )
        assert "[error]" in result

    async def test_edit_missing_task_id_param(self, tmp_path):
        _setup_feature(tmp_path)
        tool = TodoTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({
                "action": "edit",
                "feature_id": "001-test-feature",
            })
        )
        assert "[error]" in result
        assert "task_id" in result


class TestTodoToolDelete:
    async def test_delete_task(self, tmp_path):
        tasks_dir = _setup_feature(tmp_path)
        filepath = _create_task_file(tasks_dir, "001", "Doomed task")
        assert filepath.exists()

        tool = TodoTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({
                "action": "delete",
                "feature_id": "001-test-feature",
                "task_id": "001",
            })
        )
        assert "Deleted task 001" in result
        assert not filepath.exists()

    async def test_delete_missing_task(self, tmp_path):
        _setup_feature(tmp_path)
        tool = TodoTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({
                "action": "delete",
                "feature_id": "001-test-feature",
                "task_id": "999",
            })
        )
        assert "[error]" in result

    async def test_delete_missing_task_id_param(self, tmp_path):
        _setup_feature(tmp_path)
        tool = TodoTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({
                "action": "delete",
                "feature_id": "001-test-feature",
            })
        )
        assert "[error]" in result
        assert "task_id" in result


class TestTodoToolGeneral:
    async def test_unknown_action(self, tmp_path):
        tool = TodoTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({"action": "archive", "feature_id": "001-feat"})
        )
        assert "[error]" in result
        assert "Unknown action" in result

    async def test_bad_json_returns_error(self, tmp_path):
        tool = TodoTool(root_dir=tmp_path)
        result = await tool.execute("not json")
        assert "[error]" in result

    def test_definition_schema(self, tmp_path):
        tool = TodoTool(root_dir=tmp_path)
        defn = tool.definition
        assert defn["function"]["name"] == "todo"
        params = defn["function"]["parameters"]
        assert "action" in params["properties"]
        assert "feature_id" in params["properties"]
        assert set(params["required"]) == {"action", "feature_id"}
