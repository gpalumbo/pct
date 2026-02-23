"""Project-type templates: workflow stages and initial feature/tasks."""

from __future__ import annotations


def _stage(stage_id: str, label: str) -> dict:
    return {"stage": stage_id, "label": label, "enabled": True, "agent": None}


def _task(title: str) -> dict:
    return {"title": title}


# ---------------------------------------------------------------------------
# Template definitions
# ---------------------------------------------------------------------------

TEMPLATES: dict[str, dict] = {
    "coding": {
        "stages": [
            _stage("refine-spec", "Refine Spec"),
            _stage("implement", "Implement"),
            _stage("feature-test", "Feature Test"),
            _stage("code-review", "Code Review"),
            _stage("merge", "Merge"),
            _stage("full-test", "Full Test"),
            _stage("push", "Push"),
            _stage("done", "Done"),
        ],
        "initial_feature": {
            "id": "f1-project-setup",
            "title": "Project Setup",
            "tasks": [
                _task("Set up project structure and dependencies"),
                _task("Configure linting and formatting"),
                _task("Add CI/CD pipeline"),
                _task("Write initial README"),
            ],
        },
    },
    "campaign-building": {
        "stages": [
            _stage("concept", "Concept"),
            _stage("world-building", "World Building"),
            _stage("outline", "Outline"),
            _stage("draft", "Draft"),
            _stage("review", "Review"),
            _stage("revise", "Revise"),
            _stage("ready", "Ready"),
            _stage("done", "Done"),
        ],
        "initial_feature": {
            "id": "f1-campaign-foundation",
            "title": "Campaign Foundation",
            "tasks": [
                _task("Define campaign setting and tone"),
                _task("Create key NPCs and factions"),
                _task("Map major locations"),
                _task("Outline Session 1 encounter"),
            ],
        },
    },
    "novel": {
        "stages": [
            _stage("concept", "Concept"),
            _stage("world-building", "World Building"),
            _stage("outline", "Outline"),
            _stage("draft", "Draft"),
            _stage("edit", "Edit"),
            _stage("review", "Review"),
            _stage("final-polish", "Final Polish"),
            _stage("done", "Done"),
        ],
        "initial_feature": {
            "id": "f1-novel-foundation",
            "title": "Novel Foundation",
            "tasks": [
                _task("Define world rules and magic system"),
                _task("Create main character profiles"),
                _task("Outline overall plot arc"),
                _task("Draft opening chapter"),
            ],
        },
    },
}


def get_template(project_type: str) -> dict | None:
    """Return the template for a project type, or None if not found."""
    return TEMPLATES.get(project_type)
