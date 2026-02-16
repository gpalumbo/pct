"""Helper functions for todo task file management."""

from __future__ import annotations

import re
from pathlib import Path


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
