from __future__ import annotations

from collections import defaultdict, deque

from app.agents.models import AgentStep


class TaskGraph:
    def __init__(self) -> None:
        self._steps: dict[str, AgentStep] = {}
        self._dependencies: dict[str, set[str]] = defaultdict(set)
        self._dependents: dict[str, set[str]] = defaultdict(set)

    def add_step(self, step: AgentStep) -> None:
        self._steps[step.agent_id] = step
        for dep_id in step.depends_on:
            self._dependencies[step.agent_id].add(dep_id)
            self._dependents[dep_id].add(step.agent_id)

    def add_dependency(self, step_id: str, depends_on: str) -> None:
        if step_id not in self._steps:
            raise ValueError(f"Step '{step_id}' not found")
        if depends_on not in self._steps:
            raise ValueError(f"Dependency '{depends_on}' not found")
        self._dependencies[step_id].add(depends_on)
        self._dependents[depends_on].add(step_id)

    def get_topological_order(self) -> list[AgentStep]:
        in_degree: dict[str, int] = {}
        for step_id in self._steps:
            in_degree[step_id] = len(self._dependencies.get(step_id, set()))

        queue: deque[str] = deque()
        for step_id, degree in in_degree.items():
            if degree == 0:
                queue.append(step_id)

        result: list[AgentStep] = []
        while queue:
            current = queue.popleft()
            result.append(self._steps[current])
            for dependent in self._dependents.get(current, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(self._steps):
            return []
        return result

    def get_ready_steps(self, completed: set[str]) -> list[AgentStep]:
        ready: list[AgentStep] = []
        for step_id, step in self._steps.items():
            if step_id in completed:
                continue
            deps = self._dependencies.get(step_id, set())
            if deps and not deps.issubset(completed):
                continue
            ready.append(step)
        return ready

    def get_dependents(self, step_id: str) -> list[str]:
        return list(self._dependents.get(step_id, set()))

    def detect_cycles(self) -> bool:
        return len(self.get_topological_order()) == 0 and len(self._steps) > 0

    def get_levels(self) -> list[list[AgentStep]]:
        in_degree: dict[str, int] = {}
        for step_id in self._steps:
            in_degree[step_id] = len(self._dependencies.get(step_id, set()))

        levels: list[list[AgentStep]] = []
        remaining = set(self._steps.keys())
        while remaining:
            current_level: list[AgentStep] = []
            for step_id in list(remaining):
                if in_degree.get(step_id, 0) == 0:
                    current_level.append(self._steps[step_id])
            if not current_level:
                break
            levels.append(current_level)
            for step in current_level:
                remaining.remove(step.agent_id)
                for dependent in self._dependents.get(step.agent_id, set()):
                    in_degree[dependent] -= 1
        return levels

    def is_complete(self, completed: set[str]) -> bool:
        return len(self._remaining(completed)) == 0

    def get_remaining_steps(self, completed: set[str]) -> list[AgentStep]:
        return self._remaining(completed)

    def all_steps(self) -> list[AgentStep]:
        return list(self._steps.values())

    def _remaining(self, completed: set[str]) -> list[AgentStep]:
        return [s for s in self._steps.values() if s.agent_id not in completed]
