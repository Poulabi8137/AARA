from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


@dataclass
class GuardResult:
    blocked: bool = False
    cleaned: str = ""
    reason: str = ""
    warnings: list[str] = field(default_factory=list)


class InputGuard:
    MAX_INPUT_LENGTH = 10000
    DANGEROUS_PATTERNS = [
        (r"<\s*script[^>]*>", "HTML script tag"),
        (r"javascript\s*:", "JS protocol"),
        (r"data\s*:\s*text/html", "data URI attack"),
        (r"onload\s*=", "event handler"),
        (r"onerror\s*=", "event handler"),
        (r"(?i)(select|drop|insert|delete|update)\s+.*\s+(from|into|table|set)", "SQL injection"),
    ]

    async def validate(self, raw_input: str) -> GuardResult:
        try:
            decoded = raw_input.encode("utf-8").decode("utf-8")
        except UnicodeError:
            return GuardResult(blocked=True, reason="Invalid encoding")

        if len(decoded) > self.MAX_INPUT_LENGTH:
            decoded = decoded[:self.MAX_INPUT_LENGTH]

        if any(ord(c) < 32 and c not in "\n\r\t" for c in decoded):
            return GuardResult(blocked=True, reason="Control characters detected")

        normalized = unicodedata.normalize("NFKC", decoded)

        warnings: list[str] = []
        for pattern, label in self.DANGEROUS_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                return GuardResult(blocked=True, reason=label)

        return GuardResult(blocked=False, cleaned=normalized, warnings=warnings)

    async def validate_batch(self, inputs: list[str]) -> list[GuardResult]:
        return [await self.validate(inp) for inp in inputs]
