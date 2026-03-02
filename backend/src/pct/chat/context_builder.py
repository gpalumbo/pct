"""Context builder — resolve task context with template variable expansion."""

import re
from pathlib import Path

from pct.board.wikilinks import parse_wikilink
from pct.storage.feature_io import load_feature_spec
from pct.storage.task_io import load_task, load_task_body


def expand_template(template: str, variables: dict[str, str]) -> str:
    """Expand {{variable}} placeholders. Missing variables left as-is."""
    def replacer(match: re.Match) -> str:
        key = match.group(1).strip()
        return variables.get(key, match.group(0))

    return re.sub(r"\{\{(\s*\w+\s*)\}\}", replacer, template)


def resolve_task_context(
    project_root: Path,
    feature_id: str,
    task_id: str,
    custom_variables: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build the full context variables for a task.

    Returns a dict of variable_name → content suitable for template expansion.
    """
    variables: dict[str, str] = {}

    # Load task
    task = load_task(project_root, feature_id, task_id)
    if task is None:
        return variables

    # Built-in variables
    variables["task_title"] = task.title
    variables["feature_title"] = feature_id  # Will be overridden if feature loads
    variables["artifact_work_dir"] = f"work/{feature_id}/{task_id}/"
    variables["artifact_file_path"] = f"work/{feature_id}/{feature_id}.md"

    # Load artifact content
    artifact_content = load_task_body(project_root, feature_id, task_id)
    variables["artifact"] = artifact_content

    # Load feature spec for feature_title
    feature_spec = load_feature_spec(project_root, feature_id)
    if feature_spec:
        variables["feature_title"] = feature_id

    # Resolve blocked_by content
    blocked_by_parts = []
    for link in task.blocked_by:
        dep_feat, dep_task = parse_wikilink(link)
        if dep_task:
            dep_body = load_task_body(project_root, dep_feat, dep_task)
            if dep_body:
                blocked_by_parts.append(f"## {dep_feat}#{dep_task}\n{dep_body}")
    variables["blocked_by"] = "\n\n".join(blocked_by_parts)

    # Resolve cross_refs content
    cross_ref_parts = []
    for link in task.cross_refs:
        ref_feat, ref_task = parse_wikilink(link)
        if ref_task:
            ref_body = load_task_body(project_root, ref_feat, ref_task)
            if ref_body:
                cross_ref_parts.append(f"## {ref_feat}#{ref_task}\n{ref_body}")
    variables["cross_refs"] = "\n\n".join(cross_ref_parts)

    # Merge custom variables (user-defined take lower precedence than built-in)
    if custom_variables:
        for k, v in custom_variables.items():
            if k not in variables:
                variables[k] = v

    return variables
