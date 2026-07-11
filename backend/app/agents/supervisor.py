from __future__ import annotations

import asyncio
import time
from typing import Any

from app.agents.base import BaseAgent
from app.agents.models import (
    AgentContext,
    AgentOutput,
    AgentPhase,
    AgentStatus,
    AgentStep,
    WorkflowResult,
)
from app.agents.registry import AgentRegistry
from app.ai.evaluation.engine import EvaluationEngine, EvaluationReport
from app.ai.security.output_guard import OutputGuard
from app.ai.security.safety_filters import SafetyFilter
from app.core.exceptions import AARAError
from app.streaming.dispatcher_adapter import StreamEventDispatcher


class RetryableError(Exception):
    pass


class SupervisorAgent(BaseAgent):
    agent_id: str = "supervisor"
    agent_name: str = "Supervisor"
    version: str = "1.0"
    max_retries: int = 0
    timeout_seconds: int = 300

    PHASES = ["Research", "Analysis", "Idea Gen", "Writing", "Review"]
    ALL_PHASES = ["Planner", *PHASES]
    CHECKPOINT_PHASES = {"Research", "Analysis", "Idea Gen", "Writing"}
    # EvaluationEngine's own metric-registry vocabulary (app/ai/evaluation/engine.py)
    # doesn't match phase_name.lower().replace(" ", "_") for these two phases.
    EVAL_PHASE_MAP = {"idea_gen": "ideas", "writing": "draft"}

    def __init__(
        self,
        agent_registry: AgentRegistry | None = None,
        workflow_engine: Any | None = None,
        state_manager: Any | None = None,
        event_dispatcher: StreamEventDispatcher | None = None,
        evaluation_engine: EvaluationEngine | None = None,
    ) -> None:
        super().__init__()
        self._agent_registry = agent_registry or AgentRegistry()
        self._workflow_engine = workflow_engine
        self._state_manager = state_manager
        self._event_dispatcher = event_dispatcher
        self._evaluation_engine = evaluation_engine
        self._evaluation_reports: list[EvaluationReport] = []
        self._workflow_id: str = ""
        self._trace_id: str = ""
        self._phase_outputs: dict[str, AgentOutput] = {}
        self._checkpoint_ids: dict[str, str] = {}
        self._start_time: float = 0.0

    @property
    def workflow_id(self) -> str:
        return self._workflow_id

    @property
    def trace_id(self) -> str:
        return self._trace_id

    @property
    def state(self) -> dict[str, Any]:
        return self._state.intermediate_outputs

    @property
    def current_phase(self) -> str:
        return self._state.current_phase.value if self._state.current_phase else ""

    async def execute(self, context: AgentContext) -> AgentOutput:
        self._workflow_id = context.workflow_id
        self._trace_id = context.trace_id
        self._start_time = time.monotonic()
        query = context.input.get("query", "")
        workspace_id = context.input.get("workspace_id", "")

        await self.update_state(
            status=AgentStatus.RECEIVING_CONTEXT,
            current_phase=AgentPhase.PLANNING,
        )

        if self._event_dispatcher:
            await self._event_dispatcher.dispatch_workflow_started(
                self._workflow_id, "research",
                metadata={"query": query},
            )
            await self._event_dispatcher.dispatch_agent_started("Planner", self._workflow_id)

        planner_context = AgentContext(
            workflow_id=self._workflow_id,
            step_id="planner",
            trace_id=self._trace_id,
            input={"query": query, "workspace_id": workspace_id},
        )
        planner = self._agent_registry.get("planner")
        planner_output = await planner.execute(planner_context)
        plan = planner_output.output.get("plan")

        if self._event_dispatcher:
            await self._event_dispatcher.dispatch_agent_completed(
                "Planner", self._workflow_id,
                {"has_plan": plan is not None, "summary": planner_output.summary},
            )

        completed_steps: list[str] = []
        failed_steps: list[str] = []
        checkpoint_decisions: list[dict[str, Any]] = []

        for phase_name in self.PHASES:
            phase_input = {
                "query": query,
                "workspace_id": workspace_id,
                **{k: v for k, v in context.input.items() if k not in ("query", "workspace_id")},
            }
            if self._event_dispatcher:
                await self._event_dispatcher.dispatch_agent_started(phase_name, self._workflow_id)
            phase_output = await self.run_phase(phase_name, phase_input)
            self._phase_outputs[phase_name] = phase_output
            completed_steps.append(phase_name)
            if self._event_dispatcher:
                # Carries the phase's actual output (not just a status ping) so
                # SSE consumers (e.g. the Research Workspace's progressive output
                # panel) can render real content as each phase finishes, without
                # a second round-trip.
                await self._event_dispatcher.dispatch_agent_completed(
                    phase_name, self._workflow_id,
                    {"summary": phase_output.summary, "result": phase_output.output},
                )

            if self._evaluation_engine:
                phase_key = phase_name.lower().replace(" ", "_")
                eval_report = await self._evaluation_engine.evaluate(
                    phase=self.EVAL_PHASE_MAP.get(phase_key, phase_key),
                    artifact=phase_output,
                    papers=phase_output.output.get("papers", []),
                    citations=phase_output.output.get("citations", []),
                    sections=phase_output.output.get("sections", []),
                )
                eval_report.workflow_id = self._workflow_id
                eval_report.artifact_id = f"{self._workflow_id}_{phase_name}"
                self._evaluation_reports.append(eval_report)

                if self._event_dispatcher:
                    for metric in eval_report.metrics:
                        await self._event_dispatcher.dispatch_evaluation_result(
                            self._workflow_id, metric.name, metric.score, metric.details,
                        )

            if phase_name in self.CHECKPOINT_PHASES:
                checkpoint_id = await self.handle_checkpoint(phase_name, phase_output)
                checkpoint_decisions.append({
                    "phase": phase_name,
                    "checkpoint_id": checkpoint_id,
                    "status": "approved",
                })

        if self._event_dispatcher:
            await self._event_dispatcher.dispatch_workflow_completed(
                self._workflow_id,
                {"plan_steps": len(plan.steps) if plan and hasattr(plan, "steps") else 0},
            )

        workflow_result = await self.aggregate_results()
        await self.screen_output(workflow_result)
        if plan:
            workflow_result.execution_plan = plan

        workflow_result.steps_completed = completed_steps
        workflow_result.steps_failed = failed_steps
        workflow_result.checkpoint_decisions = checkpoint_decisions

        if self._evaluation_reports:
            from app.ai.evaluation.aggregation import QualityAggregator

            aggregator = QualityAggregator()
            all_metrics = [m for r in self._evaluation_reports for m in r.metrics]
            aggregated = aggregator.aggregate(all_metrics)
            workflow_result.metadata["evaluation"] = {
                "reports": [
                    {"phase": r.phase, "overall_score": r.overall_score, "passed": r.passed}
                    for r in self._evaluation_reports
                ],
                "aggregated": aggregated.model_dump() if hasattr(aggregated, "model_dump") else {},  # noqa: E501
            }

        duration_ms = int((time.monotonic() - self._start_time) * 1000)
        workflow_result.duration_ms = duration_ms

        return AgentOutput(
            agent_id=self.agent_id,
            workflow_id=self._workflow_id,
            output={"workflow_result": workflow_result.model_dump() if hasattr(workflow_result, "model_dump") else {}},  # noqa: E501
            summary=f"Workflow completed {len(completed_steps)} phases, {len(failed_steps)} failed",
            duration_ms=duration_ms,
        )

    async def execute_step(self, step: AgentStep) -> AgentOutput:
        agent = self._agent_registry.get(step.agent_id)
        max_attempts = step.max_retries + 1
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                context = AgentContext(
                    workflow_id=self._workflow_id,
                    step_id=step.agent_id,
                    trace_id=self._trace_id,
                    input=step.input,
                )
                output = await agent.execute(context)

                valid = await self.validate_output(output)
                if not valid:
                    raise RetryableError(f"Output validation failed for {step.agent_id}")

                if self._state_manager:
                    await self._state_manager.persist(self._workflow_id, step.agent_id, output)

                if self._event_dispatcher:
                    await self._event_dispatcher.dispatch_agent_completed(
                        step.agent_id, self._workflow_id, output.output,
                    )

                return output

            except RetryableError as e:
                last_error = e
                if attempt < max_attempts:
                    delay = 2 ** attempt
                    if self._event_dispatcher:
                        await self._event_dispatcher.dispatch_agent_started(step.agent_id, self._workflow_id)
                    await asyncio.sleep(delay)
                else:
                    raise

            except AARAError:
                raise

            except Exception as e:
                last_error = e
                raise RetryableError(str(e)) from e

        raise last_error or RetryableError(f"Step {step.agent_id} failed after {max_attempts} attempts")  # noqa: E501

    async def run_phase(self, phase_name: str, input_data: dict) -> AgentOutput:
        phase_id = phase_name.lower().replace(" ", "_")
        context = AgentContext(
            workflow_id=self._workflow_id,
            step_id=phase_id,
            trace_id=self._trace_id,
            input=input_data,
        )
        agent = self._agent_registry.get(phase_id)
        return await agent.execute(context)

    async def handle_checkpoint(self, phase: str, output: AgentOutput) -> str:
        import uuid

        checkpoint_id = str(uuid.uuid4())
        self._checkpoint_ids[phase] = checkpoint_id

        if self._event_dispatcher:
            await self._event_dispatcher.dispatch_checkpoint_created(
                self._workflow_id, phase, checkpoint_id, output.summary,
            )

        return checkpoint_id

    async def aggregate_results(self) -> WorkflowResult:
        result = WorkflowResult(
            workflow_id=self._workflow_id,
            status="completed",
            query="",
        )

        for phase_name in self.PHASES:
            phase_output = self._phase_outputs.get(phase_name)
            if not phase_output:
                continue

            if phase_name == "Research" and not result.papers:
                result.papers = phase_output.output.get("papers") or phase_output.output.get("results")  # noqa: E501
            elif phase_name == "Analysis" and not result.analysis:
                result.analysis = phase_output.output.get("analysis")
            elif phase_name == "Idea Gen" and not result.ideas:
                result.ideas = phase_output.output.get("ideas")
            elif phase_name == "Writing" and not result.draft:
                result.draft = phase_output.output.get("draft")
            elif phase_name == "Review" and not result.review:
                result.review = phase_output.output.get("review")

        return result

    async def screen_output(self, result: WorkflowResult) -> None:
        """Run the final draft through the output guard/safety filter before it
        reaches the user, redacting any leaked secrets or blocked content."""
        draft = result.draft
        if not isinstance(draft, dict):
            return
        sections = draft.get("sections")
        if not isinstance(sections, list):
            return

        output_guard = OutputGuard()
        safety_filter = SafetyFilter()
        findings: list[dict[str, Any]] = []

        for section in sections:
            content = section.get("content", "")
            if not content:
                continue

            guard_result = await output_guard.validate(content)
            if guard_result.issues:
                section["content"] = guard_result.cleaned
                findings.extend(guard_result.issues)

            safety_result = await safety_filter.check_output(section.get("content", ""))
            if not safety_result.passed:
                section["content"] = "[Content removed: policy violation]"
                findings.append({"severity": "critical", "description": safety_result.reason})

        if findings:
            result.metadata["security_findings"] = findings

    async def validate_output(self, output: AgentOutput) -> bool:
        workflow_result_data = output.output.get("workflow_result")
        if workflow_result_data is not None:
            try:
                WorkflowResult(**workflow_result_data)
                return True
            except (ValueError, TypeError):
                return False
        return True

    async def handle_error(self, error: Exception, context: AgentContext) -> AgentOutput:
        await self.update_state(
            status=AgentStatus.ERROR,
            current_phase=AgentPhase.IDLE,
        )

        if self._event_dispatcher:
            await self._event_dispatcher.dispatch_error(
                self.agent_id, str(error),
                context={"workflow_id": self._workflow_id},
            )

        return AgentOutput(
            agent_id=self.agent_id,
            workflow_id=context.workflow_id,
            output={"error": str(error)},
            summary=f"Supervisor workflow failed: {error}",
            duration_ms=int((time.monotonic() - self._start_time) * 1000) if self._start_time else 0,  # noqa: E501
        )
