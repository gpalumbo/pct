"""Read tool: read content from a file path or URL."""

from __future__ import annotations

import json
import re
from typing import Any

from pct.agent.tools.file_tools import _resolve_safe


def _strip_html(html: str) -> str:
    """Crude HTML-to-text: strip tags, collapse whitespace."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class ReadTool:
    """Read content from a file path or URL. Auto-detects source type."""

    def __init__(self, root_dir) -> None:
        from pathlib import Path

        self._root = Path(root_dir)

    @property
    def name(self) -> str:
        return "read"

    @property
    def definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "read",
                "description": (
                    "Read content from a file path or URL."
                    " Provide a file path relative to the project root, or a URL starting with http:// or https://."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "File path relative to project root, or a URL.",
                        },
                    },
                    "required": ["source"],
                },
            },
        }

    async def execute(self, arguments: str) -> str:
        try:
            parsed = json.loads(arguments)
            source = parsed["source"]

            if source.startswith("http://") or source.startswith("https://"):
                return await self._fetch_url(source)
            else:
                return self._read_file(source)
        except Exception as e:
            return f"[error] {e}"

    def _read_file(self, path: str) -> str:
        target = _resolve_safe(self._root, path)
        return target.read_text(encoding="utf-8")

    async def _fetch_url(self, url: str) -> str:
        import httpx

        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()

            content_bytes = resp.content
            if len(content_bytes) > 1_048_576:
                content_bytes = content_bytes[:1_048_576]

            text = content_bytes.decode("utf-8", errors="replace")

            content_type = resp.headers.get("content-type", "")
            if "html" in content_type:
                text = _strip_html(text)

            return text
