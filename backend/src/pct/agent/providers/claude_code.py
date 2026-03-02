"""ClaudeCodeProvider — stub for Claude Code CLI integration."""

from collections.abc import Awaitable, Callable
from typing import Any

from pct.agent.models import AgentResult, TaskOutcome


class ClaudeCodeProvider:
    """Stub provider for Claude Code CLI."""

    def __init__(self, cli_command: str = "claude"):
        self.cli_command = cli_command

    async def execute(
        self,
        messages: list[dict[str, str]],
        on_token: Callable[[str], Awaitable[None]] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> AgentResult:
        return AgentResult(
            outcome=TaskOutcome.failure,
            error="ClaudeCodeProvider not yet implemented",
        )

    async def interrupt(self) -> None:
        pass
