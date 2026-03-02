"""Tests for ReadTool."""

from pathlib import Path

from pct.agent.tools.read_tool import ReadTool


class TestReadTool:
    async def test_read_file(self, tmp_path: Path):
        (tmp_path / "test.txt").write_text("Hello World", encoding="utf-8")
        tool = ReadTool(tmp_path)
        result = await tool.execute(path="test.txt")
        assert result == "Hello World"

    async def test_read_missing_file(self, tmp_path: Path):
        tool = ReadTool(tmp_path)
        result = await tool.execute(path="nonexistent.txt")
        assert "Error" in result

    async def test_read_absolute_path(self, tmp_path: Path):
        f = tmp_path / "abs.txt"
        f.write_text("Absolute", encoding="utf-8")
        tool = ReadTool(tmp_path)
        result = await tool.execute(path=str(f))
        assert result == "Absolute"

    def test_properties(self, tmp_path: Path):
        tool = ReadTool(tmp_path)
        assert tool.name == "read"
        assert "Read" in tool.description or "read" in tool.description.lower()
        assert "path" in tool.parameters["properties"]
