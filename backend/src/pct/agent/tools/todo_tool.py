"""TodoTool — task management via frontmatter files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pct.models.core import Task
from pct.storage.task_io import delete_task, list_tasks, load_task, load_task_body, save_task


class TodoTool:
    def __init__(self, root_dir: Path):
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
                "description": "Manage project tasks: list, get, create, edit, delete.",
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
                            "description": "Feature ID.",
                        },
                        "task_id": {
                            "type": "string",
                            "description": "Task ID. Required for get, edit, delete.",
                        },
                        "title": {
                            "type": "string",
                            "description": "Task title. Required for create; optional for edit.",
                        },
                        "content": {
                            "type": "string",
                            "description": "Task body content.",
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
            feature_id = parsed.get("feature_id", "")
            task_id = parsed.get("task_id", "")
            title = parsed.get("title", "")
            content = parsed.get("content", "")

            if action == "list":
                tasks = list_tasks(self._root, feature_id)
                if not tasks:
                    return "No tasks found."
                return "\n".join(
                    f"- {t.id}: {t.title} [{t.current_stage_id}]" for t in tasks
                )

            elif action == "get":
                task = load_task(self._root, feature_id, task_id)
                if task is None:
                    return f"Task not found: {task_id}"
                body = load_task_body(self._root, feature_id, task_id)
                return f"# {task.title}\nStage: {task.current_stage_id}\n\n{body}"

            elif action == "create":
                task = Task(
                    id=task_id,
                    title=title or task_id,
                    feature_id=feature_id,
                    current_stage_id="refine-spec",
                )
                save_task(self._root, task, body=content)
                return f"Created task: {task_id}"

            elif action == "edit":
                task = load_task(self._root, feature_id, task_id)
                if task is None:
                    return f"Task not found: {task_id}"
                if title:
                    task.title = title
                save_task(self._root, task, body=content)
                return f"Updated task: {task_id}"

            elif action == "delete":
                if delete_task(self._root, feature_id, task_id):
                    return f"Deleted task: {task_id}"
                return f"Task not found: {task_id}"

            return f"[error] Unknown action: {action}"
        except Exception as e:
            return f"[error] {e}"
