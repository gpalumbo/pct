"""UserProvider — manual human execution provider (stub)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from pct.agent.models import AgentConfig, AgentResult


class UserProvider:
    """Agent provider for manual human execution via UI.

    Not yet implemented — raises NotImplementedError on all operations.
    """

    def __init__(self, agent_config: AgentConfig | None = None) -> None:
        self.agent_config = agent_config

    @property
    def name(self) -> str:
        if self.agent_config is not None:
            return f"User({self.agent_config.id})"
        return "User"

    async def execute(
        self,
        messages: list[dict[str, str]],
        on_token: Callable[[str], Awaitable[None]] | None = None,
    ) -> AgentResult:
        raise NotImplementedError("UserProvider is not yet implemented")

    async def interrupt(self) -> None:
        raise NotImplementedError("UserProvider is not yet implemented")
