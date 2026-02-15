"""RAG search tool using LanceDB and sentence-transformers."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RAGSearchTool:
    """Semantic search over project tasks and specs via LanceDB."""

    def __init__(self, project_id: str) -> None:
        self._project_id = project_id
        self._model = None
        self._db = None

    def _rag_dir(self) -> Path:
        return Path.home() / ".pct" / "projects" / self._project_id / "rag"

    def _ensure_loaded(self):
        """Lazy-load embedding model and LanceDB connection on first use."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer("all-MiniLM-L6-v2")

        if self._db is None:
            import lancedb

            rag_dir = self._rag_dir()
            rag_dir.mkdir(parents=True, exist_ok=True)
            self._db = lancedb.connect(str(rag_dir))

    @property
    def name(self) -> str:
        return "rag_search"

    @property
    def definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "rag_search",
                "description": "Semantic search over project tasks and specs using embeddings.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language search query.",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum results to return (default 5).",
                        },
                        "doc_type": {
                            "type": "string",
                            "enum": ["task", "spec", "feature"],
                            "description": "Optional: filter by document type.",
                        },
                    },
                    "required": ["query"],
                },
            },
        }

    async def execute(self, arguments: str) -> str:
        try:
            parsed = json.loads(arguments)
            query = parsed["query"]
            max_results = parsed.get("max_results", 5)
            doc_type = parsed.get("doc_type")

            self._ensure_loaded()

            # Determine which tables to search
            table_map = {
                "task": ["tasks"],
                "spec": ["specs"],
                "feature": ["specs"],
            }
            tables_to_search = table_map.get(doc_type, ["tasks", "specs"])

            # Get available tables
            available = self._db.list_tables()
            tables_to_search = [t for t in tables_to_search if t in available]

            if not tables_to_search:
                return "No documents indexed yet."

            # Embed the query
            vector = self._model.encode(query).tolist()

            # Search each table and collect results
            all_results = []
            for table_name in tables_to_search:
                table = self._db.open_table(table_name)
                results = (
                    table.search(vector)
                    .limit(max_results)
                    .to_list()
                )
                for r in results:
                    entry = {
                        "table": table_name,
                        "score": round(float(r.get("_distance", 0)), 4),
                    }
                    # Include all non-vector, non-internal fields
                    for k, v in r.items():
                        if k not in ("vector", "_distance", "_rowid"):
                            entry[k] = v
                    all_results.append(entry)

            # Sort by score (lower distance = better match)
            all_results.sort(key=lambda x: x["score"])
            all_results = all_results[:max_results]

            if not all_results:
                return "No matching documents found."

            return json.dumps(all_results, default=str, indent=2)
        except Exception as e:
            logger.exception("RAG search failed")
            return f"[error] {e}"
