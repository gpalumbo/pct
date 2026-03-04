"""Core chat loop orchestration — single-turn execution with tool loops."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from pct.agent.models import AgentResult, AssembledContext, TaskOutcome, ToolCall
from pct.agent.protocols import AgentProvider
from pct.agent.tools._base import ToolRegistry
from loguru import logger


_DEFAULT_MAX_TOOL_ITERATIONS = 10


async def execute_chat_turn(
    provider: AgentProvider,
    context: AssembledContext,
    on_token: Callable[[str], Awaitable[None]] | None = None,
    timeout_seconds: float | None = None,
    tool_registry: ToolRegistry | None = None,
    max_tool_iterations: int = _DEFAULT_MAX_TOOL_ITERATIONS,
    on_tool_call: Callable[[str, str, str], Awaitable[None]] | None = None,
    on_tool_result: Callable[[str, str, str], Awaitable[None]] | None = None,
    on_flush_bubble: Callable[[], Awaitable[None]] | None = None,
) -> AgentResult:
    """Execute a chat turn with optional tool-use loop.

    Uses ``context.build_llm_messages()`` to construct the message list.
    When *tool_registry* is provided, the LLM may request tool calls. Each
    tool call is executed, the result is appended to the context, and the
    provider is called again — repeating until the LLM produces a final text
    response or *max_tool_iterations* is reached.

    At iteration > 0, ``on_flush_bubble`` is called so the frontend can
    commit the current streaming content as a finalized bubble before the
    next iteration starts.
    """
    messages = context.build_llm_messages()
    now = datetime.now(UTC)

    collected_tokens: list[str] = []

    async def _tracking_callback(token: str) -> None:
        collected_tokens.append(token)
        if on_token is not None:
            await on_token(token)

    tool_definitions = tool_registry.get_definitions() if tool_registry is not None else None
    all_tool_calls: list[ToolCall] = []
    logger.debug("initial messages: {}", messages)
    start = time.monotonic()
    try:
        for _iteration in range(max_tool_iterations + 1):
            if _iteration > 0 and on_flush_bubble is not None:
                # Flush the current streaming content as a finalized bubble
                await on_flush_bubble()
                collected_tokens.clear()

            logger.debug(
                "Executing chat turn with {} messages and {} tools for provider {}",
                len(messages),
                len(tool_definitions or []),
                provider.name,
            )
            coro = provider.execute(messages, on_token=_tracking_callback, tools=tool_definitions)
            if timeout_seconds is not None:
                result = await asyncio.wait_for(coro, timeout=timeout_seconds)
            else:
                result = await coro
            logger.debug("LLM result: {}", result)

            # No tool calls — final response
            if not result.tool_calls or tool_registry is None:
                break

            all_tool_calls.extend(result.tool_calls)

            # Append the assistant message with tool calls to the local message list
            messages.append(
                {
                    "role": "assistant",
                    "content": result.output or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function_name,
                                "arguments": tc.arguments,
                            },
                        }
                        for tc in result.tool_calls
                    ],
                }
            )

            # Execute each tool and append results
            for tc in result.tool_calls:
                logger.info("Tool call: {}({})", tc.function_name, tc.arguments)
                if on_tool_call is not None:
                    await on_tool_call(tc.id, tc.function_name, tc.arguments)
                try:
                    output = await tool_registry.execute(tc.function_name, tc.arguments)
                    error = None
                except Exception as exc:
                    output = ""
                    error = str(exc)

                content = error if error else output
                if error:
                    logger.warning("Tool error [{}]: {}", tc.function_name, error)
                else:
                    preview = output[:200] + ("..." if len(output) > 200 else "")
                    logger.info("Tool result [{}]: {}", tc.function_name, preview)
                if on_tool_result is not None:
                    await on_tool_result(tc.id, tc.function_name, content)

                # Append to local messages for the LLM
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.function_name,
                        "content": content,
                    }
                )

                # Record on the context for persistence
                context.append_tool_result(tc.id, tc.function_name, content)
        else:
            # Exhausted iterations — return what we have with an error note
            result.error = f"Tool loop exceeded {max_tool_iterations} iterations"
            result.outcome = TaskOutcome.error

    except TimeoutError:
        raise
    except Exception as exc:
        logger.error("LLM exception: {}", exc)
        elapsed = time.monotonic() - start
        return AgentResult(
            outcome=TaskOutcome.error,
            error=str(exc),
            duration_seconds=elapsed,
        )

    elapsed = time.monotonic() - start
    result.duration_seconds = elapsed
    result.tool_calls = all_tool_calls

    return result
