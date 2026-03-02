"""Tests for TodoTool."""

from pathlib import Path

from pct.agent.tools.todo_tool import TodoTool
from pct.storage.directory_manager import ensure_project_dirs


class TestTodoTool:
    async def test_list_empty(self, tmp_project_root: Path):
        tool = TodoTool(tmp_project_root)
        result = await tool.execute(action="list", feature_id="f1")
        assert "No tasks" in result

    async def test_create_and_list(self, tmp_project_root: Path):
        ensure_project_dirs(tmp_project_root)
        tool = TodoTool(tmp_project_root)
        await tool.execute(action="create", feature_id="f1", task_id="t1", title="Task 1", content="Do X")
        result = await tool.execute(action="list", feature_id="f1")
        assert "t1" in result
        assert "Task 1" in result

    async def test_get(self, tmp_project_root: Path):
        tool = TodoTool(tmp_project_root)
        await tool.execute(action="create", feature_id="f1", task_id="t1", title="T1", content="Content")
        result = await tool.execute(action="get", feature_id="f1", task_id="t1")
        assert "T1" in result

    async def test_get_nonexistent(self, tmp_project_root: Path):
        tool = TodoTool(tmp_project_root)
        result = await tool.execute(action="get", feature_id="f1", task_id="nope")
        assert "not found" in result

    async def test_edit(self, tmp_project_root: Path):
        tool = TodoTool(tmp_project_root)
        await tool.execute(action="create", feature_id="f1", task_id="t1", title="V1")
        result = await tool.execute(action="edit", feature_id="f1", task_id="t1", title="V2")
        assert "Updated" in result

    async def test_delete(self, tmp_project_root: Path):
        tool = TodoTool(tmp_project_root)
        await tool.execute(action="create", feature_id="f1", task_id="t1", title="T1")
        result = await tool.execute(action="delete", feature_id="f1", task_id="t1")
        assert "Deleted" in result

    async def test_delete_nonexistent(self, tmp_project_root: Path):
        tool = TodoTool(tmp_project_root)
        result = await tool.execute(action="delete", feature_id="f1", task_id="nope")
        assert "not found" in result
