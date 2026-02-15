"""File operation tools: read, write, and edit."""

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


class FileReadTool:
    """Read file contents relative to project root."""

    def __init__(self, root_dir: Path) -> None:
        self._root = root_dir

    @property
    def name(self) -> str:
        return "file_read"

    @property
    def definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "file_read",
                "description": "Read the contents of a file relative to the project root.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path relative to project root.",
                        },
                    },
                    "required": ["path"],
                },
            },
        }

    async def execute(self, arguments: str) -> str:
        try:
            parsed = json.loads(arguments)
            target = _resolve_safe(self._root, parsed["path"])
            return target.read_text(encoding="utf-8")
        except Exception as e:
            return f"[error] {e}"


class FileWriteTool:
    """Write content to a file, creating parent directories as needed."""

    def __init__(self, root_dir: Path) -> None:
        self._root = root_dir

    @property
    def name(self) -> str:
        return "file_write"

    @property
    def definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "file_write",
                "description": (
                    "Write content to a file relative to the project root."
                    " Creates parent directories as needed."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path relative to project root.",
                        },
                        "content": {
                            "type": "string",
                            "description": "The content to write to the file.",
                        },
                    },
                    "required": ["path", "content"],
                },
            },
        }

    async def execute(self, arguments: str) -> str:
        try:
            parsed = json.loads(arguments)
            target = _resolve_safe(self._root, parsed["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(parsed["content"], encoding="utf-8")
            return f"Wrote {len(parsed['content'])} chars to {parsed['path']}"
        except Exception as e:
            return f"[error] {e}"


class FileEditTool:
    """Replace a single occurrence of old_text with new_text in a file."""

    def __init__(self, root_dir: Path) -> None:
        self._root = root_dir

    @property
    def name(self) -> str:
        return "file_edit"

    @property
    def definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "file_edit",
                "description": "Replace a single occurrence of old_text with new_text in a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path relative to project root.",
                        },
                        "old_text": {
                            "type": "string",
                            "description": "The exact text to find and replace.",
                        },
                        "new_text": {
                            "type": "string",
                            "description": "The replacement text.",
                        },
                    },
                    "required": ["path", "old_text", "new_text"],
                },
            },
        }

    async def execute(self, arguments: str) -> str:
        try:
            parsed = json.loads(arguments)
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
            return f"Edited {parsed['path']}"
        except Exception as e:
            return f"[error] {e}"
