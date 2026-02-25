"""Wikilink extraction and resolution for cross-referencing world artifacts."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pct.board.models import Feature

# Match [[...]] patterns, capturing the inner text
_WIKILINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")


def extract_wikilinks(text: str) -> list[str]:
    """Extract all ``[[Name]]`` link targets from markdown text."""
    return _WIKILINK_RE.findall(text)


def resolve_wikilinks(
    link_targets: list[str],
    features: list[Feature],
) -> list[tuple[str, str]]:
    """Resolve wikilink targets to ``(feature_id, task_id)`` tuples.

    For each link target, searches all tasks across all features for a
    case-insensitive title match.  Prefers exact matches over substring.
    """
    results: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for target in link_targets:
        target_lower = target.strip().lower()
        exact: tuple[str, str] | None = None
        substring: tuple[str, str] | None = None

        for feature in features:
            for task in feature.tasks:
                title_lower = task.title.strip().lower()
                if title_lower == target_lower:
                    exact = (feature.id, task.id)
                    break
                if target_lower in title_lower and substring is None:
                    substring = (feature.id, task.id)
            if exact:
                break

        match = exact or substring
        if match and match not in seen:
            results.append(match)
            seen.add(match)

    return results
