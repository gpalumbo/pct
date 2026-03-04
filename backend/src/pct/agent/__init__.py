"""PCT Agent Execution Engine — core chat loop and provider abstractions."""

from pct.agent.chat_loop import execute_chat_turn
from pct.agent.models import (
    AgentConfig,
    AgentJob,
    AgentResult,
    AssembledContext,
    ContextMessage,
    ContextMetadata,
    ContextResource,
    LLMMessage,
    ToolCall,
    ToolResult,
)
from pct.agent.pool import AgentPool
from pct.agent.protocols import AgentProvider, CompletionBackend
from pct.agent.tools import BashTool, Tool, ToolRegistry
from pct.models.enums import AgentType, ProviderType, TaskOutcome

__all__ = [
    # Enums
    "AgentType",
    "ProviderType",
    "TaskOutcome",
    # Models
    "LLMMessage",
    "ContextMetadata",
    "AssembledContext",
    "ContextMessage",
    "ContextResource",
    "AgentConfig",
    "AgentResult",
    "AgentJob",
    "ToolCall",
    "ToolResult",
    # Protocols
    "AgentProvider",
    "CompletionBackend",
    "Tool",
    # Chat loop
    "execute_chat_turn",
    # Tools
    "BashTool",
    "ToolRegistry",
    # Pool
    "AgentPool",
]
