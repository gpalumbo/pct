"""File tool: write or edit files with an explicit action."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _resolve_safe(root: Path, rel_path: str) -> Path:
    """Resolve *rel_path* under *root*, rejecting directory traversal."""
    target = (root / rel_path).resolve()
    root_resolved = root.resolve()
    if not str(target).startswith(str(root_resolved)):
        raise ValueError(f"Path escapes project root: {rel_path}")
    return target


class FileTool:
    """Write or edit files with an explicit action."""

    def __init__(self, root_dir: Path) -> None:
        self._root = root_dir

    @property
    def name(self) -> str:
        return "file"

    @property
    def definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "file",
                "description": (
                    "Write or edit a file. Use action 'write' to create/overwrite a file,"
                    " or 'edit' to replace a specific text snippet."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["write", "edit"],
                            "description": "The file operation to perform.",
                        },
                        "path": {
                            "type": "string",
                            "description": "File path relative to project root.",
                        },
                        "content": {
                            "type": "string",
                            "description": "The content to write (required for 'write' action).",
                        },
                        "old_text": {
                            "type": "string",
                            "description": "The exact text to find and replace (required for 'edit' action).",
                        },
                        "new_text": {
                            "type": "string",
                            "description": "The replacement text (required for 'edit' action).",
                        },
                    },
                    "required": ["action", "path"],
                },
            },
        }

    async def execute(self, arguments: str) -> str:
        try:
            parsed = json.loads(arguments)
            action = parsed.get("action")

            if action == "write":
                return self._write(parsed)
            elif action == "edit":
                return self._edit(parsed)
            else:
                return f"[error] Unknown action: {action}"
        except Exception as e:
            return f"[error] {e}"

    def _maybe_index(self, file_path: Path) -> None:
        """If path is under work/, index into RAG."""
        try:
            file_path.relative_to(self._root / "work")
        except ValueError:
            return
        try:
            from pct.rag.indexer import index_file
            from pct.settings.service import get_project_config

            cfg = get_project_config()
            if cfg and cfg.project_id:
                index_file(cfg.project_id, file_path)
        except ImportError:
            pass
        except Exception:
            pass

    def _write(self, parsed: dict) -> str:
        if "content" not in parsed:
            return "[error] content is required for write action."
        target = _resolve_safe(self._root, parsed["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(parsed["content"], encoding="utf-8")
        self._maybe_index(target)
        return f"Wrote {len(parsed['content'])} chars to {parsed['path']}"

    def _edit(self, parsed: dict) -> str:
        if "old_text" not in parsed or "new_text" not in parsed:
            return "[error] old_text and new_text are required for edit action."
        target = _resolve_safe(self._root, parsed["path"])
        content = target.read_text(encoding="utf-8")
        old_text = parsed["old_text"]
        new_text = parsed["new_text"]

        if old_text not in content:
            return "[error] old_text not found in file"

        count = content.count(old_text)
        if count > 1:
            return f"[error] old_text found {count} times; must be unique"

        content = content.replace(old_text, new_text, 1)
        target.write_text(content, encoding="utf-8")
        self._maybe_index(target)
        return f"Edited {parsed['path']}"
