"""Pydantic models and enums for the agent execution engine."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Enums (from object model spec)
# ---------------------------------------------------------------------------


class AgentType(str, Enum):
    """Types of agents that can execute tasks."""

    LLM = "llm"
    USER = "user"
    TOOL = "tool"


class ProviderType(str, Enum):
    """Agent execution backend."""

    REMOTE_API = "remote"
    LOCAL_LLM = "local"
    USER = "user"


class TaskOutcome(str, Enum):
    """Result of a task execution attempt."""

    APPROVED = "approved"
    REJECTED = "rejected"
    INTERRUPTED = "interrupted"
    IN_PROGRESS = "in-progress"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Message model
# ---------------------------------------------------------------------------


class ToolCall(BaseModel):
    """A tool invocation requested by the LLM."""

    id: str
    function_name: str
    arguments: str  # raw JSON string from LLM


class ToolResult(BaseModel):
    """Result of executing a single tool call."""

    tool_call_id: str
    name: str
    output: str = ""
    error: str | None = None


class LLMMessage(BaseModel):
    """Single message in an LLM conversation."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str
    timestamp: datetime | None = None
    tokens: int | None = None


# ---------------------------------------------------------------------------
# Context models
# ---------------------------------------------------------------------------


class ContextMetadata(BaseModel):
    """Token counts and tier breakdown for the assembled context."""

    total_tokens: int = 0
    tier_breakdown: dict[str, int] = {}
    items_included: int = 0
    items_excluded: int = 0
    retries_summarized: int = 0
    budget: int = 0


class AssembledContext(BaseModel):
    """Final context passed to an agent after context manager compression."""

    base: str = ""
    retries: str = ""
    rag: str = ""
    metadata: ContextMetadata = ContextMetadata()

    @property
    def full_text(self) -> str:
        parts = [p for p in (self.base, self.retries, self.rag) if p]
        return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Agent configuration
# ---------------------------------------------------------------------------


class AgentConfig(BaseModel):
    """Configuration for an agent executor."""

    id: str
    agent_type: AgentType
    provider_type: ProviderType
    model: str
    prompt_template: str | None = None
    lora: str | None = None
    cli_command: str | None = None
    model_path: str | None = None
    context_length: int | None = None


# ---------------------------------------------------------------------------
# Execution result
# ---------------------------------------------------------------------------


class AgentResult(BaseModel):
    """Outcome of a single agent execution turn."""

    outcome: TaskOutcome = TaskOutcome.IN_PROGRESS
    output: str = ""
    messages: list[LLMMessage] = []
    tool_calls: list[ToolCall] = []
    tokens_input: int = 0
    tokens_output: int = 0
    duration_seconds: float = 0.0
    error: str | None = None


# ---------------------------------------------------------------------------
# Agent job (submitted to pool)
# ---------------------------------------------------------------------------


class AgentJob(BaseModel):
    """Queued unit of work for the agent concurrency pool."""

    task_id: str
    feature_id: str
    context: AssembledContext
    agent_type: ProviderType
    stage: str
