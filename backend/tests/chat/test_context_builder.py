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
    def test_none_feature_id_returns_empty(self):
        """None feature_id should return empty context."""
        cross_ref, artifact_prompt, stage_prompt = resolve_task_context(None, "task1")
        assert cross_ref == ""
        assert artifact_prompt is None
        assert stage_prompt is None

    def test_none_task_id_returns_empty(self):
        """None task_id should return empty context."""
        cross_ref, artifact_prompt, stage_prompt = resolve_task_context("feature1", None)
        assert cross_ref == ""
        assert artifact_prompt is None
        assert stage_prompt is None

    def test_both_none_returns_empty(self):
        """Both None should return empty context."""
        cross_ref, artifact_prompt, stage_prompt = resolve_task_context(None, None)
        assert cross_ref == ""
        assert artifact_prompt is None
        assert stage_prompt is None

    def test_empty_strings_return_empty(self):
        """Empty strings should return empty context."""
        cross_ref, artifact_prompt, stage_prompt = resolve_task_context("", "")
        assert cross_ref == ""
        assert artifact_prompt is None
        assert stage_prompt is None
