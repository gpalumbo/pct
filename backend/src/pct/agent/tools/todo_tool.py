"""Todo tool: manage project tasks with list/get/create/edit/delete actions."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import frontmatter

from pct.agent.tools.todo_tools import _next_task_id, _slugify, _tasks_dir


class TodoTool:
    """Manage project tasks with explicit actions."""

    def __init__(self, root_dir: Path) -> None:
        self._root = root_dir

    @property
    def name(self) -> str:
        return "todo"

    @property
    def definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "todo",
                "description": "Manage project tasks. Use action to list, get, create, edit, or delete tasks.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["list", "get", "create", "edit", "delete"],
                            "description": "The action to perform.",
                        },
                        "feature_id": {
                            "type": "string",
                            "description": "Feature directory name (e.g. '001-core-server').",
                        },
                        "task_id": {
                            "type": "string",
                            "description": "Task ID (e.g. '001'). Required for get, edit, delete.",
                        },
                        "title": {
                            "type": "string",
                            "description": "Task title. Required for create; optional for edit.",
                        },
                        "body": {
                            "type": "string",
                            "description": "Markdown body. Required for create; optional for edit.",
                        },
                        "status": {
                            "type": "string",
                            "description": "Task status. Optional for create and edit.",
                        },
                        "priority": {
                            "type": "integer",
                            "description": "Priority level. Optional for create and edit.",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags for categorization. Optional for create and edit.",
                        },
                        "depends_on": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Task IDs this task depends on. Optional for create and edit.",
                        },
                    },
                    "required": ["action", "feature_id"],
                },
            },
        }

    async def execute(self, arguments: str) -> str:
        try:
            parsed = json.loads(arguments)
            action = parsed.get("action")

            if action == "list":
                return self._list(parsed)
            elif action == "get":
                return self._get(parsed)
            elif action == "create":
                return self._create(parsed)
            elif action == "edit":
                return self._edit(parsed)
            elif action == "delete":
                return self._delete(parsed)
            else:
                return f"[error] Unknown action: {action}"
        except Exception as e:
            return f"[error] {e}"

    def _list(self, parsed: dict) -> str:
        tasks = _tasks_dir(self._root, parsed["feature_id"])

        if not tasks.exists():
            return "No tasks directory found for this feature."

        files = sorted(tasks.glob("*.md"))
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

    def _get(self, parsed: dict) -> str:
        task_id = parsed.get("task_id")
        if not task_id:
            return "[error] task_id is required for get action."

        tasks = _tasks_dir(self._root, parsed["feature_id"])
        if not tasks.exists():
            return "No tasks directory found for this feature."

        matches = list(tasks.glob(f"{task_id}-*.md"))
        if not matches:
            return f"[error] Task {task_id} not found."

        post = frontmatter.load(str(matches[0]))
        meta = dict(post.metadata)
        meta["body"] = post.content
        return json.dumps(meta, default=str, indent=2)

    def _create(self, parsed: dict) -> str:
        if "title" not in parsed:
            return "[error] title is required for create action."
        if "body" not in parsed:
            return "[error] body is required for create action."

        tasks = _tasks_dir(self._root, parsed["feature_id"])
        tasks.mkdir(parents=True, exist_ok=True)

        task_id = _next_task_id(tasks)
        slug = _slugify(parsed["title"])
        now = datetime.now(UTC).isoformat()

        metadata = {
            "id": task_id,
            "title": parsed["title"],
            "feature": parsed["feature_id"],
            "status": parsed.get("status", "refine-spec"),
            "depends_on": parsed.get("depends_on", []),
            "tags": parsed.get("tags", []),
            "priority": parsed.get("priority", 0),
            "created": now,
            "updated": now,
        }

        post = frontmatter.Post(parsed["body"], **metadata)
        filename = f"{task_id}-{slug}.md"
        filepath = tasks / filename
        filepath.write_text(frontmatter.dumps(post), encoding="utf-8")

        return f"Created task {task_id}: {filepath.name}"

    def _edit(self, parsed: dict) -> str:
        task_id = parsed.get("task_id")
        if not task_id:
            return "[error] task_id is required for edit action."

        tasks = _tasks_dir(self._root, parsed["feature_id"])
        matches = list(tasks.glob(f"{task_id}-*.md"))

        if not matches:
            return f"[error] Task {task_id} not found."

        filepath = matches[0]
        post = frontmatter.load(str(filepath))

        for key in ("status", "title", "priority", "tags", "depends_on"):
            if key in parsed:
                post.metadata[key] = parsed[key]

        if "body" in parsed:
            post.content = parsed["body"]

        post.metadata["updated"] = datetime.now(UTC).isoformat()

        filepath.write_text(frontmatter.dumps(post), encoding="utf-8")
        return f"Updated task {task_id}"

    def _delete(self, parsed: dict) -> str:
        task_id = parsed.get("task_id")
        if not task_id:
            return "[error] task_id is required for delete action."

        tasks = _tasks_dir(self._root, parsed["feature_id"])
        matches = list(tasks.glob(f"{task_id}-*.md"))

        if not matches:
            return f"[error] Task {task_id} not found."

        filepath = matches[0]
        filepath.unlink()
        return f"Deleted task {task_id}"
