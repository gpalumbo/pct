"""Project-type templates: workflow stages and initial feature/tasks."""

from __future__ import annotations


def _stage(stage_id: str, label: str, prompt_template: str = "") -> dict:
    d: dict = {"stage": stage_id, "label": label, "enabled": True, "agent": None}
    if prompt_template:
        d["prompt_template"] = prompt_template
    return d


def _task(title: str, artifact_type: str = "text") -> dict:
    d: dict = {"title": title}
    if artifact_type != "text":
        d["artifact_type"] = artifact_type
    return d


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
    "writing": {
        "stages": [
            _stage(
                "concept",
                "Concept",
                "Help the user brainstorm and develop the core concept."
                " Read {{artifact}} if it exists and suggest expansions.",
            ),
            _stage(
                "outline",
                "Outline",
                "Help structure and outline the content. Reference {{cross_refs}} for world consistency.",
            ),
            _stage(
                "draft",
                "Draft",
                "Write or expand the draft. Use {{artifact}} as the working document."
                " Reference {{cross_refs}} for world consistency.",
            ),
            _stage(
                "revise",
                "Revise",
                "Review {{artifact}} for quality, consistency, and completeness."
                " Cross-check against {{cross_refs}}. Suggest specific improvements.",
            ),
            _stage(
                "polish",
                "Polish",
                "Final polish of {{artifact}}. Fix grammar, improve prose, ensure consistency with {{cross_refs}}.",
            ),
            _stage("done", "Done"),
        ],
        "initial_features": [
            {
                "id": "f0-timeline",
                "title": "Timeline & History",
                "tasks": [
                    _task("Establish world chronology", "timeline"),
                ],
            },
            {
                "id": "f1-locations",
                "title": "Locations",
                "tasks": [
                    _task("Define major regions and geography", "location"),
                    _task("Detail key cities and landmarks", "location"),
                ],
            },
            {
                "id": "f2-characters",
                "title": "Characters",
                "tasks": [
                    _task("Create protagonist profile", "character"),
                    _task("Create antagonist profile", "character"),
                ],
            },
            {
                "id": "f3-factions",
                "title": "Factions & Organizations",
                "tasks": [
                    _task("Outline major factions and power structures", "faction"),
                    _task("Define faction relationships and conflicts", "faction"),
                ],
            },
            {
                "id": "f4-magic-religion",
                "title": "Magic & Religion",
                "tasks": [
                    _task("Define magic system rules and limitations", "magic-system"),
                    _task("Outline religious traditions and beliefs", "magic-system"),
                ],
            },
            {
                "id": "f5-technology",
                "title": "Technology",
                "tasks": [
                    _task("Define technology level and key inventions", "technology"),
                ],
            },
            {
                "id": "f6-items",
                "title": "Items & Artifacts",
                "tasks": [
                    _task("Catalog significant items and their origins", "item"),
                ],
            },
        ],
    },
}


def get_template(project_type: str) -> dict | None:
    """Return the template for a project type, or None if not found."""
    return TEMPLATES.get(project_type)
