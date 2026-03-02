"""Tests for RAG indexer."""

from pathlib import Path
from unittest.mock import patch

from pct.rag.indexer import SUPPORTED_EXTENSIONS, index_file, reindex_all


class TestIndexer:
    def test_supported_extensions(self):
        assert ".md" in SUPPORTED_EXTENSIONS
        assert ".py" in SUPPORTED_EXTENSIONS
        assert ".yaml" in SUPPORTED_EXTENSIONS
        assert ".json" in SUPPORTED_EXTENSIONS
        assert ".exe" not in SUPPORTED_EXTENSIONS

    def test_index_file_unsupported_extension(self, tmp_path: Path):
        f = tmp_path / "test.exe"
        f.write_text("binary content", encoding="utf-8")
        assert index_file(tmp_path, f) is False

    def test_index_file_nonexistent(self, tmp_path: Path):
        assert index_file(tmp_path, tmp_path / "nonexistent.md") is False

    def test_index_file_empty(self, tmp_path: Path):
        f = tmp_path / "empty.md"
        f.write_text("", encoding="utf-8")
        assert index_file(tmp_path, f) is False

    @patch("pct.rag.indexer._get_embedding_model")
    @patch("pct.rag.indexer._get_db")
    def test_index_file_with_mocks(self, mock_db, mock_model, tmp_path: Path):
        """Test indexing with mocked dependencies."""
        import numpy as np

        mock_model.return_value = type("M", (), {"encode": lambda self, t: np.zeros(384)})()

        # Mock DB
        mock_table = type("T", (), {
            "delete": lambda self, q: None,
            "add": lambda self, records: None,
        })()
        mock_db_instance = type("DB", (), {
            "table_names": lambda self: ["documents"],
            "open_table": lambda self, n: mock_table,
        })()
        mock_db.return_value = mock_db_instance

        f = tmp_path / "test.md"
        f.write_text("# Test\n\nContent here.", encoding="utf-8")
        assert index_file(tmp_path, f) is True

    def test_reindex_all_no_deps(self, tmp_project_root: Path):
        """reindex_all returns 0 when DB not available."""
        with patch("pct.rag.indexer._get_db", return_value=None):
            count = reindex_all(tmp_project_root)
            assert count == 0

    def test_text_truncation(self):
        from pct.rag.indexer import MAX_TEXT_LENGTH

        assert MAX_TEXT_LENGTH == 8192
