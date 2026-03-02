"""Tests for DAG validation."""

import pytest

from pct.board.dag_validation import CycleError, validate_dag


class TestDAGValidation:
    def test_valid_dag(self):
        tasks = {
            "f1#task-a": [],
            "f1#task-b": ["[[f1#task-a]]"],
            "f1#task-c": ["[[f1#task-b]]"],
        }
        validate_dag(tasks)  # Should not raise

    def test_single_cycle(self):
        tasks = {
            "f1#task-a": ["[[f1#task-b]]"],
            "f1#task-b": ["[[f1#task-a]]"],
        }
        with pytest.raises(CycleError) as exc_info:
            validate_dag(tasks)
        assert len(exc_info.value.cycle_path) >= 2

    def test_multi_node_cycle(self):
        tasks = {
            "f1#a": ["[[f1#b]]"],
            "f1#b": ["[[f1#c]]"],
            "f1#c": ["[[f1#a]]"],
        }
        with pytest.raises(CycleError):
            validate_dag(tasks)

    def test_self_loop(self):
        tasks = {
            "f1#a": ["[[f1#a]]"],
        }
        with pytest.raises(CycleError):
            validate_dag(tasks)

    def test_cross_feature_valid(self):
        tasks = {
            "f1#a": [],
            "f2#b": ["[[f1#a]]"],
        }
        validate_dag(tasks)  # Should not raise

    def test_cross_feature_cycle(self):
        tasks = {
            "f1#a": ["[[f2#b]]"],
            "f2#b": ["[[f1#a]]"],
        }
        with pytest.raises(CycleError):
            validate_dag(tasks)

    def test_empty_graph(self):
        validate_dag({})  # Should not raise

    def test_no_deps(self):
        tasks = {"f1#a": [], "f1#b": [], "f1#c": []}
        validate_dag(tasks)

    def test_cycle_error_message(self):
        tasks = {
            "f1#a": ["[[f1#b]]"],
            "f1#b": ["[[f1#a]]"],
        }
        with pytest.raises(CycleError) as exc_info:
            validate_dag(tasks)
        assert "cycle" in str(exc_info.value).lower()
