"""Tests for agent models."""

from pct.agent.models import (
    AgentResult,
    AssembledContext,
    ContextMessage,
    ContextMetadata,
    ContextResource,
    LLMMessage,
    ToolCall,
    ToolResult,
)
from pct.models.enums import InclusionFlag, ResourceKind, TaskOutcome


class TestAgentResult:
    def test_defaults(self):
        r = AgentResult()
        assert r.outcome == TaskOutcome.in_progress
        assert r.output == ""
        assert r.tool_calls == []
        assert r.error is None

    def test_approved(self):
        r = AgentResult(
            outcome=TaskOutcome.approved,
            output="Done!",
            tokens_input=100,
            tokens_output=50,
        )
        assert r.outcome == TaskOutcome.approved


class TestToolCall:
    def test_round_trip(self):
        tc = ToolCall(id="call_1", function_name="read", arguments='{"source": "test.md"}')
        assert tc.function_name == "read"
        assert tc.arguments == '{"source": "test.md"}'
        assert tc.id == "call_1"


class TestToolResult:
    def test_basic(self):
        tr = ToolResult(tool_call_id="call_1", name="read", output="content")
        assert tr.tool_call_id == "call_1"
        assert tr.output == "content"
        assert tr.error is None


class TestLLMMessage:
    def test_basic(self):
        msg = LLMMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp is None
        assert msg.tokens is None


class TestContextResource:
    def test_basic(self):
        r = ContextResource(kind=ResourceKind.rag, label="docs", content="some text")
        assert r.kind == ResourceKind.rag
        assert r.inclusion == InclusionFlag.included

    def test_excluded(self):
        r = ContextResource(
            kind=ResourceKind.cross_ref, content="x", inclusion=InclusionFlag.excluded
        )
        assert r.inclusion == InclusionFlag.excluded


class TestContextMessage:
    def test_user(self):
        m = ContextMessage(role="user", content="Hello")
        assert m.role == "user"
        assert m.inclusion == InclusionFlag.included

    def test_tool_result(self):
        m = ContextMessage(
            role="tool_result",
            content="output",
            tool_call_id="tc1",
            tool_name="read_file",
        )
        assert m.tool_call_id == "tc1"


class TestAssembledContext:
    def test_build_system_prompt_empty(self):
        ctx = AssembledContext()
        assert ctx.build_system_prompt() == ""

    def test_build_system_prompt_prompts_only(self):
        ctx = AssembledContext(
            stage_prompt="Stage instructions",
            agent_prompt="Agent instructions",
        )
        prompt = ctx.build_system_prompt()
        assert "Stage instructions" in prompt
        assert "Agent instructions" in prompt
        # Stage comes before agent
        assert prompt.index("Stage") < prompt.index("Agent")

    def test_build_system_prompt_with_resources(self):
        ctx = AssembledContext(
            agent_prompt="Be helpful",
            resources=[
                ContextResource(kind=ResourceKind.rag, label="docs", content="RAG text"),
                ContextResource(
                    kind=ResourceKind.cross_ref, content="excluded", inclusion=InclusionFlag.excluded
                ),
            ],
        )
        prompt = ctx.build_system_prompt()
        assert "Be helpful" in prompt
        assert "RAG text" in prompt
        assert "excluded" not in prompt

    def test_build_llm_messages_empty(self):
        ctx = AssembledContext()
        msgs = ctx.build_llm_messages()
        assert msgs == []

    def test_build_llm_messages_with_system_and_user(self):
        ctx = AssembledContext(agent_prompt="You are helpful")
        ctx.append_user("Hello")
        msgs = ctx.build_llm_messages()
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[1] == {"role": "user", "content": "Hello"}

    def test_build_llm_messages_tool_result_synthesizes_wrapper(self):
        ctx = AssembledContext()
        ctx.append_user("Do something")
        ctx.append_tool_result("tc1", "read_file", "file content")
        msgs = ctx.build_llm_messages()
        # user, then synthesized assistant tool_call, then tool result
        assert len(msgs) == 3
        assert msgs[0] == {"role": "user", "content": "Do something"}
        assert msgs[1]["role"] == "assistant"
        assert len(msgs[1]["tool_calls"]) == 1
        assert msgs[1]["tool_calls"][0]["id"] == "tc1"
        assert msgs[2]["role"] == "tool"
        assert msgs[2]["content"] == "file content"

    def test_build_llm_messages_excludes_excluded(self):
        ctx = AssembledContext()
        ctx.messages.append(ContextMessage(role="user", content="visible"))
        ctx.messages.append(
            ContextMessage(role="user", content="hidden", inclusion=InclusionFlag.excluded)
        )
        ctx.messages.append(ContextMessage(role="assistant", content="reply"))
        msgs = ctx.build_llm_messages()
        assert len(msgs) == 2
        assert msgs[0]["content"] == "visible"
        assert msgs[1]["content"] == "reply"

    def test_build_llm_messages_consecutive_tool_results(self):
        """Multiple consecutive tool_results should be grouped under one assistant wrapper."""
        ctx = AssembledContext()
        ctx.append_user("Do two things")
        ctx.append_tool_result("tc1", "tool_a", "out1")
        ctx.append_tool_result("tc2", "tool_b", "out2")
        msgs = ctx.build_llm_messages()
        # user, assistant (with 2 tool_calls), tool1, tool2
        assert len(msgs) == 4
        assert msgs[1]["role"] == "assistant"
        assert len(msgs[1]["tool_calls"]) == 2
        assert msgs[2]["tool_call_id"] == "tc1"
        assert msgs[3]["tool_call_id"] == "tc2"

    def test_append_helpers(self):
        ctx = AssembledContext()
        ctx.append_user("hi")
        ctx.append_assistant("hello")
        ctx.append_tool_result("t1", "fn", "out")
        assert len(ctx.messages) == 3
        assert ctx.messages[0].role == "user"
        assert ctx.messages[1].role == "assistant"
        assert ctx.messages[2].role == "tool_result"

    def test_metadata_defaults(self):
        ctx = AssembledContext()
        assert ctx.metadata.total_tokens == 0
        assert ctx.metadata.items_included == 0


