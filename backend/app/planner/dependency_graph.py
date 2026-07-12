from __future__ import annotations

from collections import defaultdict, deque

from app.core.logging import get_logger
from app.planner.models import (
    DependencyGraph,
    DependencyType,
    ResearchTask,
    TaskDependency,
)

logger = get_logger("planner.dependency_graph")


class DependencyGraphBuilder:
    def build(
        self,
        tasks: list[ResearchTask],
        custom_dependencies: list[TaskDependency] | None = None,
    ) -> DependencyGraph:
        graph = DependencyGraph()
        task_ids = {t.task_id for t in tasks}
        graph.nodes = set(task_ids)

        edges: dict[str, list[TaskDependency]] = defaultdict(list)

        if custom_dependencies:
            for dep in custom_dependencies:
                if dep.task_id in task_ids and dep.depends_on in task_ids:
                    edges[dep.task_id].append(dep)

        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id in task_ids:
                    edges[task.task_id].append(
                        TaskDependency(
                            task_id=task.task_id,
                            depends_on=dep_id,
                            dependency_type=DependencyType.BLOCKING,
                        )
                    )

        graph.edges = dict(edges)
        graph.circular_dependencies = self._detect_cycles(task_ids, edges)

        if graph.circular_dependencies:
            graph.is_valid = False
            logger.warning(
                "circular dependencies detected",
                extra={"cycles": len(graph.circular_dependencies)},
            )
        else:
            graph.execution_order = self._topological_sort(task_ids, edges)
            graph.parallelizable = self._find_parallelizable(task_ids, edges)

        logger.info(
            "dependency graph built",
            extra={
                "nodes": len(graph.nodes),
                "edges": sum(len(v) for v in edges.values()),
                "levels": len(graph.execution_order),
                "valid": graph.is_valid,
            },
        )
        return graph

    def _detect_cycles(
        self,
        task_ids: set[str],
        edges: dict[str, list[TaskDependency]],
    ) -> list[list[str]]:
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {tid: WHITE for tid in task_ids}
        cycles: list[list[str]] = []
        path: list[str] = []

        def dfs(node: str) -> None:
            color[node] = GRAY
            path.append(node)
            for dep in edges.get(node, []):
                neighbor = dep.depends_on
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    cycle_start = path.index(neighbor)
                    cycles.append(list(path[cycle_start:]))
                elif color[neighbor] == WHITE:
                    dfs(neighbor)
            path.pop()
            color[node] = BLACK

        for tid in task_ids:
            if color[tid] == WHITE:
                dfs(tid)

        return cycles

    def _topological_sort(
        self,
        task_ids: set[str],
        edges: dict[str, list[TaskDependency]],
    ) -> list[list[str]]:
        in_degree: dict[str, int] = {tid: 0 for tid in task_ids}
        rev_edges: dict[str, list[str]] = defaultdict(list)

        for tid, deps in edges.items():
            for dep in deps:
                in_degree[tid] = in_degree.get(tid, 0) + 1
                rev_edges[dep.depends_on].append(tid)

        queue: deque[str] = deque()
        for tid, degree in in_degree.items():
            if degree == 0:
                queue.append(tid)

        levels: list[list[str]] = []
        while queue:
            level: list[str] = []
            for _ in range(len(queue)):
                node = queue.popleft()
                level.append(node)
                for neighbor in rev_edges.get(node, []):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
            levels.append(level)

        return levels

    def _find_parallelizable(
        self,
        task_ids: set[str],
        edges: dict[str, list[TaskDependency]],
    ) -> list[list[str]]:
        dep_set: dict[str, set[str]] = {}
        for tid in task_ids:
            dep_set[tid] = {d.depends_on for d in edges.get(tid, [])}

        groups: list[list[str]] = []
        assigned: set[str] = set()

        for tid in task_ids:
            if tid in assigned:
                continue
            group = [tid]
            assigned.add(tid)
            for other in task_ids:
                if other in assigned:
                    continue
                self_deps = dep_set.get(other, set())
                other_deps = dep_set.get(tid, set())
                if not self_deps.intersection({tid}) and not other_deps.intersection(
                    {other}
                ):
                    group.append(other)
                    assigned.add(other)
            groups.append(group)

        return groups
