"""Tests for context builder."""

from pct.chat.context_builder import expand_template, resolve_task_context


class TestExpandTemplate:
    def test_basic_expansion(self):
        result = expand_template("Hello {{name}}", {"name": "World"})
        assert result == "Hello World"

    def test_missing_variable_left_as_is(self):
        result = expand_template("Hello {{unknown}}", {})
        assert result == "Hello {{unknown}}"

    def test_multiple_variables(self):
        result = expand_template("{{a}} and {{b}}", {"a": "X", "b": "Y"})
        assert result == "X and Y"

    def test_no_variables(self):
        result = expand_template("No variables here", {"a": "X"})
        assert result == "No variables here"


class TestResolveTaskContext:
    def test_non_task_session_returns_empty(self):
        """Non-task session IDs should return empty context."""
        cross_ref, artifact_prompt, stage_prompt = resolve_task_context("planning")
        assert cross_ref == ""
        assert artifact_prompt is None
        assert stage_prompt is None

    def test_invalid_session_id_format(self):
        """Invalid task session format returns empty."""
        cross_ref, artifact_prompt, stage_prompt = resolve_task_context("task-onlyfeature")
        assert cross_ref == ""

    def test_task_prefix_required(self):
        """Session IDs not starting with 'task-' return empty."""
        cross_ref, artifact_prompt, stage_prompt = resolve_task_context("some-other")
        assert cross_ref == ""
        assert artifact_prompt is None
        assert stage_prompt is None