class TestImagegenContextRoles:
    def test_build_llm_messages_skips_imagegen_roles(self):
        """build_llm_messages ignores imagegen_positive/negative/result roles."""
        ctx = AssembledContext()
        ctx.append_user("Hello")
        ctx.append_imagegen_positive("a cat in space")
        ctx.append_imagegen_negative("blurry")
        ctx.append_imagegen_result("img001.png")
        ctx.append_assistant("Here are your images")
        msgs = ctx.build_llm_messages()
        assert len(msgs) == 2
        assert msgs[0] == {"role": "user", "content": "Hello"}
        assert msgs[1] == {"role": "assistant", "content": "Here are your images"}

    def test_append_imagegen_helpers(self):
        """append_imagegen_positive/negative/result create correct messages."""
        ctx = AssembledContext()
        ctx.append_imagegen_positive("sunset")
        ctx.append_imagegen_negative("blurry")
        ctx.append_imagegen_result("img1.png\nimg2.png")
        assert len(ctx.messages) == 3
        assert ctx.messages[0].role == "imagegen_positive"
        assert ctx.messages[0].content == "sunset"
        assert ctx.messages[1].role == "imagegen_negative"
        assert ctx.messages[2].role == "imagegen_result"
        assert ctx.messages[2].content == "img1.png\nimg2.png"

    def test_get_imagegen_messages(self):
        """get_imagegen_messages returns only imagegen messages, excludes excluded."""
        ctx = AssembledContext()
        ctx.append_user("Hello")
        ctx.append_imagegen_positive("a dog")
        ctx.append_imagegen_negative("ugly")
        ctx.append_imagegen_result("img.png")
        ctx.append_assistant("Done")
        # Exclude the negative prompt
        ctx.messages[2].inclusion = InclusionFlag.excluded
        result = ctx.get_imagegen_messages()
        assert len(result) == 2
        assert result[0].role == "imagegen_positive"
        assert result[1].role == "imagegen_result"

    def test_imagegen_roles_do_not_corrupt_tool_result_flush(self):
        """Imagegen roles between tool_results don't break the tool flush logic."""
        ctx = AssembledContext()
        ctx.append_user("Do something")
        ctx.append_tool_result("tc1", "read", "content")
        ctx.append_imagegen_positive("a prompt")
        ctx.append_assistant("Done")
        msgs = ctx.build_llm_messages()
        # user, assistant (synthesized tool_call), tool result, assistant
        assert len(msgs) == 4
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"  # synthesized wrapper
        assert msgs[2]["role"] == "tool"
        assert msgs[3]["role"] == "assistant"


class TestContextMetadata:
    def test_defaults(self):
        cm = ContextMetadata()
        assert cm.total_tokens == 0
        assert cm.tier_breakdown == {}
