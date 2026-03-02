"""Directory structure management per tech_spec §1."""

from pathlib import Path


def ensure_project_dirs(project_root: Path) -> None:
    """Create all standard project directories if missing."""
    dirs = [
        project_root / "pct-admin" / "active-features",
        project_root / "pct-admin" / "feature_backlog",
        project_root / ".pct" / "execution" / "active-tasks",
        project_root / ".pct" / "execution" / "completed-tasks",
        project_root / ".pct" / "chat_history",
        project_root / ".pct" / "rag",
        project_root / ".pct" / "kanban_snapshots",
        project_root / "work",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def create_feature_dir(project_root: Path, feature_id: str) -> Path:
    """Create feature directories under pct-admin and work."""
    admin_dir = project_root / "pct-admin" / "active-features" / feature_id / "tasks"
    admin_dir.mkdir(parents=True, exist_ok=True)

    work_dir = project_root / "work" / feature_id
    work_dir.mkdir(parents=True, exist_ok=True)

    return work_dir


def create_task_work_dir(project_root: Path, feature_id: str, task_id: str) -> Path:
    """Create task work directory with images subdirectory."""
    task_dir = project_root / "work" / feature_id / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "images").mkdir(exist_ok=True)
    return task_dir


def ensure_global_config_dir(global_dir: Path) -> None:
    """Create global ~/.pct directories."""
    (global_dir / "registries").mkdir(parents=True, exist_ok=True)
