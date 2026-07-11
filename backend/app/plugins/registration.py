from __future__ import annotations

from app.plugins.agent_registry import AgentRegistry
from app.plugins.tool_registry import ToolRegistry
from app.plugins.workflow_registry import WorkflowRegistry


class RegistryValidator:
    def validate(
        self,
        agent_registry: AgentRegistry,
        tool_registry: ToolRegistry,
        workflow_registry: WorkflowRegistry,
    ) -> list[str]:
        errors: list[str] = []

        for wf_def in workflow_registry.list_workflows():
            for agent_id in wf_def.agents:
                if not agent_registry.contains(agent_id):
                    errors.append(
                        f"Workflow '{wf_def.workflow_type}' references unknown agent '{agent_id}'"
                    )

        tool_ids = [t.tool_id for t in tool_registry.list_tools()]
        if len(tool_ids) != len(set(tool_ids)):
            errors.append("Duplicate tool IDs detected")

        agent_ids = [a.agent_id for a in agent_registry.list_agents()]
        if len(agent_ids) != len(set(agent_ids)):
            errors.append("Duplicate agent IDs detected")

        return errors
