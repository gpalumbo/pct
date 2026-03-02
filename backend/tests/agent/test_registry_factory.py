"""Tests for tool registry factory."""

from pathlib import Path

from pct.agent.tools.registry_factory import create_global_registry, reset_global_registry


class TestRegistryFactory:
    def setup_method(self):
        reset_global_registry()

    def test_creates_registry_with_all_tools(self, tmp_path: Path):
        registry = create_global_registry(tmp_path)
        assert "read" in registry.tool_names
        assert "file" in registry.tool_names
        assert "search" in registry.tool_names
        assert "todo" in registry.tool_names
        assert "bash" in registry.tool_names

    def test_singleton(self, tmp_path: Path):
        r1 = create_global_registry(tmp_path)
        r2 = create_global_registry(tmp_path)
        assert r1 is r2

    def test_reset(self, tmp_path: Path):
        r1 = create_global_registry(tmp_path)
        reset_global_registry()
        r2 = create_global_registry(tmp_path)
        assert r1 is not r2
