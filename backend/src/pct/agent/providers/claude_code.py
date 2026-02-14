"""ClaudeCodeProvider — subprocess-based remote Claude Code CLI provider (stub)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from pct.agent.models import AgentResult


class ClaudeCodeProvider:
    """Agent provider that delegates to Claude Code CLI via subprocess.

    Not yet implemented — raises NotImplementedError on all operations.
    """

    async def execute(
        self,
        messages: list[dict[str, str]],
        on_token: Callable[[str], Awaitable[None]] | None = None,
    ) -> AgentResult:
        raise NotImplementedError("ClaudeCodeProvider is not yet implemented")

    async def interrupt(self) -> None:
        raise NotImplementedError("ClaudeCodeProvider is not yet implemented")
