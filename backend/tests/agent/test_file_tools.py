"""Tests for FileTool."""

import json
from pathlib import Path

from pct.agent.tools.file_tools import FileTool


class TestFileTool:
    async def test_write(self, tmp_path: Path):
        tool = FileTool(tmp_path)
        args = json.dumps({"action": "write", "path": "output.txt", "content": "Hello"})
        result = await tool.execute(args)
        assert "Wrote" in result
        assert (tmp_path / "output.txt").read_text() == "Hello"

    async def test_write_creates_dirs(self, tmp_path: Path):
        tool = FileTool(tmp_path)
        args = json.dumps(
            {"action": "write", "path": "sub/dir/file.txt", "content": "Nested"}
        )
        await tool.execute(args)
        assert (tmp_path / "sub" / "dir" / "file.txt").read_text() == "Nested"

    async def test_edit(self, tmp_path: Path):
        (tmp_path / "edit.txt").write_text("Hello World", encoding="utf-8")
        tool = FileTool(tmp_path)
        args = json.dumps(
            {
                "action": "edit",
                "path": "edit.txt",
                "old_text": "World",
                "new_text": "PCT",
            }
        )
        result = await tool.execute(args)
        assert "Edited" in result
        assert (tmp_path / "edit.txt").read_text() == "Hello PCT"

    async def test_edit_old_text_not_found(self, tmp_path: Path):
        (tmp_path / "edit.txt").write_text("Hello", encoding="utf-8")
        tool = FileTool(tmp_path)
        args = json.dumps(
            {
                "action": "edit",
                "path": "edit.txt",
                "old_text": "Missing",
                "new_text": "New",
            }
        )
        result = await tool.execute(args)
        assert "error" in result.lower()

    async def test_edit_missing_file(self, tmp_path: Path):
        tool = FileTool(tmp_path)
        args = json.dumps(
            {
                "action": "edit",
                "path": "nope.txt",
                "old_text": "X",
                "new_text": "Y",
            }
        )
        result = await tool.execute(args)
        assert "error" in result.lower()
