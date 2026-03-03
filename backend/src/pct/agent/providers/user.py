"""UserProvider — manual human execution provider (stub)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from pct.agent.models import AgentResult


class UserProvider:
    """Agent provider for manual human execution via UI.

    Not yet implemented — raises NotImplementedError on all operations.
    """

    async def execute(
        self,
        messages: list[dict[str, str]],
        on_token: Callable[[str], Awaitable[None]] | None = None,
    ) -> AgentResult:
        raise NotImplementedError("UserProvider is not yet implemented")

    async def interrupt(self) -> None:
        raise NotImplementedError("UserProvider is not yet implemented")
