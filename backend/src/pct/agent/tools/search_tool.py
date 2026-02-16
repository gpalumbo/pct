"""Search tool: combined web search and RAG semantic search."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SearchTool:
    """Search the web and project knowledge base in parallel."""

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
        return "search"

    @property
    def definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "search",
                "description": (
                    "Search the web and project knowledge base."
                    " Returns combined results from both sources."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query.",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum results per source (default 5).",
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

            web_coro = self._web_search(query, max_results)
            rag_coro = self._rag_search(query, max_results)

            web_result, rag_result = await asyncio.gather(
                web_coro, rag_coro, return_exceptions=True
            )

            sections = []

            # Web results
            if isinstance(web_result, Exception):
                sections.append(f"## Web Results\n\n[error] {web_result}")
            else:
                sections.append(f"## Web Results\n\n{web_result}")

            # Project results
            if isinstance(rag_result, Exception):
                logger.debug("RAG search failed: %s", rag_result)
                sections.append("## Project Results\n\nNo project index available.")
            else:
                sections.append(f"## Project Results\n\n{rag_result}")

            return "\n\n".join(sections)
        except Exception as e:
            return f"[error] {e}"

    async def _web_search(self, query: str, max_results: int) -> str:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return "No results found."

        lines = []
        for r in results:
            lines.append(f"**{r.get('title', '')}**")
            lines.append(r.get("href", ""))
            lines.append(r.get("body", ""))
            lines.append("")
        return "\n".join(lines).strip()

    async def _rag_search(self, query: str, max_results: int) -> str:
        self._ensure_loaded()

        available = self._db.list_tables()
        tables_to_search = [t for t in ["tasks", "specs"] if t in available]

        if not tables_to_search:
            return "No documents indexed yet."

        vector = self._model.encode(query).tolist()

        all_results = []
        for table_name in tables_to_search:
            table = self._db.open_table(table_name)
            results = table.search(vector).limit(max_results).to_list()
            for r in results:
                entry = {
                    "table": table_name,
                    "score": round(float(r.get("_distance", 0)), 4),
                }
                for k, v in r.items():
                    if k not in ("vector", "_distance", "_rowid"):
                        entry[k] = v
                all_results.append(entry)

        all_results.sort(key=lambda x: x["score"])
        all_results = all_results[:max_results]

        if not all_results:
            return "No matching documents found."

        return json.dumps(all_results, default=str, indent=2)
