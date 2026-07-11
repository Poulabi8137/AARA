from __future__ import annotations

from app.agents.models import WorkflowResult
from app.agents.supervisor import SupervisorAgent


class TestScreenOutput:
    async def test_redacts_leaked_secret_in_draft(self):
        supervisor = SupervisorAgent()
        result = WorkflowResult(
            workflow_id="wf-1",
            status="completed",
            draft={
                "sections": [
                    {"heading": "Method", "content": "Use key sk-" + "a" * 40 + " to call the API."},
                ],
            },
        )

        await supervisor.screen_output(result)

        assert "sk-" not in result.draft["sections"][0]["content"]
        assert "[REDACTED]" in result.draft["sections"][0]["content"]
        assert result.metadata["security_findings"]

    async def test_blocks_unsafe_content_in_draft(self):
        supervisor = SupervisorAgent()
        result = WorkflowResult(
            workflow_id="wf-1",
            status="completed",
            draft={
                "sections": [
                    {"heading": "Method", "content": "How to make a bomb using household items."},
                ],
            },
        )

        await supervisor.screen_output(result)

        assert result.draft["sections"][0]["content"] == "[Content removed: policy violation]"
        assert result.metadata["security_findings"]

    async def test_leaves_clean_draft_untouched(self):
        supervisor = SupervisorAgent()
        result = WorkflowResult(
            workflow_id="wf-1",
            status="completed",
            draft={
                "sections": [
                    {"heading": "Introduction", "content": "This paper explores research gaps."},
                ],
            },
        )

        await supervisor.screen_output(result)

        assert result.draft["sections"][0]["content"] == "This paper explores research gaps."
        assert "security_findings" not in result.metadata

    async def test_noop_when_draft_missing(self):
        supervisor = SupervisorAgent()
        result = WorkflowResult(workflow_id="wf-1", status="completed", draft=None)

        await supervisor.screen_output(result)

        assert "security_findings" not in result.metadata
