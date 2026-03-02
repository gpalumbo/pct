"""RAG indexer — LanceDB + sentence-transformers embedding."""

import contextlib
from pathlib import Path

SUPPORTED_EXTENSIONS = {".md", ".txt", ".py", ".yaml", ".yml", ".json", ".rst"}
MAX_TEXT_LENGTH = 8192

# Lazy singleton for embedding model
_embedding_model = None


def _get_embedding_model():
    """Lazy load the embedding model (heavy import)."""
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model
    try:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        return _embedding_model
    except ImportError:
        return None


def _get_db(project_root: Path):
    """Get or create LanceDB connection."""
    try:
        import lancedb

        db_path = project_root / ".pct" / "rag"
        db_path.mkdir(parents=True, exist_ok=True)
        return lancedb.connect(str(db_path))
    except ImportError:
        return None


def _embed_text(text: str) -> list[float] | None:
    """Embed text using the sentence-transformers model."""
    model = _get_embedding_model()
    if model is None:
        return None
    truncated = text[:MAX_TEXT_LENGTH]
    embedding = model.encode(truncated)
    return embedding.tolist()


def index_file(project_root: Path, file_path: Path) -> bool:
    """Index a single file into LanceDB. Returns True on success."""
    if file_path.suffix not in SUPPORTED_EXTENSIONS:
        return False
    if not file_path.exists():
        return False

    text = file_path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return False

    embedding = _embed_text(text)
    if embedding is None:
        return False

    db = _get_db(project_root)
    if db is None:
        return False

    rel_path = str(file_path.relative_to(project_root)) if file_path.is_relative_to(project_root) else str(file_path)

    record = {
        "path": rel_path,
        "text": text[:MAX_TEXT_LENGTH],
        "vector": embedding,
    }

    try:
        table_name = "documents"
        if table_name in db.table_names():
            table = db.open_table(table_name)
            # Upsert by deleting existing then adding
            with contextlib.suppress(Exception):
                table.delete(f'path = "{rel_path}"')
            table.add([record])
        else:
            db.create_table(table_name, [record])
        return True
    except Exception:
        return False


def reindex_all(project_root: Path) -> int:
    """Drop and rebuild the full RAG index. Returns count of indexed files."""
    db = _get_db(project_root)
    if db is None:
        return 0

    # Drop existing table
    try:
        if "documents" in db.table_names():
            db.drop_table("documents")
    except Exception:
        pass

    count = 0
    # Index work/ directory
    work_dir = project_root / "work"
    if work_dir.exists():
        for f in work_dir.rglob("*"):
            if f.is_file() and f.suffix in SUPPORTED_EXTENSIONS and index_file(project_root, f):
                count += 1

    # Index project spec
    project_spec = project_root / "pct-admin" / "project_spec.md"
    if project_spec.exists() and index_file(project_root, project_spec):
        count += 1

    # Index feature specs
    features_dir = project_root / "pct-admin" / "active-features"
    if features_dir.exists():
        for spec in features_dir.rglob("feature_spec.md"):
            if index_file(project_root, spec):
                count += 1

    return count
