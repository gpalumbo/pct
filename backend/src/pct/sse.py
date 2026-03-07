"""Shared SSE (Server-Sent Events) utilities."""

from __future__ import annotations

import json


def sse_event(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"
