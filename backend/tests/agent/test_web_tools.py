"""Tests for web tools: WebSearchTool and WebFetchTool."""

from __future__ import annotations

import json

from pct.agent.tools.web_tools import WebFetchTool, WebSearchTool, _strip_html


class TestWebSearchTool:
    def test_definition_schema(self):
        tool = WebSearchTool()
        defn = tool.definition
        assert defn["type"] == "function"
        assert defn["function"]["name"] == "web_search"
        params = defn["function"]["parameters"]
        assert "query" in params["properties"]
        assert "query" in params["required"]

    async def test_bad_json_returns_error(self):
        tool = WebSearchTool()
        result = await tool.execute("not json")
        assert "[error]" in result


class TestWebFetchTool:
    def test_definition_schema(self):
        tool = WebFetchTool()
        defn = tool.definition
        assert defn["function"]["name"] == "web_fetch"
        assert "url" in defn["function"]["parameters"]["properties"]

    async def test_bad_json_returns_error(self):
        tool = WebFetchTool()
        result = await tool.execute("not json")
        assert "[error]" in result

    async def test_invalid_url_returns_error(self):
        tool = WebFetchTool()
        result = await tool.execute(json.dumps({"url": "http://localhost:99999/nope"}))
        assert "[error]" in result


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
