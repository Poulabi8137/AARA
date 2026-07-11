from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.exceptions import RegistryError


@dataclass
class WorkflowDefinition:
    workflow_type: str
    description: str = ""
    agents: list[str] = field(default_factory=list)
    handler: type | None = None


class WorkflowRegistry:
    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowDefinition] = {}

    def register(
        self,
        workflow_type: str,
        description: str = "",
        agents: list[str] | None = None,
    ) -> Any:
        def decorator(cls: type) -> type:
            if workflow_type in self._workflows:
                raise RegistryError(f"Workflow '{workflow_type}' already registered")
            self._workflows[workflow_type] = WorkflowDefinition(
                workflow_type=workflow_type,
                description=description,
                agents=agents or [],
                handler=cls,
            )
            return cls
        return decorator

    def get_plan(self, workflow_type: str) -> WorkflowDefinition:
        wf = self._workflows.get(workflow_type)
        if not wf:
            raise RegistryError(f"Workflow '{workflow_type}' not registered")
        return wf

    def list_workflows(self) -> list[WorkflowDefinition]:
        return list(self._workflows.values())

    def contains(self, workflow_type: str) -> bool:
        return workflow_type in self._workflows

    def unregister(self, workflow_type: str) -> None:
        self._workflows.pop(workflow_type, None)
