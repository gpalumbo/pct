"""LocalLLMProvider — wraps a CompletionBackend (llama_cpp or fake) for agent execution."""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from pct.agent.models import AgentConfig, AgentResult, ToolCall
from pct.agent.protocols import CompletionBackend
from pct.models.enums import TaskOutcome
from loguru import logger


def _brace_fix_candidates(raw: str):
    """Yield the raw string, then variants with extra leading/trailing braces stripped."""
    yield raw
    has_extra_open = raw.startswith("{{")
    has_extra_close = raw.endswith("}}")
    if has_extra_open:
        yield raw[1:]
    if has_extra_close:
        yield raw[:-1]
    if has_extra_open and has_extra_close:
        yield raw[1:-1]


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
    tag_matches = re.findall(r"<tool_call>\s*(.*?)\s*</tool_call>", content, re.DOTALL)

    if not tag_matches:
        # Fall back to a bare JSON object
        stripped = content.strip()
        if stripped.startswith("{"):
            tag_matches = [stripped]

    for raw in tag_matches:
        data = None
        for candidate in _brace_fix_candidates(raw):
            try:
                data = json.loads(candidate)
                break
            except json.JSONDecodeError:
                continue
        if data is None:
            logger.warning("Failed to parse tool call JSON")
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


def _strip_tool_call_tags(text: str) -> str:
    """Remove ``<tool_call>...</tool_call>`` blocks from text."""
    return re.sub(r"\s*<tool_call>.*?</tool_call>\s*", "", text, flags=re.DOTALL).strip()


class _ToolCallStreamFilter:
    """Buffers streaming tokens to suppress ``<tool_call>...</tool_call>`` blocks.

    Raw tokens are accumulated and only forwarded to ``on_token`` when they are
    confirmed *not* to be part of a tool-call tag.  The provider's own
    ``collected`` list still records every token so tool-call parsing works on
    the full text.
    """

    _OPEN = "<tool_call>"
    _CLOSE = "</tool_call>"

    def __init__(self, on_token: Callable[[str], Awaitable[None]]) -> None:
        self._on_token = on_token
        self._buffer = ""
        self._suppressing = False

    async def feed(self, token: str) -> None:
        self._buffer += token
        await self._process()

    async def _process(self) -> None:
        while self._buffer:
            if self._suppressing:
                idx = self._buffer.find(self._CLOSE)
                if idx != -1:
                    # End of tag found — discard everything up to & including it
                    self._buffer = self._buffer[idx + len(self._CLOSE) :]
                    self._suppressing = False
                    continue
                # Could be a partial close tag at the tail — keep buffering
                for i in range(1, len(self._CLOSE)):
                    if self._buffer.endswith(self._CLOSE[:i]):
                        return
                # No partial match — discard buffer (still inside tag)
                self._buffer = ""
                return
            else:
                idx = self._buffer.find(self._OPEN)
                if idx != -1:
                    before = self._buffer[:idx]
                    if before:
                        await self._on_token(before)
                    self._buffer = self._buffer[idx + len(self._OPEN) :]
                    self._suppressing = True
                    continue
                # Could be a partial open tag at the tail — hold it back
                for i in range(1, len(self._OPEN)):
                    if self._buffer.endswith(self._OPEN[:i]):
                        safe = self._buffer[: -i]
                        if safe:
                            await self._on_token(safe)
                        self._buffer = self._buffer[-i:]
                        return
                # Nothing suspicious — flush entire buffer
                await self._on_token(self._buffer)
                self._buffer = ""
                return

    async def finish(self) -> None:
        """Flush any remaining non-suppressed text."""
        if self._buffer and not self._suppressing:
            await self._on_token(self._buffer)
        self._buffer = ""


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
        temperature: float | None = None,
        agent_config: AgentConfig | None = None,
    ) -> None:
        self.agent_config = agent_config
        if backend is not None:
            self._backend = backend
        elif model_path is not None:
            try:
                from llama_cpp import Llama
            except ImportError:
                msg = "llama-cpp-python is not installed. Install with: pip install llama-cpp-python"
                raise RuntimeError(msg) from None

            kwargs: dict[str, Any] = {
                "n_ctx": context_length if context_length is not None else 0,
            }
            self._backend = Llama(model_path=model_path, verbose=False, **kwargs)
        else:
            raise ValueError("Either backend or model_path must be provided")

        self._temperature = temperature
        self._interrupted = False

    @property
    def name(self) -> str:
        if self.agent_config is not None:
            return f"LocalLLM({self.agent_config.id})"
        return "LocalLLM"

    async def execute(
        self,
        messages: list[dict[str, str]],
        on_token: Callable[[str], Awaitable[None]] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> AgentResult:
        """Execute a chat completion against the backend."""
        self._interrupted = False
        loop = asyncio.get_running_loop()
        stream = on_token is not None

        try:
            if stream:
                return await self._execute_streaming(messages, on_token, loop, tools=tools)
            else:
                return await self._execute_non_streaming(messages, loop, tools=tools)
        except Exception as exc:
            return AgentResult(
                outcome=TaskOutcome.error,
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
            lambda: self._backend.create_chat_completion(messages, stream=False, **kwargs),
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
                content = ""

        return AgentResult(
            outcome=TaskOutcome.approved,
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
        tools: list[dict[str, Any]] | None = None,
    ) -> AgentResult:
        queue: asyncio.Queue[str | None | Exception] = asyncio.Queue()

        def _run_stream() -> None:
            try:
                stream_kwargs: dict[str, Any] = {}
                if self._temperature is not None:
                    stream_kwargs["temperature"] = self._temperature
                if tools:
                    stream_kwargs["tools"] = tools
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

        # Filter suppresses <tool_call>…</tool_call> from the UI stream
        # while `collected` keeps the raw text for tool-call parsing.
        stream_filter = _ToolCallStreamFilter(on_token)
        collected: list[str] = []
        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                await stream_filter.finish()
                return AgentResult(
                    outcome=TaskOutcome.error,
                    output="".join(collected),
                    error=str(item),
                )
            collected.append(item)
            await stream_filter.feed(item)

        await stream_filter.finish()

        if self._interrupted:
            return AgentResult(
                outcome=TaskOutcome.interrupted,
                output=_strip_tool_call_tags("".join(collected)),
            )

        full_text = "".join(collected)

        # Check if streamed text contains tool calls
        parsed_tool_calls = _parse_tool_calls_from_content(full_text)
        if parsed_tool_calls:
            # Return any text before the tool call as output
            clean_text = _strip_tool_call_tags(full_text)
            return AgentResult(
                outcome=TaskOutcome.approved,
                output=clean_text,
                tool_calls=parsed_tool_calls,
            )

        return AgentResult(
            outcome=TaskOutcome.approved,
            output=full_text,
        )

    async def interrupt(self) -> None:
        """Signal the provider to stop generation."""
        self._interrupted = True
