"""Tests for agent pool."""

import asyncio

from pct.agent.models import TaskOutcome
from pct.agent.pool import AgentPool
from pct.agent.providers.user import UserProvider


class TestAgentPool:
    async def test_execute_user_provider(self):
        pool = AgentPool(remote_limit=2, local_limit=1)
        provider = UserProvider()
        result = await pool.execute(provider, [{"role": "user", "content": "Hi"}])
        assert result.outcome == TaskOutcome.in_progress

    async def test_concurrent_execution(self):
        pool = AgentPool(remote_limit=2, local_limit=1)
        provider = UserProvider()

        # Run 3 concurrent tasks — should all succeed
        results = await asyncio.gather(
            pool.execute(provider, [{"role": "user", "content": "1"}]),
            pool.execute(provider, [{"role": "user", "content": "2"}]),
            pool.execute(provider, [{"role": "user", "content": "3"}]),
        )
        assert len(results) == 3
        assert all(r.outcome == TaskOutcome.in_progress for r in results)

    async def test_semaphore_keys(self):
        pool = AgentPool(remote_limit=5, local_limit=2)
        assert "remote" in pool.semaphores
        assert "local" in pool.semaphores
