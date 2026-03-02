"""PERT chart data builder — dependency graph visualization."""

from __future__ import annotations

from collections import defaultdict, deque

from pydantic import BaseModel

from pct.board.wikilinks import parse_wikilink
from pct.models.core import Task


class PertNode(BaseModel):
    model_config = {"extra": "forbid"}

    id: str  # "feature_id#task_id"
    task_id: str
    feature_id: str
    title: str
    stage_id: str
    execution_status: str
    is_blocked: bool
    is_completed: bool


class PertEdge(BaseModel):
    model_config = {"extra": "forbid"}

    source: str  # node id
    target: str  # node id
    edge_type: str  # "blocked_by" or "cross_ref"


class CriticalPath(BaseModel):
    model_config = {"extra": "forbid"}

    task_ids: list[str]
    chain_length: int
    stages_remaining: int


class PertData(BaseModel):
    model_config = {"extra": "forbid"}

    nodes: list[PertNode]
    edges: list[PertEdge]
    critical_path: CriticalPath | None
    total_tasks: int
    completed_count: int
    blocked_count: int


def _task_to_node(task: Task, done_stage: str, blocked_keys: set[str]) -> PertNode:
    """Convert a Task model instance to a PertNode."""
    key = f"{task.feature_id}#{task.id}"
    return PertNode(
        id=key,
        task_id=task.id,
        feature_id=task.feature_id,
        title=task.title,
        stage_id=task.current_stage_id,
        execution_status=task.execution_status.value,
        is_blocked=key in blocked_keys,
        is_completed=task.current_stage_id == done_stage,
    )


def _resolve_dep_key(link: str) -> str | None:
    """Parse a WikiLink and return 'feature_id#task_id' or None."""
    feat_id, task_id = parse_wikilink(link)
    if task_id:
        return f"{feat_id}#{task_id}"
    return None


def build_pert_data(
    tasks: list[Task],
    feature_id: str | None = None,
    done_stage: str = "done",
) -> PertData:
    """Build PERT graph data from tasks.

    Args:
        tasks: list of Task model instances.
        feature_id: if provided, filter to only this feature's tasks.
        done_stage: the stage ID that counts as "completed".

    Returns:
        PertData with nodes, edges, critical path, and summary counts.
    """
    if feature_id is not None:
        tasks = [t for t in tasks if t.feature_id == feature_id]

    # Index tasks by key
    task_by_key: dict[str, Task] = {}
    for t in tasks:
        key = f"{t.feature_id}#{t.id}"
        task_by_key[key] = t

    # Build edges and determine which tasks are blocked
    edges: list[PertEdge] = []
    blocked_keys: set[str] = set()

    for t in tasks:
        target_key = f"{t.feature_id}#{t.id}"

        # blocked_by edges (hard dependency)
        for link in t.blocked_by:
            source_key = _resolve_dep_key(link)
            if source_key and source_key in task_by_key:
                edges.append(PertEdge(
                    source=source_key,
                    target=target_key,
                    edge_type="blocked_by",
                ))
                # Task is blocked if dependency is not completed
                dep_task = task_by_key[source_key]
                if dep_task.current_stage_id != done_stage:
                    blocked_keys.add(target_key)

        # cross_refs edges (soft reference)
        for link in t.cross_refs:
            source_key = _resolve_dep_key(link)
            if source_key and source_key in task_by_key:
                edges.append(PertEdge(
                    source=source_key,
                    target=target_key,
                    edge_type="cross_ref",
                ))

    # Build nodes
    nodes = [_task_to_node(t, done_stage, blocked_keys) for t in tasks]

    # Compute critical path
    critical_path = compute_critical_path(nodes, edges, done_stage)

    # Summary counts
    completed_count = sum(1 for n in nodes if n.is_completed)
    blocked_count = sum(1 for n in nodes if n.is_blocked)

    return PertData(
        nodes=nodes,
        edges=edges,
        critical_path=critical_path,
        total_tasks=len(nodes),
        completed_count=completed_count,
        blocked_count=blocked_count,
    )


def compute_critical_path(
    nodes: list[PertNode],
    edges: list[PertEdge],
    done_stage: str = "done",
) -> CriticalPath | None:
    """Find longest path in DAG using topological sort + DP.

    Only considers blocked_by edges (not cross_refs).
    Returns None if no blocked_by edges exist.
    """
    # Filter to blocked_by edges only
    blocked_edges = [e for e in edges if e.edge_type == "blocked_by"]
    if not blocked_edges:
        return None

    node_ids = {n.id for n in nodes}
    node_map = {n.id: n for n in nodes}

    # Build adjacency list: source -> [target]
    adj: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {nid: 0 for nid in node_ids}

    for e in blocked_edges:
        if e.source in node_ids and e.target in node_ids:
            adj[e.source].append(e.target)
            in_degree[e.target] += 1

    # Kahn's topological sort
    queue: deque[str] = deque()
    for nid in node_ids:
        if in_degree[nid] == 0:
            queue.append(nid)

    topo_order: list[str] = []
    while queue:
        node = queue.popleft()
        topo_order.append(node)
        for neighbor in adj[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # DP: longest path ending at each node
    dist: dict[str, int] = {nid: 1 for nid in node_ids}
    predecessor: dict[str, str | None] = {nid: None for nid in node_ids}

    for node in topo_order:
        for neighbor in adj[node]:
            if dist[node] + 1 > dist[neighbor]:
                dist[neighbor] = dist[node] + 1
                predecessor[neighbor] = node

    # Find the node with the longest path
    if not dist:
        return None

    end_node = max(dist, key=lambda k: dist[k])
    max_length = dist[end_node]

    if max_length <= 1:
        # No meaningful chain (single nodes only)
        return None

    # Reconstruct path
    path: list[str] = []
    current: str | None = end_node
    while current is not None:
        path.append(current)
        current = predecessor[current]
    path.reverse()

    # Count stages remaining (non-completed tasks in path)
    stages_remaining = sum(
        1 for nid in path
        if nid in node_map and not node_map[nid].is_completed
    )

    return CriticalPath(
        task_ids=path,
        chain_length=len(path),
        stages_remaining=stages_remaining,
    )
