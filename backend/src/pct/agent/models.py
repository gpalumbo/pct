"""Agent execution models — tool calls, messages, context, config, results."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from pct.models.enums import AgentType, InclusionFlag, ProviderType, ResourceKind, TaskOutcome


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
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_calls: list[ToolCall] | None = None


class ContextMetadata(BaseModel):
    """Token counts and tier breakdown for the assembled context."""

    model_config = {"extra": "forbid"}

    total_tokens: int = 0
    tier_breakdown: dict[str, int] = Field(default_factory=dict)
    items_included: int = 0
    items_excluded: int = 0
    retries_summarized: int = 0
    budget: int = 0


class ContextResource(BaseModel):
    """A non-message resource attached to the assembled context."""

    model_config = {"extra": "forbid"}

    kind: ResourceKind
    label: str = ""
    content: str = ""
    inclusion: InclusionFlag = InclusionFlag.included


class ContextMessage(BaseModel):
    """A single conversation message stored on the context.

    Only user, assistant, and tool_result roles are stored.
    System prompts are reconstructed from prompt fields.
    tool_call messages are synthesized from tool_result metadata.
    """

    model_config = {"extra": "forbid"}

    role: Literal["user", "assistant", "tool_result", "imagegen_positive", "imagegen_negative", "imagegen_result"]
    content: str = ""
    inclusion: InclusionFlag = InclusionFlag.included
    tool_call_id: str | None = None
    tool_name: str | None = None


_TEXT_ROLES: frozenset[str] = frozenset({"user", "assistant", "tool_result"})
_IMAGEGEN_ROLES: frozenset[str] = frozenset({"imagegen_positive", "imagegen_negative", "imagegen_result"})


class AssembledContext(BaseModel):
    """Single source of truth for chat context.

    Carries both non-message context (prompts, resources) and the conversation
    message history.  ``build_llm_messages()`` constructs the API-ready message
    list on demand — no separate history list needed.
    """

    model_config = {"extra": "forbid"}

    project_prompt: str = ""
    agent_prompt: str = ""
    stage_prompt: str = ""
    resources: list[ContextResource] = Field(default_factory=list)
    messages: list[ContextMessage] = Field(default_factory=list)
    metadata: ContextMetadata = Field(default_factory=ContextMetadata)

    def build_system_prompt(self) -> str:
        """Join non-empty prompts and included resources into a system prompt."""
        parts: list[str] = []
        for p in (self.stage_prompt, self.agent_prompt, self.project_prompt):
            if p:
                parts.append(p)
        for r in self.resources:
            if r.inclusion != InclusionFlag.excluded and r.content:
                header = f"[{r.kind.value}] {r.label}".strip() if r.label else f"[{r.kind.value}]"
                parts.append(f"{header}\n{r.content}")
        return "\n\n".join(parts)

    def build_llm_messages(self) -> list[dict]:
        """Construct the LLM-ready message list.

        - System prompt (if non-empty) as the first message.
        - For tool_result messages, synthesizes the required assistant
          tool_call wrapper with ``arguments: "{}"``.
        - Excluded messages are skipped.
        """
        out: list[dict] = []
        sys_prompt = self.build_system_prompt()
        if sys_prompt:
            out.append({"role": "system", "content": sys_prompt})

        pending_tool_results: list[ContextMessage] = []

        for msg in self.messages:
            if msg.inclusion == InclusionFlag.excluded:
                continue

            # Skip non-LLM roles (imagegen context etc.)
            if msg.role not in _TEXT_ROLES:
                continue

            if msg.role == "tool_result":
                pending_tool_results.append(msg)
                continue

            # Flush any pending tool_results before the next non-tool message
            if pending_tool_results:
                out.extend(self._flush_tool_results(pending_tool_results))
                pending_tool_results = []

            out.append({"role": msg.role, "content": msg.content})

        # Flush remaining tool_results at the end
        if pending_tool_results:
            out.extend(self._flush_tool_results(pending_tool_results))

        return out

    @staticmethod
    def _flush_tool_results(results: list[ContextMessage]) -> list[dict]:
        """Synthesize assistant tool_call wrapper + tool result messages."""
        msgs: list[dict] = []
        # Synthesize the assistant message with tool_calls
        tool_calls = []
        for r in results:
            tool_calls.append({
                "id": r.tool_call_id or "unknown",
                "type": "function",
                "function": {
                    "name": r.tool_name or "unknown",
                    "arguments": "{}",
                },
            })
        msgs.append({
            "role": "assistant",
            "content": "",
            "tool_calls": tool_calls,
        })
        # Append individual tool result messages
        for r in results:
            msgs.append({
                "role": "tool",
                "tool_call_id": r.tool_call_id or "unknown",
                "name": r.tool_name or "unknown",
                "content": r.content,
            })
        return msgs

    def append_user(self, content: str) -> None:
        """Append a user message."""
        self.messages.append(ContextMessage(role="user", content=content))

    def append_assistant(self, content: str) -> None:
        """Append an assistant message."""
        self.messages.append(ContextMessage(role="assistant", content=content))

    def append_tool_result(
        self, tool_call_id: str, tool_name: str, content: str
    ) -> None:
        """Append a tool result message."""
        self.messages.append(
            ContextMessage(
                role="tool_result",
                content=content,
                tool_call_id=tool_call_id,
                tool_name=tool_name,
            )
        )

    def append_imagegen_positive(self, content: str) -> None:
        """Append an imagegen positive prompt message."""
        self.messages.append(ContextMessage(role="imagegen_positive", content=content))

    def append_imagegen_negative(self, content: str) -> None:
        """Append an imagegen negative prompt message."""
        self.messages.append(ContextMessage(role="imagegen_negative", content=content))

    def append_imagegen_result(self, content: str) -> None:
        """Append an imagegen result message (JSON or newline-separated image paths)."""
        self.messages.append(ContextMessage(role="imagegen_result", content=content))

    def get_imagegen_messages(self) -> list[ContextMessage]:
        """Return only imagegen messages (for imagegen context)."""
        return [
            m for m in self.messages
            if m.role in _IMAGEGEN_ROLES
            and m.inclusion != InclusionFlag.excluded
        ]


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
