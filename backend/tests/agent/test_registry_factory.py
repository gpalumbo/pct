"""Tests for the registry factory — verify all tools are registered."""

from __future__ import annotations

from pathlib import Path

from pct.agent.tools.registry_factory import create_global_registry


EXPECTED_TOOLS = [
    "bash",
    "file_read",
    "file_write",
    "file_edit",
    "web_search",
    "web_fetch",
    "todo_read",
    "todo_create",
    "todo_edit",
    "rag_search",
]


class TestRegistryFactory:
    def test_all_tools_registered(self, tmp_path):
        registry = create_global_registry(
            project_root=tmp_path,
            project_id="test-project",
        )
        definitions = registry.get_definitions()
        names = [d["function"]["name"] for d in definitions]

        assert len(definitions) == 10
        for expected in EXPECTED_TOOLS:
            assert expected in names, f"Missing tool: {expected}"

    def test_definitions_are_valid_schemas(self, tmp_path):
        registry = create_global_registry(
            project_root=tmp_path,
            project_id="test-project",
        )
        for defn in registry.get_definitions():
            assert defn["type"] == "function"
            assert "name" in defn["function"]
            assert "parameters" in defn["function"]
            assert "properties" in defn["function"]["parameters"]
