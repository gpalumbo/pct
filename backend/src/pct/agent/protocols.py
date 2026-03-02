"""Agent provider protocol."""

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

from pct.agent.models import AgentResult


@runtime_checkable
class AgentProvider(Protocol):
    async def execute(
        self,
        messages: list[dict[str, str]],
        on_token: Callable[[str], Awaitable[None]] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> AgentResult: ...

    async def interrupt(self) -> None: ...
