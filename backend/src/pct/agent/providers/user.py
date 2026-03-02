"""UserProvider — human performs the work (no-op provider)."""

from collections.abc import Awaitable, Callable
from typing import Any

from pct.agent.models import AgentResult, TaskOutcome


class UserProvider:
    """Provider for User agents — always returns in_progress (human must act)."""

    async def execute(
        self,
        messages: list[dict[str, str]],
        on_token: Callable[[str], Awaitable[None]] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> AgentResult:
        return AgentResult(
            outcome=TaskOutcome.in_progress,
            output="Waiting for user action.",
        )

    async def interrupt(self) -> None:
        pass  # No-op for user provider
