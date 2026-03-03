"""Read tool: read content from a file path or URL."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pct.agent.tools.file_tools import _resolve_safe


class ReadTool:
    """Read content from a file path or URL. Auto-detects source type."""

    def __init__(self, root_dir: Path) -> None:
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
                    " Provide a file path relative to the project root,"
                    " or a URL starting with http:// or https://."
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
            text = resp.text
            if len(text) > 10000:
                text = text[:10000]
            return text
