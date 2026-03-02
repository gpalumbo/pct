"""RAG search — semantic search over indexed documents."""

from pathlib import Path

from pct.rag.indexer import _embed_text, _get_db


def rag_search_context(project_root: Path, query: str, max_results: int = 5) -> str:
    """Search the RAG index and return formatted results."""
    embedding = _embed_text(query)
    if embedding is None:
        return ""

    db = _get_db(project_root)
    if db is None:
        return ""

    try:
        if "documents" not in db.table_names():
            return ""

        table = db.open_table("documents")
        results = table.search(embedding).limit(max_results).to_list()

        if not results:
            return ""

        parts = []
        for r in results:
            path = r.get("path", "unknown")
            text = r.get("text", "")
            snippet = text[:500]
            parts.append(f"### {path}\n{snippet}")

        return "\n\n".join(parts)
    except Exception:
        return ""
