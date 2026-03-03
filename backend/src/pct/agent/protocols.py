"""Protocol definitions for agent providers and LLM backends."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from typing import Any, Protocol, runtime_checkable

from pct.agent.models import AgentResult


@runtime_checkable
class CompletionBackend(Protocol):
    """Subset of the llama_cpp.Llama API used by LocalLLMProvider.

    Any object implementing ``create_chat_completion`` with this signature
    can serve as a backend — including test fakes.
    """

    def create_chat_completion(
        self,
        messages: list[dict[str, str]],
        stream: bool = False,
        **kwargs: Any,
    ) -> dict | Iterator[dict]: ...


@runtime_checkable
class AgentProvider(Protocol):
    """Common interface for all agent execution backends."""

    async def execute(
        self,
        messages: list[dict[str, str]],
        on_token: Callable[[str], Awaitable[None]] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> AgentResult: ...

    async def interrupt(self) -> None: ...
