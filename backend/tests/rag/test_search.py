"""Tests for RAG search."""

from pathlib import Path
from unittest.mock import patch

from pct.rag.search import rag_search_context


class TestRagSearch:
    def test_empty_index(self, tmp_path: Path):
        """Search on empty/nonexistent index returns empty."""
        with patch("pct.rag.search._get_db", return_value=None):
            result = rag_search_context(tmp_path, "test query")
            assert result == ""

    def test_no_embedding_model(self, tmp_path: Path):
        with patch("pct.rag.search._embed_text", return_value=None):
            result = rag_search_context(tmp_path, "test query")
            assert result == ""

    @patch("pct.rag.search._embed_text")
    @patch("pct.rag.search._get_db")
    def test_search_with_results(self, mock_db, mock_embed, tmp_path: Path):
        """Test search returns formatted results."""

        mock_embed.return_value = [0.0] * 384

        mock_results = [
            {"path": "work/f1/t1/main.md", "text": "Task content here"},
            {"path": "pct-admin/project_spec.md", "text": "Project specification"},
        ]

        class MockSearchResult:
            def limit(self, n):
                return self

            def to_list(self):
                return mock_results

        mock_table = type("T", (), {"search": lambda self, v: MockSearchResult()})()
        mock_db_instance = type("DB", (), {
            "table_names": lambda self: ["documents"],
            "open_table": lambda self, n: mock_table,
        })()
        mock_db.return_value = mock_db_instance

        result = rag_search_context(tmp_path, "test query", max_results=5)
        assert "work/f1/t1/main.md" in result
        assert "Task content" in result
