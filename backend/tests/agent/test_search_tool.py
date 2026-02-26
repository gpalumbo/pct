"""Tests for SearchTool: web search, RAG search, combined output, graceful failures."""

from __future__ import annotations

import json

from pct.agent.tools.search_tool import SearchTool


class TestSearchToolDefinition:
    def test_definition_schema(self):
        tool = SearchTool(project_id="test-proj")
        defn = tool.definition
        assert defn["type"] == "function"
        assert defn["function"]["name"] == "search"
        params = defn["function"]["parameters"]
        assert "query" in params["properties"]
        assert "query" in params["required"]
        assert "max_results" in params["properties"]

    def test_name(self):
        tool = SearchTool(project_id="test-proj")
        assert tool.name == "search"


class TestSearchToolExecution:
    async def test_bad_json_returns_error(self):
        tool = SearchTool(project_id="test-proj")
        result = await tool.execute("not json")
        assert "[error]" in result

    async def test_rag_failure_returns_gracefully(self, tmp_path, monkeypatch):
        """When RAG fails (no index), web results should still be returned."""
        tool = SearchTool(project_id="test-empty")
        # Point RAG dir to tmp_path so it creates a fresh empty DB
        monkeypatch.setattr(tool, "_rag_dir", lambda: tmp_path / "rag")

        # Mock web search to avoid network calls
        async def mock_web(query, max_results):
            return "**Mock Result**\nhttps://example.com\nMock body"

        monkeypatch.setattr(tool, "_web_search", mock_web)

        result = await tool.execute(json.dumps({"query": "test"}))
        assert "## Web Results" in result
        assert "Mock Result" in result
        assert "## Project Results" in result

    async def test_both_sources_in_output(self, tmp_path, monkeypatch):
        """Output should have labeled sections for web and project results."""
        tool = SearchTool(project_id="test-proj")

        async def mock_web(query, max_results):
            return "Web result here"

        async def mock_rag(query, max_results):
            return "RAG result here"

        monkeypatch.setattr(tool, "_web_search", mock_web)
        monkeypatch.setattr(tool, "_rag_search", mock_rag)

        result = await tool.execute(json.dumps({"query": "test"}))
        assert "## Web Results" in result
        assert "Web result here" in result
        assert "## Project Results" in result
        assert "RAG result here" in result

    async def test_web_error_still_shows_rag(self, monkeypatch):
        """When web search fails, RAG results should still appear."""
        tool = SearchTool(project_id="test-proj")

        async def mock_web(query, max_results):
            raise ConnectionError("no internet")

        async def mock_rag(query, max_results):
            return "RAG works fine"

        monkeypatch.setattr(tool, "_web_search", mock_web)
        monkeypatch.setattr(tool, "_rag_search", mock_rag)

        result = await tool.execute(json.dumps({"query": "test"}))
        assert "## Web Results" in result
        assert "[error]" in result
        assert "## Project Results" in result
        assert "RAG works fine" in result

    async def test_empty_rag_db(self, tmp_path, monkeypatch):
        """With empty RAG DB, should show 'No documents indexed yet.'"""
        tool = SearchTool(project_id="test-empty")
        monkeypatch.setattr(tool, "_rag_dir", lambda: tmp_path / "rag")

        async def mock_web(query, max_results):
            return "Web result"

        monkeypatch.setattr(tool, "_web_search", mock_web)

        result = await tool.execute(json.dumps({"query": "test"}))
        assert "No documents indexed" in result or "No project index" in result
