"""LocalLLMProvider — wraps a CompletionBackend (llama_cpp or fake) for agent execution."""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger

from pct.agent.models import AgentResult, TaskOutcome, ToolCall
from pct.agent.protocols import CompletionBackend


def _suppress_llama_logs() -> None:
    """Install a log callback that only passes through perf context lines."""
    try:
        import ctypes

        import llama_cpp

        if getattr(_suppress_llama_logs, "_installed", False):
            return

        @llama_cpp.llama_log_callback  # type: ignore[misc]
        def _log_callback(level, message, user_data):
            text = message.decode("utf-8", errors="replace") if isinstance(message, bytes) else message
            if "llama_perf_context_print" in text:
                print(text, end="", flush=True)

        # Keep a reference so the ctypes callback isn't garbage-collected
        _suppress_llama_logs._cb = _log_callback  # type: ignore[attr-defined]
        llama_cpp.llama_log_set(_log_callback, ctypes.c_void_p())
        _suppress_llama_logs._installed = True  # type: ignore[attr-defined]
    except Exception:
        pass  # If anything fails, just use default logging


def _parse_tool_calls_from_content(content: str) -> list[ToolCall]:
    """Extract tool calls from text content as a fallback.

    Some local LLMs emit tool calls as text in the content field rather
    than populating the structured ``tool_calls`` response field.  Handles:

    * ``<tool_call>{"name": ..., "arguments": ...}</tool_call>`` tags
    * A bare JSON object with a ``"name"`` key
    """
    if not content:
        return []

    tool_calls: list[ToolCall] = []

    # Try <tool_call>...</tool_call> tags first
    tag_matches = re.findall(
        r"<tool_call>\s*(.*?)\s*</tool_call>", content, re.DOTALL
    )

    if not tag_matches:
        # Fall back to a bare JSON object
        stripped = content.strip()
        if stripped.startswith("{"):
            tag_matches = [stripped]

    for raw in tag_matches:
        try:
            if raw.startswith("{{") and raw.endswith("}}"):
                # Some LLMs wrap JSON in extra braces: {{"name": ...}}
                data = json.loads(raw[1:-1])
            else:   
                data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse tool call JSON")
            continue

        if not isinstance(data, dict) or "name" not in data:
            continue

        tc_id = data.get("id", f"call_{uuid.uuid4().hex[:8]}")
        arguments = data.get("arguments", data.get("parameters", {}))
        if isinstance(arguments, dict):
            arguments = json.dumps(arguments)

        tool_calls.append(
            ToolCall(
                id=tc_id,
                function_name=data["name"],
                arguments=arguments,
            )
        )

    return tool_calls


class LocalLLMProvider:
    """Agent provider backed by a local LLM via CompletionBackend protocol.

    If no ``backend`` is provided, attempts to load llama_cpp.Llama from
    ``model_path``.
    """

    def __init__(
        self,
        backend: CompletionBackend | None = None,
        model_path: str | None = None,
        context_length: int | None = None,
        n_gpu_layers: int | None = None,
        temperature: float | None = None,
    ) -> None:
        if backend is not None:
            self._backend = backend
        elif model_path is not None:
            from pct.agent._llama_compat import require_llama

            Llama = require_llama()
            kwargs: dict[str, Any] = {
                # n_ctx=0 tells llama.cpp to use the model's training context length
                "n_ctx": context_length if context_length is not None else 0,
            }
            if n_gpu_layers is not None:
                kwargs["n_gpu_layers"] = n_gpu_layers
            self._backend = Llama(model_path=model_path, verbose=False, **kwargs)

            # Install after Llama() — verbose=False sets a no-op callback
            # internally, so we override it to keep perf context lines.
            _suppress_llama_logs()
        else:
            raise ValueError("Either backend or model_path must be provided")

        self._temperature = temperature
        self._interrupted = False

    async def execute(
        self,
        messages: list[dict[str, str]],
        on_token: Callable[[str], Awaitable[None]] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> AgentResult:
        """Execute a chat completion against the backend."""
        self._interrupted = False
        loop = asyncio.get_running_loop()
        # When tools are active, use non-streaming so we can parse tool_calls
        stream = on_token is not None and not tools

        try:
            if stream:
                return await self._execute_streaming(messages, on_token, loop)
            else:
                return await self._execute_non_streaming(messages, loop, tools=tools)
        except Exception as exc:
            return AgentResult(
                outcome=TaskOutcome.ERROR,
                error=str(exc),
            )

    async def _execute_non_streaming(
        self,
        messages: list[dict[str, str]],
        loop: asyncio.AbstractEventLoop,
        tools: list[dict[str, Any]] | None = None,
    ) -> AgentResult:
        kwargs: dict[str, Any] = {}
        if tools:
            kwargs["tools"] = tools
        if self._temperature is not None:
            kwargs["temperature"] = self._temperature
        response = await loop.run_in_executor(
            None,
            lambda: self._backend.create_chat_completion(
                messages, stream=False, **kwargs
            ),
        )
        choice = response["choices"][0]
        message = choice["message"]
        content = message.get("content") or ""
        usage = response.get("usage", {})

        # Parse tool calls if present
        raw_tool_calls = message.get("tool_calls") or []
        parsed_tool_calls = [
            ToolCall(
                id=tc["id"],
                function_name=tc["function"]["name"],
                arguments=tc["function"]["arguments"],
            )
            for tc in raw_tool_calls
        ]

        # Fallback: some local models emit tool calls as text in content
        if not parsed_tool_calls and content:
            parsed_tool_calls = _parse_tool_calls_from_content(content)
            if parsed_tool_calls:
                content = ""  # was a tool call, not a text response

        return AgentResult(
            outcome=TaskOutcome.APPROVED,
            output=content,
            tool_calls=parsed_tool_calls,
            tokens_input=usage.get("prompt_tokens", 0),
            tokens_output=usage.get("completion_tokens", 0),
        )

    async def _execute_streaming(
        self,
        messages: list[dict[str, str]],
        on_token: Callable[[str], Awaitable[None]],
        loop: asyncio.AbstractEventLoop,
    ) -> AgentResult:
        queue: asyncio.Queue[str | None | Exception] = asyncio.Queue()

        def _run_stream() -> None:
            try:
                stream_kwargs: dict[str, Any] = {}
                if self._temperature is not None:
                    stream_kwargs["temperature"] = self._temperature
                chunks = self._backend.create_chat_completion(
                    messages, stream=True, **stream_kwargs
                )
                for chunk in chunks:
                    if self._interrupted:
                        break
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        loop.call_soon_threadsafe(queue.put_nowait, content)
            except Exception as exc:
                loop.call_soon_threadsafe(queue.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        loop.run_in_executor(None, _run_stream)

        collected: list[str] = []
        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                return AgentResult(
                    outcome=TaskOutcome.ERROR,
                    output="".join(collected),
                    error=str(item),
                )
            collected.append(item)
            await on_token(item)

        if self._interrupted:
            return AgentResult(
                outcome=TaskOutcome.INTERRUPTED,
                output="".join(collected),
            )
        return AgentResult(
            outcome=TaskOutcome.APPROVED,
            output="".join(collected),
        )

    async def interrupt(self) -> None:
        """Signal the provider to stop generation."""
        self._interrupted = True