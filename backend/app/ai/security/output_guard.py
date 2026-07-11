from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OutputGuardResult:
    passed: bool = True
    blocked: bool = False
    cleaned: str = ""
    reason: str = ""
    issues: list[dict[str, str]] = field(default_factory=list)


class OutputGuard:
    SECRET_PATTERNS = [
        (r"sk-[A-Za-z0-9]{32,}", "OpenAI API key"),
        (r"AIza[0-9A-Za-z\-_]{35}", "Gemini API key"),
        (r"ghp_[A-Za-z0-9]{36}", "GitHub token"),
        (r"xox[bpr]-[A-Za-z0-9\-]{10,}", "Slack token"),
    ]

    async def validate(
        self, agent_output: str, expected_schema: type[Any] | None = None
    ) -> OutputGuardResult:
        issues: list[dict[str, str]] = []
        cleaned = agent_output

        if expected_schema:
            try:
                expected_schema.model_validate_json(agent_output)
            except Exception:
                return OutputGuardResult(
                    passed=False,
                    blocked=True,
                    reason="Output does not match expected schema",
                )

        for pattern, label in self.SECRET_PATTERNS:
            if re.search(pattern, cleaned):
                cleaned = re.sub(pattern, "[REDACTED]", cleaned)
                issues.append({"severity": "critical", "description": f"{label} leaked in output"})

        return OutputGuardResult(
            passed=len(issues) == 0,
            blocked=False,
            cleaned=cleaned,
            issues=issues,
        )
