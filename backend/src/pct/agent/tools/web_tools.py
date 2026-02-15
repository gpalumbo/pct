"""Web tools: search and fetch."""

from __future__ import annotations

import json
import re
from typing import Any


class WebSearchTool:
    """Search the web using DuckDuckGo."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web using DuckDuckGo and return results.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query.",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default 5).",
                        },
                    },
                    "required": ["query"],
                },
            },
        }

    async def execute(self, arguments: str) -> str:
        try:
            from duckduckgo_search import DDGS

            parsed = json.loads(arguments)
            query = parsed["query"]
            max_results = parsed.get("max_results", 5)

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
            return f"[error] {e}"


def _strip_html(html: str) -> str:
    """Crude HTML-to-text: strip tags, collapse whitespace."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class WebFetchTool:
    """Fetch the content of a URL."""

    @property
    def name(self) -> str:
        return "web_fetch"

    @property
    def definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "web_fetch",
                "description": "Fetch the text content of a URL.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to fetch.",
                        },
                    },
                    "required": ["url"],
                },
            },
        }

    async def execute(self, arguments: str) -> str:
        try:
            import httpx

            parsed = json.loads(arguments)
            url = parsed["url"]

            async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()

                # Enforce 1MB limit
                content_bytes = resp.content
                if len(content_bytes) > 1_048_576:
                    content_bytes = content_bytes[:1_048_576]

                text = content_bytes.decode("utf-8", errors="replace")

                content_type = resp.headers.get("content-type", "")
                if "html" in content_type:
                    text = _strip_html(text)

                return text
        except Exception as e:
            return f"[error] {e}"
