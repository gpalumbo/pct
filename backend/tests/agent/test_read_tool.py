"""Tests for ReadTool: file read, URL fetch, and auto-detection."""

from __future__ import annotations

import json

import pytest

from pct.agent.tools.read_tool import ReadTool, _strip_html


class TestReadToolFile:
    async def test_read_existing_file(self, tmp_path):
        (tmp_path / "hello.txt").write_text("hello world", encoding="utf-8")
        tool = ReadTool(root_dir=tmp_path)
        result = await tool.execute(json.dumps({"source": "hello.txt"}))
        assert result == "hello world"

    async def test_read_missing_file(self, tmp_path):
        tool = ReadTool(root_dir=tmp_path)
        result = await tool.execute(json.dumps({"source": "nope.txt"}))
        assert "[error]" in result

    async def test_read_path_traversal_rejected(self, tmp_path):
        tool = ReadTool(root_dir=tmp_path)
        result = await tool.execute(json.dumps({"source": "../../etc/passwd"}))
        assert "[error]" in result
        assert "escapes" in result.lower() or "Path" in result

    async def test_read_nested_file(self, tmp_path):
        sub = tmp_path / "sub" / "dir"
        sub.mkdir(parents=True)
        (sub / "data.txt").write_text("nested data", encoding="utf-8")
        tool = ReadTool(root_dir=tmp_path)
        result = await tool.execute(json.dumps({"source": "sub/dir/data.txt"}))
        assert result == "nested data"


class TestReadToolURL:
    async def test_invalid_url_returns_error(self, tmp_path):
        tool = ReadTool(root_dir=tmp_path)
        result = await tool.execute(json.dumps({"source": "http://localhost:99999/nope"}))
        assert "[error]" in result

    async def test_bad_json_returns_error(self, tmp_path):
        tool = ReadTool(root_dir=tmp_path)
        result = await tool.execute("not json")
        assert "[error]" in result


class TestReadToolAutoDetection:
    async def test_http_url_detected(self, tmp_path):
        tool = ReadTool(root_dir=tmp_path)
        # Will fail to connect but should attempt URL path, not file path
        result = await tool.execute(json.dumps({"source": "http://localhost:99999/test"}))
        assert "[error]" in result
        # Should NOT contain "escapes" (file traversal error)
        assert "escapes" not in result.lower()

    async def test_https_url_detected(self, tmp_path):
        tool = ReadTool(root_dir=tmp_path)
        result = await tool.execute(json.dumps({"source": "https://localhost:99999/test"}))
        assert "[error]" in result
        assert "escapes" not in result.lower()

    async def test_plain_path_treated_as_file(self, tmp_path):
        (tmp_path / "file.txt").write_text("content", encoding="utf-8")
        tool = ReadTool(root_dir=tmp_path)
        result = await tool.execute(json.dumps({"source": "file.txt"}))
        assert result == "content"


class TestReadToolDefinition:
    def test_definition_schema(self, tmp_path):
        tool = ReadTool(root_dir=tmp_path)
        defn = tool.definition
        assert defn["type"] == "function"
        assert defn["function"]["name"] == "read"
        assert "source" in defn["function"]["parameters"]["properties"]
        assert "source" in defn["function"]["parameters"]["required"]


class TestStripHtml:
    def test_strips_tags(self):
        assert _strip_html("<p>hello</p>") == "hello"

    def test_strips_script_and_style(self):
        html = "<style>body{}</style><script>alert(1)</script><p>text</p>"
        assert "alert" not in _strip_html(html)
        assert "text" in _strip_html(html)

    def test_collapses_whitespace(self):
        result = _strip_html("<div>  a   b  </div>")
        assert result == "a b"
