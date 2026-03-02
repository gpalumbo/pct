"""Shared test fixtures."""

from pathlib import Path

import pytest
import yaml


@pytest.fixture
def tmp_project_root(tmp_path: Path) -> Path:
    """Create a temporary project root with basic structure."""
    (tmp_path / "pct-admin" / "active-features").mkdir(parents=True)
    (tmp_path / "pct-admin" / "feature_backlog").mkdir(parents=True)
    (tmp_path / ".pct").mkdir()
    (tmp_path / "work").mkdir()
    return tmp_path


@pytest.fixture
def sample_pct_yaml(tmp_project_root: Path) -> Path:
    """Write a minimal pct.yaml and return its path."""
    config = {
        "id": "test-project",
        "name": "Test Project",
        "project_type": "coding",
        "directory": str(tmp_project_root),
        "default_agent_id": "default-agent",
        "planning_agent_id": "planning-agent",
        "max_remote_agents": 2,
        "max_local_agents": 1,
        "font_size": 14,
        "features": [],
        "workflow_stages": [
            {"id": "refine-spec", "label": "Refine Spec", "enabled": True, "auto_run": False, "sort_order": 0},
            {"id": "implement", "label": "Implement", "enabled": True, "auto_run": False, "sort_order": 1},
            {"id": "done", "label": "Done", "enabled": True, "auto_run": False, "sort_order": 2},
        ],
        "agents": [],
        "artifact_types": [{"id": "text", "label": "Text"}],
        "users": [],
        "template_variables": [],
        "prompt_templates": [],
        "planning_messages": [],
    }
    yaml_path = tmp_project_root / "pct.yaml"
    yaml_path.write_text(yaml.safe_dump(config, sort_keys=False))
    return yaml_path
