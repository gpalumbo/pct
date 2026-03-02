"""FileTool — write/edit files."""

from pathlib import Path
from typing import Any


class FileTool:
    def __init__(self, project_root: Path):
        self.project_root = project_root

    @property
    def name(self) -> str:
        return "file"

    @property
    def description(self) -> str:
        return "Write or edit files. Actions: 'write' (full content), 'edit' (old→new replacement)."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["write", "edit"]},
                "path": {"type": "string", "description": "File path relative to project root"},
                "content": {"type": "string", "description": "Full content (write) or new text (edit)"},
                "old_text": {"type": "string", "description": "Text to replace (edit only)"},
            },
            "required": ["action", "path"],
        }

    async def execute(
        self,
        action: str = "write",
        path: str = "",
        content: str = "",
        old_text: str = "",
        **kwargs: Any,
    ) -> str:
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = self.project_root / path

        if action == "write":
            return self._write(file_path, content)
        elif action == "edit":
            return self._edit(file_path, old_text, content)
        return f"Unknown action: {action}"

    def _write(self, path: Path, content: str) -> str:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return f"Written: {path}"
        except Exception as e:
            return f"Error: {e}"

    def _edit(self, path: Path, old_text: str, new_text: str) -> str:
        if not path.exists():
            return f"Error: File not found: {path}"
        try:
            content = path.read_text(encoding="utf-8")
            if old_text not in content:
                return f"Error: old_text not found in {path}"
            content = content.replace(old_text, new_text, 1)
            path.write_text(content, encoding="utf-8")
            return f"Edited: {path}"
        except Exception as e:
            return f"Error: {e}"
