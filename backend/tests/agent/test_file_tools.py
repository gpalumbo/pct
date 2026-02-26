"""Tests for FileTool with write and edit actions."""

from __future__ import annotations

import json

from pct.agent.tools.file_tools import FileTool


class TestFileToolWrite:
    async def test_write_creates_file(self, tmp_path):
        tool = FileTool(root_dir=tmp_path)
        result = await tool.execute(json.dumps({"action": "write", "path": "out.txt", "content": "data"}))
        assert "Wrote" in result
        assert (tmp_path / "out.txt").read_text(encoding="utf-8") == "data"

    async def test_write_creates_parent_dirs(self, tmp_path):
        tool = FileTool(root_dir=tmp_path)
        result = await tool.execute(json.dumps({"action": "write", "path": "sub/dir/file.txt", "content": "nested"}))
        assert "Wrote" in result
        assert (tmp_path / "sub" / "dir" / "file.txt").read_text(encoding="utf-8") == "nested"

    async def test_write_path_traversal_rejected(self, tmp_path):
        tool = FileTool(root_dir=tmp_path)
        result = await tool.execute(json.dumps({"action": "write", "path": "../escape.txt", "content": "bad"}))
        assert "[error]" in result

    async def test_write_missing_content(self, tmp_path):
        tool = FileTool(root_dir=tmp_path)
        result = await tool.execute(json.dumps({"action": "write", "path": "out.txt"}))
        assert "[error]" in result
        assert "content" in result.lower()


class TestFileToolEdit:
    async def test_edit_replaces_text(self, tmp_path):
        (tmp_path / "code.py").write_text("def foo():\n    pass\n", encoding="utf-8")
        tool = FileTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({"action": "edit", "path": "code.py", "old_text": "pass", "new_text": "return 42"})
        )
        assert "Edited" in result
        assert "return 42" in (tmp_path / "code.py").read_text(encoding="utf-8")

    async def test_edit_old_text_not_found(self, tmp_path):
        (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
        tool = FileTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({"action": "edit", "path": "a.txt", "old_text": "missing", "new_text": "x"})
        )
        assert "[error]" in result
        assert "not found" in result

    async def test_edit_ambiguous_match(self, tmp_path):
        (tmp_path / "dup.txt").write_text("aaa bbb aaa", encoding="utf-8")
        tool = FileTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({"action": "edit", "path": "dup.txt", "old_text": "aaa", "new_text": "ccc"})
        )
        assert "[error]" in result
        assert "2 times" in result

    async def test_edit_path_traversal_rejected(self, tmp_path):
        tool = FileTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({"action": "edit", "path": "../../x.txt", "old_text": "a", "new_text": "b"})
        )
        assert "[error]" in result

    async def test_edit_missing_old_text_param(self, tmp_path):
        (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
        tool = FileTool(root_dir=tmp_path)
        result = await tool.execute(json.dumps({"action": "edit", "path": "a.txt", "new_text": "x"}))
        assert "[error]" in result
        assert "old_text" in result


class TestFileToolGeneral:
    async def test_unknown_action(self, tmp_path):
        tool = FileTool(root_dir=tmp_path)
        result = await tool.execute(json.dumps({"action": "delete", "path": "file.txt"}))
        assert "[error]" in result
        assert "Unknown action" in result

    async def test_bad_json_returns_error(self, tmp_path):
        tool = FileTool(root_dir=tmp_path)
        result = await tool.execute("not json")
        assert "[error]" in result

    def test_definition_schema(self, tmp_path):
        tool = FileTool(root_dir=tmp_path)
        defn = tool.definition
        assert defn["type"] == "function"
        assert defn["function"]["name"] == "file"
        params = defn["function"]["parameters"]
        assert "action" in params["properties"]
        assert "path" in params["properties"]
        assert "content" in params["properties"]
        assert "old_text" in params["properties"]
        assert "new_text" in params["properties"]
        assert set(params["required"]) == {"action", "path"}
