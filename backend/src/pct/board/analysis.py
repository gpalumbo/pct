"""Gap analysis and continuity checking for collaborative writing projects."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from pct.agent.models import AssembledContext
from pct.board import service as board_service

logger = logging.getLogger(__name__)


def collect_world_artifacts() -> str:
    """Iterate all features + tasks, load each artifact, concatenate with headers."""
    sections: list[str] = []
    features = board_service.list_features()

    for feature in features:
        for task in feature.tasks:
            artifact = board_service.read_artifact(feature.id, task.id)
            content = artifact.get("content", "")
            if not content:
                continue
            sections.append(
                f"### {feature.title} > {task.title} "
                f"[type: {task.artifact_type}]\n\n{content}"
            )

    if not sections:
        return "_No world artifacts found._"
    return "\n\n---\n\n".join(sections)


def collect_timeline_artifacts() -> str:
    """Collect all artifacts with artifact_type 'timeline'."""
    sections: list[str] = []
    features = board_service.list_features()

    for feature in features:
        for task in feature.tasks:
            if task.artifact_type != "timeline":
                continue
            artifact = board_service.read_artifact(feature.id, task.id)
            content = artifact.get("content", "")
            if not content:
                continue
            sections.append(
                f"### {feature.title} > {task.title}\n\n{content}"
            )

    if not sections:
        return "_No timeline artifacts found._"
    return "\n\n---\n\n".join(sections)


def collect_story_arc_content(feature_id: str) -> str:
    """Load feature spec + all task artifacts within one feature."""
    feature = board_service.get_feature(feature_id)
    if feature is None:
        return ""

    sections: list[str] = []

    if feature.specification:
        sections.append(f"## Feature Specification\n\n{feature.specification}")

    for task in feature.tasks:
        artifact = board_service.read_artifact(feature.id, task.id)
        content = artifact.get("content", "")
        if content:
            sections.append(
                f"### {task.title} [type: {task.artifact_type}]\n\n{content}"
            )

    return "\n\n---\n\n".join(sections) if sections else "_No content found._"


def build_gap_analysis_prompt(feature_id: str) -> AssembledContext:
    """Build prompt for gap analysis of a feature."""
    world_artifacts = collect_world_artifacts()
    story_content = collect_story_arc_content(feature_id)

    prompt = f"""## World Artifacts

{world_artifacts}

---

## Story Content for Analysis

{story_content}

---

## Instructions

Analyze the world-building and story content above. Identify:

1. **Missing artifacts**: Important elements mentioned but not yet developed (characters referenced but not profiled, locations mentioned but not described, etc.)
2. **Underdeveloped artifacts**: Existing entries that need more detail or depth
3. **Suggested new tasks**: Concrete work items that would strengthen the world or story

For each suggestion, output in this structured format:

TASK: [suggested task title] | FEATURE: [target feature id] | TYPE: [artifact type: character, location, faction, timeline, magic-system, technology, item, story-arc, chapter, or text] | REASON: [brief explanation of why this is needed]

Be specific and actionable. Focus on gaps that would most improve consistency and richness of the world."""

    return AssembledContext(base=prompt)


def build_continuity_check_prompt(feature_id: str) -> AssembledContext:
    """Build prompt for continuity checking of a feature."""
    timeline_artifacts = collect_timeline_artifacts()
    world_artifacts = collect_world_artifacts()
    story_content = collect_story_arc_content(feature_id)

    prompt = f"""## Authoritative Timeline / Chronology

{timeline_artifacts}

---

## World Artifacts

{world_artifacts}

---

## Story Content to Check

{story_content}

---

## Instructions

You are a continuity checker. Using the timeline as the authoritative chronology, cross-check all facts between artifacts and the story content. Look for:

1. **Temporal contradictions**: Events in the story that contradict the established timeline
2. **Factual inconsistencies**: Details that conflict between different artifacts (character descriptions, location details, faction relationships, etc.)
3. **Logic gaps**: Events or outcomes that don't follow logically from established rules (magic systems, technology limitations, etc.)
4. **Character continuity**: Personality shifts, knowledge inconsistencies, or relationship contradictions

For each issue found, output in this structured format:

ISSUE: [brief description] | SEVERITY: [high/medium/low] | LOCATION: [which artifact(s) are affected] | SUGGESTION: [how to resolve the inconsistency]

Be thorough but fair — flag genuine contradictions, not stylistic choices."""

    return AssembledContext(base=prompt)
