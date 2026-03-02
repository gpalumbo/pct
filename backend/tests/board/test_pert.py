"""Tests for PERT chart data builder."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pct.board.pert import (
    CriticalPath,
    PertData,
    PertEdge,
    PertNode,
    build_pert_data,
    compute_critical_path,
)
from pct.models.core import Task
from pct.models.enums import ExecutionStatus


def _make_task(
    task_id: str,
    feature_id: str = "f1",
    title: str | None = None,
    stage_id: str = "implement",
    execution_status: ExecutionStatus = ExecutionStatus.idle,
    blocked_by: list[str] | None = None,
    cross_refs: list[str] | None = None,
) -> Task:
    """Helper to create a Task with sensible defaults."""
    return Task(
        id=task_id,
        feature_id=feature_id,
        title=title or task_id,
        current_stage_id=stage_id,
        execution_status=execution_status,
        blocked_by=blocked_by or [],
        cross_refs=cross_refs or [],
    )


class TestBuildPertDataEmpty:
    def test_build_pert_data_empty(self):
        result = build_pert_data([], done_stage="done")
        assert result.total_tasks == 0
        assert result.completed_count == 0
        assert result.blocked_count == 0
        assert result.nodes == []
        assert result.edges == []
        assert result.critical_path is None


class TestBuildPertDataSingleTask:
    def test_build_pert_data_single_task(self):
        tasks = [_make_task("t1")]
        result = build_pert_data(tasks, done_stage="done")
        assert result.total_tasks == 1
        assert len(result.nodes) == 1
        assert result.nodes[0].id == "f1#t1"
        assert result.nodes[0].task_id == "t1"
        assert result.nodes[0].feature_id == "f1"
        assert result.edges == []
        assert result.critical_path is None


class TestBuildPertDataWithDependencies:
    def test_build_pert_data_with_dependencies(self):
        tasks = [
            _make_task("a"),
            _make_task("b", blocked_by=["[[f1#a]]"]),
            _make_task("c", blocked_by=["[[f1#b]]"]),
        ]
        result = build_pert_data(tasks, done_stage="done")
        assert result.total_tasks == 3
        blocked_edges = [e for e in result.edges if e.edge_type == "blocked_by"]
        assert len(blocked_edges) == 2
        assert any(e.source == "f1#a" and e.target == "f1#b" for e in blocked_edges)
        assert any(e.source == "f1#b" and e.target == "f1#c" for e in blocked_edges)

    def test_cross_feature_dependencies(self):
        tasks = [
            _make_task("a", feature_id="f1"),
            _make_task("b", feature_id="f2", blocked_by=["[[f1#a]]"]),
        ]
        result = build_pert_data(tasks, done_stage="done")
        assert len(result.edges) == 1
        assert result.edges[0].source == "f1#a"
        assert result.edges[0].target == "f2#b"


class TestBuildPertDataWithCrossRefs:
    def test_build_pert_data_with_cross_refs(self):
        tasks = [
            _make_task("a"),
            _make_task("b", cross_refs=["[[f1#a]]"]),
        ]
        result = build_pert_data(tasks, done_stage="done")
        assert len(result.edges) == 1
        assert result.edges[0].edge_type == "cross_ref"
        assert result.edges[0].source == "f1#a"
        assert result.edges[0].target == "f1#b"

    def test_cross_refs_dont_block(self):
        """Cross-refs should not mark tasks as blocked."""
        tasks = [
            _make_task("a"),
            _make_task("b", cross_refs=["[[f1#a]]"]),
        ]
        result = build_pert_data(tasks, done_stage="done")
        b_node = next(n for n in result.nodes if n.task_id == "b")
        assert b_node.is_blocked is False


class TestCriticalPathLinearChain:
    def test_critical_path_linear_chain(self):
        tasks = [
            _make_task("a"),
            _make_task("b", blocked_by=["[[f1#a]]"]),
            _make_task("c", blocked_by=["[[f1#b]]"]),
        ]
        result = build_pert_data(tasks, done_stage="done")
        assert result.critical_path is not None
        assert result.critical_path.task_ids == ["f1#a", "f1#b", "f1#c"]
        assert result.critical_path.chain_length == 3


class TestCriticalPathDiamond:
    def test_critical_path_diamond(self):
        """Diamond: A->B, A->C, B->D, C->D. Longest is length 3."""
        tasks = [
            _make_task("a"),
            _make_task("b", blocked_by=["[[f1#a]]"]),
            _make_task("c", blocked_by=["[[f1#a]]"]),
            _make_task("d", blocked_by=["[[f1#b]]", "[[f1#c]]"]),
        ]
        result = build_pert_data(tasks, done_stage="done")
        assert result.critical_path is not None
        assert result.critical_path.chain_length == 3
        assert result.critical_path.task_ids[0] == "f1#a"
        assert result.critical_path.task_ids[-1] == "f1#d"


class TestCriticalPathNoEdges:
    def test_critical_path_no_edges(self):
        tasks = [_make_task("a"), _make_task("b"), _make_task("c")]
        result = build_pert_data(tasks, done_stage="done")
        assert result.critical_path is None

    def test_critical_path_cross_refs_only(self):
        """Cross-refs are not considered for critical path."""
        tasks = [
            _make_task("a"),
            _make_task("b", cross_refs=["[[f1#a]]"]),
        ]
        result = build_pert_data(tasks, done_stage="done")
        assert result.critical_path is None


class TestCriticalPathCompletedTasks:
    def test_critical_path_completed_tasks(self):
        """Completed tasks still in path but stages_remaining excludes them."""
        tasks = [
            _make_task("a", stage_id="done"),
            _make_task("b", blocked_by=["[[f1#a]]"]),
            _make_task("c", blocked_by=["[[f1#b]]"]),
        ]
        result = build_pert_data(tasks, done_stage="done")
        assert result.critical_path is not None
        assert result.critical_path.chain_length == 3
        assert result.critical_path.stages_remaining == 2

    def test_all_completed(self):
        tasks = [
            _make_task("a", stage_id="done"),
            _make_task("b", stage_id="done", blocked_by=["[[f1#a]]"]),
        ]
        result = build_pert_data(tasks, done_stage="done")
        assert result.critical_path is not None
        assert result.critical_path.stages_remaining == 0


class TestPertNodeStatus:
    def test_is_blocked_when_dependency_not_done(self):
        tasks = [
            _make_task("a", stage_id="implement"),
            _make_task("b", blocked_by=["[[f1#a]]"]),
        ]
        result = build_pert_data(tasks, done_stage="done")
        b_node = next(n for n in result.nodes if n.task_id == "b")
        assert b_node.is_blocked is True

    def test_not_blocked_when_dependency_done(self):
        tasks = [
            _make_task("a", stage_id="done"),
            _make_task("b", blocked_by=["[[f1#a]]"]),
        ]
        result = build_pert_data(tasks, done_stage="done")
        b_node = next(n for n in result.nodes if n.task_id == "b")
        assert b_node.is_blocked is False

    def test_is_completed(self):
        tasks = [_make_task("a", stage_id="done")]
        result = build_pert_data(tasks, done_stage="done")
        assert result.nodes[0].is_completed is True

    def test_not_completed(self):
        tasks = [_make_task("a", stage_id="implement")]
        result = build_pert_data(tasks, done_stage="done")
        assert result.nodes[0].is_completed is False

    def test_execution_status_preserved(self):
        tasks = [_make_task("a", execution_status=ExecutionStatus.running)]
        result = build_pert_data(tasks, done_stage="done")
        assert result.nodes[0].execution_status == "running"


class TestPertDataCounts:
    def test_counts(self):
        tasks = [
            _make_task("a", stage_id="done"),
            _make_task("b", stage_id="implement"),
            _make_task("c", blocked_by=["[[f1#b]]"]),
        ]
        result = build_pert_data(tasks, done_stage="done")
        assert result.total_tasks == 3
        assert result.completed_count == 1
        assert result.blocked_count == 1


class TestFeatureFiltering:
    def test_filter_by_feature(self):
        tasks = [
            _make_task("a", feature_id="f1"),
            _make_task("b", feature_id="f2"),
        ]
        result = build_pert_data(tasks, feature_id="f1", done_stage="done")
        assert result.total_tasks == 1
        assert result.nodes[0].feature_id == "f1"

    def test_no_filter_returns_all(self):
        tasks = [
            _make_task("a", feature_id="f1"),
            _make_task("b", feature_id="f2"),
        ]
        result = build_pert_data(tasks, done_stage="done")
        assert result.total_tasks == 2


class TestPertModels:
    def test_pert_node_forbids_extra(self):
        with pytest.raises(ValidationError):
            PertNode(
                id="f1#t1",
                task_id="t1",
                feature_id="f1",
                title="T1",
                stage_id="done",
                execution_status="idle",
                is_blocked=False,
                is_completed=False,
                extra_field="bad",
            )

    def test_pert_edge_forbids_extra(self):
        with pytest.raises(ValidationError):
            PertEdge(source="a", target="b", edge_type="blocked_by", extra="bad")

    def test_critical_path_forbids_extra(self):
        with pytest.raises(ValidationError):
            CriticalPath(task_ids=[], chain_length=0, stages_remaining=0, extra="bad")

    def test_pert_data_forbids_extra(self):
        with pytest.raises(ValidationError):
            PertData(
                nodes=[],
                edges=[],
                critical_path=None,
                total_tasks=0,
                completed_count=0,
                blocked_count=0,
                extra="bad",
            )


class TestComputeCriticalPathDirect:
    def test_returns_none_for_empty(self):
        result = compute_critical_path([], [])
        assert result is None

    def test_returns_none_for_cross_ref_only(self):
        nodes = [
            PertNode(id="f1#a", task_id="a", feature_id="f1", title="A",
                     stage_id="impl", execution_status="idle",
                     is_blocked=False, is_completed=False),
            PertNode(id="f1#b", task_id="b", feature_id="f1", title="B",
                     stage_id="impl", execution_status="idle",
                     is_blocked=False, is_completed=False),
        ]
        edges = [PertEdge(source="f1#a", target="f1#b", edge_type="cross_ref")]
        result = compute_critical_path(nodes, edges)
        assert result is None


class TestEdgeToUnknownTask:
    def test_dependency_to_unknown_task_ignored(self):
        """If blocked_by references a task not in the list, it should be ignored."""
        tasks = [
            _make_task("a", blocked_by=["[[f1#unknown]]"]),
        ]
        result = build_pert_data(tasks, done_stage="done")
        assert result.total_tasks == 1
        assert result.edges == []
        assert result.nodes[0].is_blocked is False
