"""SearchTool — combined web search + RAG semantic search."""

from typing import Any


class SearchTool:
    def __init__(self, project_root=None):
        self.project_root = project_root

    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "Search the web or project knowledge base."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "source": {"type": "string", "enum": ["web", "rag", "both"], "default": "both"},
            },
            "required": ["query"],
        }

    async def execute(self, query: str = "", source: str = "both", **kwargs: Any) -> str:
        results = []

        if source in ("web", "both"):
            web_results = await self._web_search(query)
            if web_results:
                results.append("## Web Results\n" + web_results)

        if source in ("rag", "both"):
            rag_results = self._rag_search(query)
            if rag_results:
                results.append("## RAG Results\n" + rag_results)

        return "\n\n".join(results) if results else "No results found."

    async def _web_search(self, query: str) -> str:
        try:
            from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
                return "\n".join(f"- {r['title']}: {r['body']}" for r in results)
        except Exception as e:
            return f"Web search error: {e}"

    def _rag_search(self, query: str) -> str:
        # Stub — will be implemented in Phase 6
        return ""
