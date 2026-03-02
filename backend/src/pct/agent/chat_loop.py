"""Chat loop — execute agent turns with tool iteration."""

import time
from collections.abc import Awaitable, Callable

from pct.agent.models import AgentResult, TaskOutcome, ToolCall
from pct.agent.protocols import AgentProvider
from pct.agent.tools._base import ToolRegistry

MAX_TOOL_ITERATIONS = 10


async def execute_chat_turn(
    provider: AgentProvider,
    messages: list[dict[str, str]],
    tool_registry: ToolRegistry | None = None,
    on_token: Callable[[str], Awaitable[None]] | None = None,
    timeout: float = 300.0,
) -> AgentResult:
    """Execute a single chat turn with optional tool calling.

    1. Call provider.execute(messages, on_token, tools)
    2. If result contains tool_calls and registry is provided:
       - Execute each tool call
       - Append tool results to messages
       - Loop back (max 10 iterations)
    3. Return final AgentResult
    """
    start = time.time()
    tools = tool_registry.get_definitions() if tool_registry else None
    all_tool_calls: list[ToolCall] = []

    for _iteration in range(MAX_TOOL_ITERATIONS):
        try:
            result = await provider.execute(messages, on_token=on_token, tools=tools)
        except Exception as e:
            return AgentResult(
                outcome=TaskOutcome.failure,
                error=str(e),
                duration_seconds=time.time() - start,
            )

        if not result.tool_calls or tool_registry is None:
            result.duration_seconds = time.time() - start
            result.tool_calls = all_tool_calls + result.tool_calls
            return result

        # Execute tool calls
        for tc in result.tool_calls:
            tool_result = await tool_registry.execute(tc.tool_name, **tc.arguments)
            tc.result = tool_result
            all_tool_calls.append(tc)

            # Add tool results to message history
            messages.append({"role": "assistant", "content": f"[Tool: {tc.tool_name}]"})
            messages.append({"role": "user", "content": f"[Tool Result]\n{tool_result}"})

    # Max iterations reached
    result = AgentResult(
        outcome=TaskOutcome.in_progress,
        output="Max tool iterations reached",
        tool_calls=all_tool_calls,
        duration_seconds=time.time() - start,
    )
    return result
