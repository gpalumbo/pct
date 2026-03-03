"""Settings service — config CRUD backed by storage layer."""

import logging
from pathlib import Path

from pct.models.core import Project
from pct.storage.project_io import init_project, load_project_config, save_project_config

logger = logging.getLogger(__name__)


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
    _apply_initial_features(project_root, project.project_type)
    return project


def _apply_initial_features(project_root: Path, project_type: str) -> None:
    """Create the initial features and tasks from the project template."""
    from pct.board.models import FeatureCreate, TaskCreate
    from pct.board.service import BoardService
    from pct.settings.templates import get_initial_features

    feat_templates = get_initial_features(project_type)
    if not feat_templates:
        return

    board = BoardService(project_root)

    for feat_tpl in feat_templates:
        try:
            board.create_feature(FeatureCreate(
                id=feat_tpl["id"],
                title=feat_tpl["title"],
            ))
            for task_tpl in feat_tpl.get("tasks", []):
                board.create_task(
                    feat_tpl["id"],
                    TaskCreate(
                        id=task_tpl["id"],
                        title=task_tpl["title"],
                        artifact_type_id=task_tpl.get("artifact_type_id"),
                    ),
                )
        except Exception:
            logger.exception("Failed to create initial feature %s", feat_tpl["id"])


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
