"""Tests for RAG search tool — schema validation and empty DB handling."""

from __future__ import annotations

import json

from pct.agent.tools.rag_tools import RAGSearchTool


class TestRAGSearchTool:
    def test_definition_schema(self):
        tool = RAGSearchTool(project_id="test-proj")
        defn = tool.definition
        assert defn["type"] == "function"
        assert defn["function"]["name"] == "rag_search"
        params = defn["function"]["parameters"]
        assert "query" in params["properties"]
        assert "query" in params["required"]
        assert "max_results" in params["properties"]
        assert "doc_type" in params["properties"]

    async def test_empty_db_returns_no_documents(self, tmp_path, monkeypatch):
        """When no tables exist, return a helpful message instead of crashing."""
        tool = RAGSearchTool(project_id="test-empty")
        # Point RAG dir to tmp_path so it creates a fresh empty DB
        monkeypatch.setattr(tool, "_rag_dir", lambda: tmp_path / "rag")

        result = await tool.execute(json.dumps({"query": "test query"}))
        assert "no documents" in result.lower() or "No documents" in result

    async def test_bad_json_returns_error(self):
        tool = RAGSearchTool(project_id="test-proj")
        result = await tool.execute("not json")
        assert "[error]" in result
