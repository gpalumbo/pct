"""Tests for agent protocol compliance."""

from pct.agent.protocols import AgentProvider, CompletionBackend
from pct.agent.providers.claude_code import ClaudeCodeProvider
from pct.agent.providers.local_llm import LocalLLMProvider
from pct.agent.providers.user import UserProvider


class FakeBackend:
    """Minimal CompletionBackend implementation for testing."""

    def create_chat_completion(self, messages, stream=False, **kwargs):
        return {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }


class TestProtocolCompliance:
    def test_user_provider_is_agent_provider(self):
        assert isinstance(UserProvider(), AgentProvider)

    def test_local_llm_provider_is_agent_provider(self):
        provider = LocalLLMProvider(backend=FakeBackend())
        assert isinstance(provider, AgentProvider)

    def test_claude_code_provider_is_agent_provider(self):
        assert isinstance(ClaudeCodeProvider(), AgentProvider)


class TestCompletionBackend:
    def test_fake_backend_satisfies_protocol(self):
        assert isinstance(FakeBackend(), CompletionBackend)
