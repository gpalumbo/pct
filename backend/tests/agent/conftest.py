"""Test fixtures for the agent module — FakeLlama and helpers."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from pct.agent.models import AssembledContext, ContextMetadata
from pct.agent.providers.local_llm import LocalLLMProvider


class FakeLlama:
    """Implements CompletionBackend protocol. No llama_cpp import needed.

    Configurable responses, failure injection, and call tracking.

    For tool-call testing, pass ``tool_call_responses`` — a dict mapping
    call index (0-based) to a list of tool_call dicts.  When the call
    index matches, a tool_call response is returned instead of text.
    """

    def __init__(
        self,
        responses: list[str] | None = None,
        fail_after: int | None = None,
        stream_chunk_size: int = 4,
        tool_call_responses: dict[int, list[dict[str, Any]]] | None = None,
    ) -> None:
        self.responses = responses or ["Test response."]
        self.fail_after = fail_after
        self.stream_chunk_size = stream_chunk_size
        self.tool_call_responses = tool_call_responses or {}
        self.call_count = 0
        self.last_messages: list[dict[str, str]] = []

    def create_chat_completion(
        self,
        messages: list[dict[str, str]],
        stream: bool = False,
        **kwargs,
    ) -> dict | Iterator[dict]:
        self.last_messages = messages
        idx = self.call_count
        self.call_count += 1

        if self.fail_after is not None and self.fail_after == 0:
            raise RuntimeError("Backend failure (injected)")

        # Return a tool_call response if configured for this call index
        if idx in self.tool_call_responses:
            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": self.tool_call_responses[idx],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }

        response_text = self.responses[idx % len(self.responses)]

        if stream:
            return self._stream_response(response_text)

        return {
            "choices": [
                {
                    "message": {"role": "assistant", "content": response_text},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": len(response_text.split()),
            },
        }

    def _stream_response(self, text: str) -> Iterator[dict]:
        chunks = [text[i : i + self.stream_chunk_size] for i in range(0, len(text), self.stream_chunk_size)]
        for idx, chunk in enumerate(chunks):
            if self.fail_after is not None and idx >= self.fail_after:
                raise RuntimeError("Backend failure during streaming (injected)")
            yield {
                "choices": [
                    {
                        "delta": {"content": chunk},
                        "finish_reason": None if idx < len(chunks) - 1 else "stop",
                    }
                ],
            }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_llama() -> FakeLlama:
    """A FakeLlama that returns a single non-streaming response."""
    return FakeLlama(responses=["Test response."])


@pytest.fixture
def fake_llama_streaming() -> FakeLlama:
    """A FakeLlama configured for streaming tests."""
    return FakeLlama(responses=["Hello from the local LLM!"], stream_chunk_size=4)


@pytest.fixture
def fake_llama_failing() -> FakeLlama:
    """A FakeLlama that fails immediately."""
    return FakeLlama(fail_after=0)


@pytest.fixture
def local_provider(fake_llama: FakeLlama) -> LocalLLMProvider:
    """A LocalLLMProvider backed by FakeLlama."""
    return LocalLLMProvider(backend=fake_llama)


@pytest.fixture
def sample_context() -> AssembledContext:
    """A minimal AssembledContext for tests."""
    return AssembledContext(
        base="You are working on project X.",
        retries="Previous attempt was rejected: missing tests.",
        rag="Similar task: added unit tests for auth module.",
        metadata=ContextMetadata(
            total_tokens=100,
            tier_breakdown={"base": 40, "retries": 30, "rag": 30},
            items_included=1,
            items_excluded=0,
            retries_summarized=1,
            budget=8000,
        ),
    )
