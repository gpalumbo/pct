"""Agent execution models."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TaskOutcome(StrEnum):
    success = "success"
    failure = "failure"
    in_progress = "in_progress"


class ToolCall(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: str = ""


class AgentResult(BaseModel):
    outcome: TaskOutcome = TaskOutcome.in_progress
    output: str = ""
    messages: list[dict[str, str]] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tokens_input: int = 0
    tokens_output: int = 0
    duration_seconds: float = 0.0
    error: str | None = None
