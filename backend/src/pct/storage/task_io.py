"""Task I/O — YAML frontmatter markdown files."""

from pathlib import Path

import frontmatter

from pct.models.core import Task
from pct.storage._atomic import atomic_write


def _task_file_path(project_root: Path, feature_id: str, task_id: str) -> Path:
    return project_root / "pct-admin" / "active-features" / feature_id / "tasks" / f"{task_id}.md"


def load_task(project_root: Path, feature_id: str, task_id: str) -> Task | None:
    """Load a task from its frontmatter markdown file."""
    path = _task_file_path(project_root, feature_id, task_id)
    if not path.exists():
        return None
    post = frontmatter.load(str(path))
    metadata = dict(post.metadata)
    metadata.setdefault("feature_id", feature_id)
    metadata.setdefault("id", task_id)
    return Task(**metadata)


def save_task(project_root: Path, task: Task, body: str = "") -> None:
    """Atomically write a task to its frontmatter markdown file."""
    path = _task_file_path(project_root, task.feature_id, task.id)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Build frontmatter data — exclude stage_contexts (stored separately)
    data = task.model_dump(mode="json", exclude={"stage_contexts"})

    post = frontmatter.Post(body, **data)
    content = frontmatter.dumps(post)
    atomic_write(path, content)


def load_task_body(project_root: Path, feature_id: str, task_id: str) -> str:
    """Load just the markdown body of a task file."""
    path = _task_file_path(project_root, feature_id, task_id)
    if not path.exists():
        return ""
    post = frontmatter.load(str(path))
    return post.content


def list_tasks(project_root: Path, feature_id: str) -> list[Task]:
    """List all tasks for a feature."""
    tasks_dir = project_root / "pct-admin" / "active-features" / feature_id / "tasks"
    if not tasks_dir.exists():
        return []
    tasks = []
    for f in sorted(tasks_dir.glob("*.md")):
        task_id = f.stem
        task = load_task(project_root, feature_id, task_id)
        if task is not None:
            tasks.append(task)
    return tasks


def delete_task(project_root: Path, feature_id: str, task_id: str) -> bool:
    """Delete a task file. Returns True if file existed."""
    path = _task_file_path(project_root, feature_id, task_id)
    if path.exists():
        path.unlink()
        return True
    return False
