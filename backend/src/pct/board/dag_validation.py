"""DAG validation for blocked_by dependency graph — tech_spec §3.6."""

from pct.board.wikilinks import parse_wikilink


class CycleError(Exception):
    """Raised when a cycle is detected in the dependency graph."""

    def __init__(self, cycle_path: list[str]):
        self.cycle_path = cycle_path
        super().__init__(f"Dependency cycle detected: {' → '.join(cycle_path)}")


def validate_dag(
    tasks: dict[str, list[str]],
) -> None:
    """Validate that blocked_by graph is acyclic.

    Args:
        tasks: mapping of task_key → list of blocked_by WikiLink strings.
               task_key format: 'feature_id#task_id'

    Raises:
        CycleError with the cycle path if a cycle is detected.
    """
    # Build adjacency: task_key → set of dependency task_keys
    adj: dict[str, set[str]] = {}
    for task_key, deps in tasks.items():
        adj.setdefault(task_key, set())
        for dep in deps:
            feat_id, task_id = parse_wikilink(dep)
            if task_id:
                dep_key = f"{feat_id}#{task_id}"
                adj.setdefault(dep_key, set())
                adj[task_key].add(dep_key)

    # 3-color DFS: WHITE=0, GRAY=1, BLACK=2
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {node: WHITE for node in adj}
    parent: dict[str, str | None] = {node: None for node in adj}

    def dfs(node: str) -> list[str] | None:
        color[node] = GRAY
        for neighbor in adj.get(node, set()):
            if color.get(neighbor, WHITE) == GRAY:
                # Found cycle — reconstruct path
                path = [neighbor, node]
                current = node
                while parent.get(current) is not None and parent[current] != neighbor:
                    current = parent[current]
                    path.append(current)
                path.reverse()
                return path
            if color.get(neighbor, WHITE) == WHITE:
                parent[neighbor] = node
                result = dfs(neighbor)
                if result is not None:
                    return result
        color[node] = BLACK
        return None

    for node in list(adj.keys()):
        if color.get(node, WHITE) == WHITE:
            cycle = dfs(node)
            if cycle is not None:
                raise CycleError(cycle)
