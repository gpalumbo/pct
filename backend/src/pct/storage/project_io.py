"""Project configuration I/O — load/save pct.yaml."""

from pathlib import Path

import yaml

from pct.models.core import Project
from pct.storage._atomic import atomic_write
from pct.storage.directory_manager import ensure_project_dirs


def load_project_config(project_root: Path) -> Project | None:
    """Load Project from pct.yaml. Returns None if file doesn't exist."""
    yaml_path = project_root / "pct.yaml"
    if not yaml_path.exists():
        return None
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if data is None:
        return None
    return Project(**data)


def save_project_config(project_root: Path, project: Project) -> None:
    """Atomically write Project to pct.yaml."""
    yaml_path = project_root / "pct.yaml"
    content = yaml.safe_dump(
        project.model_dump(mode="json"),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    atomic_write(yaml_path, content)


def init_project(project_root: Path, project: Project) -> None:
    """Initialize a new project: create dirs, write pct.yaml."""
    ensure_project_dirs(project_root)
    save_project_config(project_root, project)

    # Create project spec placeholder
    spec_path = project_root / "pct-admin" / "project_spec.md"
    if not spec_path.exists():
        spec_path.write_text(f"# {project.name}\n\nProject specification.\n", encoding="utf-8")

    # Create work/INDEX.md
    index_path = project_root / "work" / "INDEX.md"
    if not index_path.exists():
        index_path.write_text(f"# {project.name} — Project Index\n\n## Ideas\n\n", encoding="utf-8")
