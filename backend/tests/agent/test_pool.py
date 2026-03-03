"""Tests for agent pool."""

from pct.agent.models import AgentJob, AgentResult, AssembledContext
from pct.agent.pool import AgentPool
from pct.models.enums import ProviderType, TaskOutcome


class FakeProvider:
    """Fake provider that returns a canned result."""

    def __init__(self, outcome=TaskOutcome.approved):
        self._outcome = outcome

    async def execute(self, messages, on_token=None, tools=None):
        return AgentResult(outcome=self._outcome, output="fake")

    async def interrupt(self):
        pass


class TestAgentPool:
    async def test_submit_and_await(self):
        provider = FakeProvider()
        pool = AgentPool(
            providers={ProviderType.remote_api: provider},
            remote_limit=2,
            local_limit=1,
        )
        job = AgentJob(
            task_id="t1",
            feature_id="f1",
            context=AssembledContext(base="Hello"),
            agent_type=ProviderType.remote_api,
            stage="refine-spec",
        )
        future = pool.submit(job)
        result = await future
        assert result.outcome == TaskOutcome.approved

    async def test_shutdown(self):
        provider = FakeProvider()
        pool = AgentPool(
            providers={ProviderType.remote_api: provider},
            remote_limit=2,
            local_limit=1,
        )
        await pool.shutdown()
        assert pool._tasks == []
