"""Settings service — config CRUD backed by storage layer."""

from pathlib import Path

from pct.models.core import Project
from pct.storage.project_io import init_project, load_project_config, save_project_config


def get_project_status(project_root: Path) -> dict:
    """Check if project is initialized."""
    config = load_project_config(project_root)
    return {
        "initialized": config is not None,
        "project_id": config.id if config else None,
        "project_name": config.name if config else None,
    }


def get_project_config(project_root: Path) -> Project | None:
    return load_project_config(project_root)


def update_project_config(project_root: Path, project: Project) -> Project:
    save_project_config(project_root, project)
    return project


def initialize_project(project_root: Path, project: Project) -> Project:
    init_project(project_root, project)
    return project


def browse_files(base_path: Path, rel_path: str = "") -> list[dict]:
    """List directory contents. Prevents directory traversal."""
    target = (base_path / rel_path).resolve()
    # Security: ensure target is under base_path
    if not str(target).startswith(str(base_path.resolve())):
        return []
    if not target.is_dir():
        return []
    entries = []
    for item in sorted(target.iterdir()):
        entries.append({
            "name": item.name,
            "path": str(item.relative_to(base_path)),
            "is_dir": item.is_dir(),
            "size": item.stat().st_size if item.is_file() else 0,
        })
    return entries
