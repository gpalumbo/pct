"""Tests for file tools: FileReadTool, FileWriteTool, FileEditTool."""

from __future__ import annotations

import json

import pytest

from pct.agent.tools.file_tools import FileEditTool, FileReadTool, FileWriteTool


class TestFileReadTool:
    async def test_read_existing_file(self, tmp_path):
        (tmp_path / "hello.txt").write_text("hello world", encoding="utf-8")
        tool = FileReadTool(root_dir=tmp_path)
        result = await tool.execute(json.dumps({"path": "hello.txt"}))
        assert result == "hello world"

    async def test_read_missing_file(self, tmp_path):
        tool = FileReadTool(root_dir=tmp_path)
        result = await tool.execute(json.dumps({"path": "nope.txt"}))
        assert "[error]" in result

    async def test_read_path_traversal_rejected(self, tmp_path):
        tool = FileReadTool(root_dir=tmp_path)
        result = await tool.execute(json.dumps({"path": "../../etc/passwd"}))
        assert "[error]" in result
        assert "escapes" in result.lower() or "outside" in result.lower() or "Path" in result

    def test_definition_schema(self, tmp_path):
        tool = FileReadTool(root_dir=tmp_path)
        defn = tool.definition
        assert defn["type"] == "function"
        assert defn["function"]["name"] == "file_read"
        assert "path" in defn["function"]["parameters"]["properties"]


class TestFileWriteTool:
    async def test_write_creates_file(self, tmp_path):
        tool = FileWriteTool(root_dir=tmp_path)
        result = await tool.execute(json.dumps({"path": "out.txt", "content": "data"}))
        assert "Wrote" in result
        assert (tmp_path / "out.txt").read_text(encoding="utf-8") == "data"

    async def test_write_creates_parent_dirs(self, tmp_path):
        tool = FileWriteTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({"path": "sub/dir/file.txt", "content": "nested"})
        )
        assert "Wrote" in result
        assert (tmp_path / "sub" / "dir" / "file.txt").read_text(encoding="utf-8") == "nested"

    async def test_write_path_traversal_rejected(self, tmp_path):
        tool = FileWriteTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({"path": "../escape.txt", "content": "bad"})
        )
        assert "[error]" in result

    def test_definition_schema(self, tmp_path):
        tool = FileWriteTool(root_dir=tmp_path)
        defn = tool.definition
        assert defn["function"]["name"] == "file_write"
        params = defn["function"]["parameters"]
        assert "path" in params["properties"]
        assert "content" in params["properties"]


class TestFileEditTool:
    async def test_edit_replaces_text(self, tmp_path):
        (tmp_path / "code.py").write_text("def foo():\n    pass\n", encoding="utf-8")
        tool = FileEditTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({"path": "code.py", "old_text": "pass", "new_text": "return 42"})
        )
        assert "Edited" in result
        assert "return 42" in (tmp_path / "code.py").read_text(encoding="utf-8")

    async def test_edit_old_text_not_found(self, tmp_path):
        (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
        tool = FileEditTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({"path": "a.txt", "old_text": "missing", "new_text": "x"})
        )
        assert "[error]" in result
        assert "not found" in result

    async def test_edit_ambiguous_match(self, tmp_path):
        (tmp_path / "dup.txt").write_text("aaa bbb aaa", encoding="utf-8")
        tool = FileEditTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({"path": "dup.txt", "old_text": "aaa", "new_text": "ccc"})
        )
        assert "[error]" in result
        assert "2 times" in result

    async def test_edit_path_traversal_rejected(self, tmp_path):
        tool = FileEditTool(root_dir=tmp_path)
        result = await tool.execute(
            json.dumps({"path": "../../x.txt", "old_text": "a", "new_text": "b"})
        )
        assert "[error]" in result

    def test_definition_schema(self, tmp_path):
        tool = FileEditTool(root_dir=tmp_path)
        defn = tool.definition
        assert defn["function"]["name"] == "file_edit"
        params = defn["function"]["parameters"]
        assert "old_text" in params["properties"]
        assert "new_text" in params["properties"]
