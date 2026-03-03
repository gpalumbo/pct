"""Tests for ReadTool."""

import json
from pathlib import Path

from pct.agent.tools.read_tool import ReadTool


class TestReadTool:
    async def test_read_file(self, tmp_path: Path):
        (tmp_path / "test.txt").write_text("Hello World", encoding="utf-8")
        tool = ReadTool(tmp_path)
        result = await tool.execute(json.dumps({"source": "test.txt"}))
        assert result == "Hello World"

    async def test_read_missing_file(self, tmp_path: Path):
        tool = ReadTool(tmp_path)
        result = await tool.execute(json.dumps({"source": "nonexistent.txt"}))
        assert "error" in result.lower()

    def test_properties(self, tmp_path: Path):
        tool = ReadTool(tmp_path)
        assert tool.name == "read"
        defn = tool.definition
        assert defn["function"]["name"] == "read"
        assert "source" in defn["function"]["parameters"]["properties"]
