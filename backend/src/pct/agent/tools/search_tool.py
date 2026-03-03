"""Search tool: combined web search and RAG semantic search."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from loguru import logger


class SearchTool:
    """Search the web and project knowledge base."""

    def __init__(self, project_id: str = "") -> None:
        self._project_id = project_id

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

            if isinstance(web_result, Exception):
                sections.append(f"## Web Results\n\n[error] {web_result}")
            else:
                sections.append(f"## Web Results\n\n{web_result}")

            if isinstance(rag_result, Exception):
                logger.debug("RAG search failed: {}", rag_result)
                sections.append("## Project Results\n\nNo project index available.")
            else:
                sections.append(f"## Project Results\n\n{rag_result}")

            return "\n\n".join(sections)
        except Exception as e:
            return f"[error] {e}"

    async def _web_search(self, query: str, max_results: int) -> str:
        try:
            from ddgs import DDGS

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
        except Exception as e:
            return f"Web search error: {e}"

    async def _rag_search(self, query: str, max_results: int) -> str:
        return "No documents indexed yet."
