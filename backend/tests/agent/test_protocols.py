"""Tests for agent protocol compliance."""

from pct.agent.protocols import AgentProvider
from pct.agent.providers.claude_code import ClaudeCodeProvider
from pct.agent.providers.local_llm import LocalLLMProvider
from pct.agent.providers.user import UserProvider


class TestProtocolCompliance:
    def test_user_provider_is_agent_provider(self):
        assert isinstance(UserProvider(), AgentProvider)

    def test_local_llm_provider_is_agent_provider(self):
        # LocalLLMProvider satisfies the protocol even without model loaded
        provider = LocalLLMProvider.__new__(LocalLLMProvider)
        provider.model_path = "test"
        provider.context_length = 4096
        provider.temperature = 0.7
        provider._llm = None
        provider._interrupted = False
        assert isinstance(provider, AgentProvider)

    def test_claude_code_provider_is_agent_provider(self):
        assert isinstance(ClaudeCodeProvider(), AgentProvider)
