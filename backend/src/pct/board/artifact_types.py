"""Artifact type definitions with LLM prompt hints for collaborative writing."""

from __future__ import annotations

WRITING_ARTIFACT_TYPES: dict[str, dict[str, str]] = {
    "timeline": {
        "label": "Timeline & History",
        "template_hint": (
            "You are writing a chronological timeline. Focus on events, dates, "
            "cause-and-effect relationships, and historical context. Use [[wikilinks]] "
            "to reference entities (characters, locations, factions) defined elsewhere."
        ),
    },
    "location": {
        "label": "Location",
        "template_hint": (
            "You are writing a location entry. Include physical description, atmosphere, "
            "history, notable inhabitants, and how this place connects to the broader world. "
            "Use [[wikilinks]] to reference related entities."
        ),
    },
    "character": {
        "label": "Character",
        "template_hint": (
            "You are writing a character profile. Cover appearance, personality, motivations, "
            "backstory, relationships with other characters, and role in the story. "
            "Use [[wikilinks]] to reference related entities."
        ),
    },
    "faction": {
        "label": "Faction / Organization",
        "template_hint": (
            "You are writing about a faction or organization. Include founding history, "
            "goals, internal structure, notable members, alliances and rivalries. "
            "Use [[wikilinks]] to reference related entities."
        ),
    },
    "magic-system": {
        "label": "Magic & Religion",
        "template_hint": (
            "You are writing about a magic system or religion. Define rules, limitations, "
            "source of power, cost of use, and cultural attitudes toward it. "
            "Use [[wikilinks]] to reference related entities."
        ),
    },
    "technology": {
        "label": "Technology",
        "template_hint": (
            "You are writing about technology. Describe function, who has access, "
            "societal impact, limitations, and how it shapes the world. "
            "Use [[wikilinks]] to reference related entities."
        ),
    },
    "item": {
        "label": "Item / Artifact",
        "template_hint": (
            "You are writing about a notable item or artifact. Include physical description, "
            "origin, powers or significance, current owner, and its role in the story. "
            "Use [[wikilinks]] to reference related entities."
        ),
    },
    "story-arc": {
        "label": "Story Arc",
        "template_hint": (
            "You are writing a story arc. Outline the premise, major plot points, "
            "character involvement, themes, and how it connects to the broader narrative. "
            "Use [[wikilinks]] to reference related entities."
        ),
    },
    "chapter": {
        "label": "Chapter",
        "template_hint": (
            "You are writing narrative prose for a chapter. Focus on pacing, scene "
            "transitions, dialogue, and advancing the plot. Use [[wikilinks]] to reference "
            "world entities for consistency."
        ),
    },
    "text": {
        "label": "Text",
        "template_hint": "",
    },
}


def get_artifact_type_prompt(artifact_type: str) -> str:
    """Return the LLM template hint for a given artifact type, or empty string.

    Checks user-configured artifact types first, falls back to hardcoded defaults.
    """
    try:
        from pct.settings import service as settings_service

        for at in settings_service.get_artifact_types():
            if at.id == artifact_type:
                return at.template_hint
    except Exception:
        pass

    # Fallback to hardcoded defaults
    entry = WRITING_ARTIFACT_TYPES.get(artifact_type)
    if entry:
        return entry["template_hint"]
    return ""
