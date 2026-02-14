"""Tests for pct.agent.models — Pydantic model validation."""

from datetime import datetime, timezone

from pct.agent.models import (
    AgentConfig,
    AgentResult,
    AgentType,
    AssembledContext,
    ContextMetadata,
    LLMMessage,
    ProviderType,
    TaskOutcome,
)


class TestAgentResult:
    def test_agent_result_defaults(self):
        """AgentResult with no args has zero tokens, zero duration, None error."""
        result = AgentResult()
        assert result.tokens_input == 0
        assert result.tokens_output == 0
        assert result.duration_seconds == 0.0
        assert result.error is None
        assert result.output == ""
        assert result.messages == []

    def test_agent_result_with_error(self):
        """Error field is preserved when set."""
        result = AgentResult(
            outcome=TaskOutcome.ERROR,
            error="Model crashed",
        )
        assert result.outcome == TaskOutcome.ERROR
        assert result.error == "Model crashed"


class TestAssembledContext:
    def test_assembled_context_full_text(self, sample_context):
        """full_text concatenates all three tiers with double newlines."""
        text = sample_context.full_text
        assert "You are working on project X." in text
        assert "Previous attempt was rejected" in text
        assert "Similar task" in text
        # Tiers are separated by double newlines
        assert "\n\n" in text

    def test_assembled_context_empty_tiers(self):
        """Empty tiers don't produce extra whitespace."""
        ctx = AssembledContext(base="Just the base.", retries="", rag="")
        assert ctx.full_text == "Just the base."

        ctx2 = AssembledContext(base="", retries="", rag="")
        assert ctx2.full_text == ""


class TestLLMMessage:
    def test_llm_message_serialization(self):
        """Round-trip through model_dump / model_validate."""
        now = datetime.now(timezone.utc)
        msg = LLMMessage(role="user", content="Hello", timestamp=now, tokens=5)
        data = msg.model_dump()
        restored = LLMMessage.model_validate(data)
        assert restored.role == "user"
        assert restored.content == "Hello"
        assert restored.tokens == 5
        assert restored.timestamp == now


class TestEnums:
    def test_provider_type_values(self):
        """ProviderType enum values match the spec."""
        assert ProviderType.REMOTE_API.value == "remote"
        assert ProviderType.LOCAL_LLM.value == "local"
        assert ProviderType.USER.value == "user"


class TestAgentConfig:
    def test_agent_config_optional_fields(self):
        """cli_command, lora default to None."""
        config = AgentConfig(
            id="test-agent",
            agent_type=AgentType.LLM,
            provider_type=ProviderType.LOCAL_LLM,
            model="llama-7b",
        )
        assert config.cli_command is None
        assert config.lora is None
        assert config.prompt_template is None
        assert config.context_length is None
