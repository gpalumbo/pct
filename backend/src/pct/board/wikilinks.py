"""WikiLink parsing and resolution — [[feature_id#task_id]] format."""

import re

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def extract_wikilinks(text: str) -> list[str]:
    """Extract all WikiLink strings from text."""
    return WIKILINK_RE.findall(text)


def parse_wikilink(link: str) -> tuple[str, str | None]:
    """Parse a WikiLink inner content into (feature_id, task_id | None).

    '[[f1#task-1]]' → ('f1', 'task-1')
    '[[f1]]' → ('f1', None)
    """
    # Strip [[ and ]] if present
    inner = link.strip("[]")
    if "#" in inner:
        parts = inner.split("#", 1)
        return parts[0], parts[1]
    return inner, None


def format_wikilink(feature_id: str, task_id: str | None = None) -> str:
    """Format a WikiLink string."""
    if task_id:
        return f"[[{feature_id}#{task_id}]]"
    return f"[[{feature_id}]]"


def resolve_wikilink(link: str) -> tuple[str, str | None]:
    """Resolve a raw WikiLink string (including brackets)."""
    return parse_wikilink(link)
