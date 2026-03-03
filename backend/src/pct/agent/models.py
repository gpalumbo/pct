"""Agent execution models — tool calls, messages, context, config, results."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from pct.models.enums import AgentType, ProviderType, TaskOutcome


class ToolCall(BaseModel):
    """A tool invocation requested by the LLM."""

    model_config = {"extra": "forbid"}

    id: str
    function_name: str
    arguments: str  # raw JSON string from LLM


class ToolResult(BaseModel):
    """Result of executing a single tool call."""

    model_config = {"extra": "forbid"}

    tool_call_id: str
    name: str
    output: str = ""
    error: str | None = None


class LLMMessage(BaseModel):
    """Single message in an LLM conversation."""

    model_config = {"extra": "forbid"}

    role: Literal["system", "user", "assistant", "tool"]
    content: str
    timestamp: datetime | None = None
    tokens: int | None = None


class ContextMetadata(BaseModel):
    """Token counts and tier breakdown for the assembled context."""

    model_config = {"extra": "forbid"}

    total_tokens: int = 0
    tier_breakdown: dict[str, int] = Field(default_factory=dict)
    items_included: int = 0
    items_excluded: int = 0
    retries_summarized: int = 0
    budget: int = 0


class AssembledContext(BaseModel):
    """Final context passed to an agent after context manager compression."""

    model_config = {"extra": "forbid"}

    base: str = ""
    retries: str = ""
    rag: str = ""
    metadata: ContextMetadata = Field(default_factory=ContextMetadata)

    @property
    def full_text(self) -> str:
        parts = [p for p in (self.base, self.retries, self.rag) if p]
        return "\n\n".join(parts)


class AgentConfig(BaseModel):
    """Configuration for an agent executor."""

    model_config = {"extra": "forbid"}

    id: str
    agent_type: AgentType
    provider_type: ProviderType
    model: str
    prompt_template: str | None = None
    lora: str | None = None
    cli_command: str | None = None
    context_length: int | None = None
    temperature: float | None = None


class AgentResult(BaseModel):
    """Outcome of a single agent execution turn."""

    outcome: TaskOutcome = TaskOutcome.in_progress
    output: str = ""
    messages: list[LLMMessage] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tokens_input: int = 0
    tokens_output: int = 0
    duration_seconds: float = 0.0
    error: str | None = None


class AgentJob(BaseModel):
    """Queued unit of work for the agent concurrency pool."""

    model_config = {"extra": "forbid"}

    task_id: str
    feature_id: str
    context: AssembledContext
    agent_type: ProviderType
    stage: str
