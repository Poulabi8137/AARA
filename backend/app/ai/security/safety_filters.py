from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SafetyFilterResult:
    passed: bool = True
    blocked: bool = False
    reason: str = ""
    categories: list[str] = field(default_factory=list)


class SafetyFilter:
    BLOCKED_CONTENT = [
        (
            r"(?i)how\s+to\s+(make|create|build|synthesize)\s+(a\s+)?(weapon|bomb|explosive)",
            "weapon_creation",
        ),
        (r"(?i)instructions?\s+for\s+(self.harm|suicide)", "self_harm"),
        (r"(?i)child\s+(abuse|exploitation|pornography)", "child_exploitation"),
    ]

    BLOCKED_CATEGORIES = ["hate_speech", "harassment", "violence", "illegal_activity",
                           "self_harm", "sexual_content", "weapon_creation"]

    async def check_input(self, text: str) -> SafetyFilterResult:
        triggered = []
        for pattern, category in self.BLOCKED_CONTENT:
            if re.search(pattern, text):
                triggered.append(category)

        if triggered:
            return SafetyFilterResult(
                passed=False,
                blocked=True,
                reason=f"Blocked content detected: {', '.join(triggered)}",
                categories=triggered,
            )

        return SafetyFilterResult(passed=True)

    async def check_output(self, text: str) -> SafetyFilterResult:
        triggered = []
        for pattern, category in self.BLOCKED_CONTENT:
            if re.search(pattern, text):
                triggered.append(category)

        if triggered:
            return SafetyFilterResult(
                passed=False,
                reason=f"Blocked content detected in output: {', '.join(triggered)}",
                categories=triggered,
            )

        return SafetyFilterResult(passed=True)
