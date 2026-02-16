"""Core chat loop orchestration — message building and single-turn execution."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from loguru import logger

from pct.agent.models import AgentResult, AssembledContext, LLMMessage, TaskOutcome
from pct.agent.protocols import AgentProvider
from pct.agent.tools import ToolRegistry


def build_messages(
    context: AssembledContext,
    system_prompt: str | None = None,
) -> list[dict[str, str]]:
    """Convert an AssembledContext into a list of LLM messages.

    Returns a list of ``{"role": ..., "content": ...}`` dicts suitable for
    any chat-completion API.
    """
    messages: list[dict[str, str]] = []
    if system_prompt is not None:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": context.full_text})
    return messages


_DEFAULT_MAX_TOOL_ITERATIONS = 10


async def execute_chat_turn(
    provider: AgentProvider,
    context: AssembledContext,
    system_prompt: str | None = None,
    on_token: Callable[[str], Awaitable[None]] | None = None,
    timeout_seconds: float | None = None,
    tool_registry: ToolRegistry | None = None,
    max_tool_iterations: int = _DEFAULT_MAX_TOOL_ITERATIONS,
) -> AgentResult:
    """Execute a chat turn with optional tool-use loop.

    When *tool_registry* is provided, the LLM may request tool calls. Each
    tool call is executed, the result is appended to the conversation, and the
    provider is called again — repeating until the LLM produces a final text
    response or *max_tool_iterations* is reached.
    """
    messages = build_messages(context, system_prompt)
    now = datetime.now(timezone.utc)

    # Track streamed tokens so we can record them in messages
    collected_tokens: list[str] = []

    async def _tracking_callback(token: str) -> None:
        collected_tokens.append(token)
        if on_token is not None:
            await on_token(token)

    tool_definitions = (
        tool_registry.get_definitions() if tool_registry is not None else None
    )
    all_tool_calls: list = []

    start = time.monotonic()
    try:
        for _iteration in range(max_tool_iterations + 1):
            coro = provider.execute(
                messages, on_token=_tracking_callback, tools=tool_definitions
            )
            if timeout_seconds is not None:
                result = await asyncio.wait_for(coro, timeout=timeout_seconds)
            else:
                result = await coro
            logger.debug("LLM result: {}", result)

            # No tool calls — final response
            if not result.tool_calls or tool_registry is None:
                break

            all_tool_calls.extend(result.tool_calls)

            # Append the assistant message with tool calls (OpenAI format)
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
                try:
                    output = await tool_registry.execute(
                        tc.function_name, tc.arguments
                    )
                    error = None
                except Exception as exc:
                    output = ""
                    error = str(exc)

                content = error if error else output
                if error:
                    logger.warning("Tool error [{}]: {}", tc.function_name, error)
                else:
                    preview = output[:200] + ("…" if len(output) > 200 else "")
                    logger.info("Tool result [{}]: {}", tc.function_name, preview)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": content,
                    }
                )
        else:
            # Exhausted iterations — return what we have with an error note
            result.error = (
                f"Tool loop exceeded {max_tool_iterations} iterations"
            )
            result.outcome = TaskOutcome.ERROR

    except asyncio.TimeoutError:
        raise
    except Exception as exc:
        logger.error("LLM exception: {}", exc )
        elapsed = time.monotonic() - start
        return AgentResult(
            outcome=TaskOutcome.ERROR,
            error=str(exc),
            duration_seconds=elapsed,
        )

    elapsed = time.monotonic() - start
    result.duration_seconds = elapsed
    result.tool_calls = all_tool_calls

    # Build message records for the conversation
    result.messages = [
        LLMMessage(role=m["role"], content=m.get("content", ""), timestamp=now)
        for m in messages
    ]
    if result.output:
        result.messages.append(
            LLMMessage(role="assistant", content=result.output, timestamp=now)
        )

    return result