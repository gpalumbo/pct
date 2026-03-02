"""ReadTool — read files or fetch URLs."""

from pathlib import Path
from typing import Any


class ReadTool:
    def __init__(self, project_root: Path):
        self.project_root = project_root

    @property
    def name(self) -> str:
        return "read"

    @property
    def description(self) -> str:
        return "Read a file from the project or fetch a URL."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path or URL to read"},
            },
            "required": ["path"],
        }

    async def execute(self, path: str = "", **kwargs: Any) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return await self._fetch_url(path)
        return self._read_file(path)

    def _read_file(self, path: str) -> str:
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = self.project_root / path
        if not file_path.exists():
            return f"Error: File not found: {path}"
        try:
            return file_path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading file: {e}"

    async def _fetch_url(self, url: str) -> str:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                return resp.text[:10000]  # Limit response size
        except Exception as e:
            return f"Error fetching URL: {e}"
