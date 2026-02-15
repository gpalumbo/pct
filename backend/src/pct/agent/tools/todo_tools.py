"""Todo tools: read, create, and edit task files under .pct/active-features/."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import frontmatter


def _tasks_dir(root: Path, feature_id: str) -> Path:
    """Return the tasks directory for a feature."""
    return root / ".pct" / "active-features" / feature_id / "tasks"


def _next_task_id(tasks_dir: Path) -> str:
    """Return the next zero-padded task ID (e.g. '004')."""
    existing = sorted(tasks_dir.glob("*.md"))
    max_id = 0
    for f in existing:
        match = re.match(r"^(\d+)-", f.name)
        if match:
            max_id = max(max_id, int(match.group(1)))
    return f"{max_id + 1:03d}"


def _slugify(title: str) -> str:
    """Convert a title to a kebab-case filename slug."""
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")[:60]


class TodoReadTool:
    """List tasks in a feature or read a single task."""

    def __init__(self, root_dir: Path) -> None:
        self._root = root_dir

    @property
    def name(self) -> str:
        return "todo_read"

    @property
    def definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "todo_read",
                "description": "List all tasks in a feature, or read a single task by ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "feature_id": {
                            "type": "string",
                            "description": "Feature directory name (e.g. '001-core-server').",
                        },
                        "task_id": {
                            "type": "string",
                            "description": "Optional task ID (e.g. '001') to read a single task.",
                        },
                    },
                    "required": ["feature_id"],
                },
            },
        }

    async def execute(self, arguments: str) -> str:
        try:
            parsed = json.loads(arguments)
            tasks_dir = _tasks_dir(self._root, parsed["feature_id"])

            if not tasks_dir.exists():
                return "No tasks directory found for this feature."

            task_id = parsed.get("task_id")
            if task_id:
                # Read single task
                matches = list(tasks_dir.glob(f"{task_id}-*.md"))
                if not matches:
                    return f"[error] Task {task_id} not found."
                post = frontmatter.load(str(matches[0]))
                meta = dict(post.metadata)
                meta["body"] = post.content
                return json.dumps(meta, default=str, indent=2)

            # List all tasks
            files = sorted(tasks_dir.glob("*.md"))
            if not files:
                return "No tasks found."
            summaries = []
            for f in files:
                post = frontmatter.load(str(f))
                summaries.append(
                    f"- {post.metadata.get('id', '???')} | "
                    f"{post.metadata.get('status', '???')} | "
                    f"{post.metadata.get('title', f.stem)}"
                )
            return "\n".join(summaries)
        except Exception as e:
            return f"[error] {e}"


class TodoCreateTool:
    """Create a new task file in a feature."""

    def __init__(self, root_dir: Path) -> None:
        self._root = root_dir

    @property
    def name(self) -> str:
        return "todo_create"

    @property
    def definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "todo_create",
                "description": "Create a new task in a feature's task list.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "feature_id": {
                            "type": "string",
                            "description": "Feature directory name (e.g. '001-core-server').",
                        },
                        "title": {
                            "type": "string",
                            "description": "Task title.",
                        },
                        "body": {
                            "type": "string",
                            "description": "Markdown body with spec, acceptance criteria, etc.",
                        },
                        "priority": {
                            "type": "integer",
                            "description": "Priority level (default 0).",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags for categorization.",
                        },
                        "depends_on": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Task IDs this task depends on.",
                        },
                    },
                    "required": ["feature_id", "title", "body"],
                },
            },
        }

    async def execute(self, arguments: str) -> str:
        try:
            parsed = json.loads(arguments)
            tasks_dir = _tasks_dir(self._root, parsed["feature_id"])
            tasks_dir.mkdir(parents=True, exist_ok=True)

            task_id = _next_task_id(tasks_dir)
            slug = _slugify(parsed["title"])
            now = datetime.now(UTC).isoformat()

            metadata = {
                "id": task_id,
                "title": parsed["title"],
                "feature": parsed["feature_id"],
                "status": "refine-spec",
                "depends_on": parsed.get("depends_on", []),
                "tags": parsed.get("tags", []),
                "priority": parsed.get("priority", 0),
                "created": now,
                "updated": now,
            }

            post = frontmatter.Post(parsed["body"], **metadata)
            filename = f"{task_id}-{slug}.md"
            filepath = tasks_dir / filename
            filepath.write_text(frontmatter.dumps(post), encoding="utf-8")

            return f"Created task {task_id}: {filepath.name}"
        except Exception as e:
            return f"[error] {e}"


class TodoEditTool:
    """Edit an existing task's frontmatter fields."""

    def __init__(self, root_dir: Path) -> None:
        self._root = root_dir

    @property
    def name(self) -> str:
        return "todo_edit"

    @property
    def definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "todo_edit",
                "description": "Edit an existing task's metadata or body.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "feature_id": {
                            "type": "string",
                            "description": "Feature directory name.",
                        },
                        "task_id": {
                            "type": "string",
                            "description": "Task ID (e.g. '001').",
                        },
                        "status": {
                            "type": "string",
                            "description": "New status value.",
                        },
                        "title": {
                            "type": "string",
                            "description": "New title.",
                        },
                        "body": {
                            "type": "string",
                            "description": "New markdown body.",
                        },
                        "priority": {
                            "type": "integer",
                            "description": "New priority.",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "New tags list.",
                        },
                    },
                    "required": ["feature_id", "task_id"],
                },
            },
        }

    async def execute(self, arguments: str) -> str:
        try:
            parsed = json.loads(arguments)
            tasks_dir = _tasks_dir(self._root, parsed["feature_id"])
            matches = list(tasks_dir.glob(f"{parsed['task_id']}-*.md"))

            if not matches:
                return f"[error] Task {parsed['task_id']} not found."

            filepath = matches[0]
            post = frontmatter.load(str(filepath))

            # Update frontmatter fields if provided
            for key in ("status", "title", "priority", "tags"):
                if key in parsed:
                    post.metadata[key] = parsed[key]

            # Update body if provided
            if "body" in parsed:
                post.content = parsed["body"]

            # Auto-update timestamp
            post.metadata["updated"] = datetime.now(UTC).isoformat()

            filepath.write_text(frontmatter.dumps(post), encoding="utf-8")
            return f"Updated task {parsed['task_id']}"
        except Exception as e:
            return f"[error] {e}"
