"""RAG indexer: index work artifacts into LanceDB for semantic search."""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".md", ".txt", ".py", ".yaml", ".yml", ".json", ".rst"}

# Lazy-loaded singletons
_model = None
_connections: dict[str, object] = {}


def _get_model():
    """Lazy-load the sentence transformer model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _get_db(project_id: str):
    """Get or create a LanceDB connection for a project."""
    if project_id not in _connections:
        import lancedb

        rag_dir = Path.home() / ".pct" / "projects" / project_id / "rag"
        rag_dir.mkdir(parents=True, exist_ok=True)
        _connections[project_id] = lancedb.connect(str(rag_dir))
    return _connections[project_id]


def _read_file_text(file_path: Path) -> str | None:
    """Read file text, return None if unreadable."""
    try:
        return file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def index_file(project_id: str, file_path: Path) -> bool:
    """Upsert a single file into the 'artifacts' table. Returns True on success."""
    if file_path.suffix not in SUPPORTED_EXTENSIONS:
        return False

    text = _read_file_text(file_path)
    if not text or not text.strip():
        return False

    model = _get_model()
    db = _get_db(project_id)
    vector = model.encode(text[:8192]).tolist()

    record = {
        "path": str(file_path),
        "text": text[:8192],
        "vector": vector,
    }

    table_name = "artifacts"
    try:
        existing_tables = db.list_tables()
    except Exception:
        existing_tables = []

    if table_name in existing_tables:
        table = db.open_table(table_name)
        with contextlib.suppress(Exception):
            table.delete(f'path = "{str(file_path)}"')
        table.add([record])
    else:
        try:
            db.create_table(table_name, [record])
        except ValueError:
            # Table was created concurrently or exists from a prior session
            table = db.open_table(table_name)
            table.add([record])

    return True


def index_directory(project_id: str, directory: Path) -> int:
    """Index all supported text files recursively. Returns count of indexed files."""
    count = 0
    if not directory.is_dir():
        return count

    for file_path in sorted(directory.rglob("*")):
        if file_path.is_file() and file_path.suffix in SUPPORTED_EXTENSIONS and index_file(project_id, file_path):
            count += 1
    return count


def reindex_all(project_id: str, work_dir: Path) -> int:
    """Drop existing artifacts table and re-index everything."""
    db = _get_db(project_id)
    existing_tables = db.list_tables()
    if "artifacts" in existing_tables:
        db.drop_table("artifacts")
    return index_directory(project_id, work_dir)
