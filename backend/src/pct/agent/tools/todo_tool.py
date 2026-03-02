"""TodoTool — task management via frontmatter files."""

from pathlib import Path
from typing import Any

from pct.models.core import Task
from pct.storage.task_io import delete_task, list_tasks, load_task, load_task_body, save_task


class TodoTool:
    def __init__(self, project_root: Path):
        self.project_root = project_root

    @property
    def name(self) -> str:
        return "todo"

    @property
    def description(self) -> str:
        return "Manage tasks: list, get, create, edit, delete."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "get", "create", "edit", "delete"]},
                "feature_id": {"type": "string"},
                "task_id": {"type": "string"},
                "title": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["action", "feature_id"],
        }

    async def execute(
        self,
        action: str = "list",
        feature_id: str = "",
        task_id: str = "",
        title: str = "",
        content: str = "",
        **kwargs: Any,
    ) -> str:
        if action == "list":
            tasks = list_tasks(self.project_root, feature_id)
            if not tasks:
                return "No tasks found."
            return "\n".join(f"- {t.id}: {t.title} [{t.current_stage_id}]" for t in tasks)

        elif action == "get":
            task = load_task(self.project_root, feature_id, task_id)
            if task is None:
                return f"Task not found: {task_id}"
            body = load_task_body(self.project_root, feature_id, task_id)
            return f"# {task.title}\nStage: {task.current_stage_id}\n\n{body}"

        elif action == "create":
            task = Task(
                id=task_id,
                title=title or task_id,
                feature_id=feature_id,
                current_stage_id="refine-spec",
            )
            save_task(self.project_root, task, body=content)
            return f"Created task: {task_id}"

        elif action == "edit":
            task = load_task(self.project_root, feature_id, task_id)
            if task is None:
                return f"Task not found: {task_id}"
            if title:
                task.title = title
            save_task(self.project_root, task, body=content)
            return f"Updated task: {task_id}"

        elif action == "delete":
            if delete_task(self.project_root, feature_id, task_id):
                return f"Deleted task: {task_id}"
            return f"Task not found: {task_id}"

        return f"Unknown action: {action}"
