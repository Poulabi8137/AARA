from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ai.context.assembler import ContextSection


@dataclass
class TokenBudgetResult:
    allocated: list[ContextSection]
    total_tokens: int = 0
    truncated: bool = False
    remaining: int = 0


class TokenBudget:
    def __init__(self, max_tokens: int = 8000, reserve_output: int = 2048) -> None:
        self.max_tokens = max_tokens
        self.reserve_output = reserve_output
        self._budget = max_tokens - reserve_output

    def allocate(self, sections: list[ContextSection]) -> TokenBudgetResult:
        allocated: list[ContextSection] = []
        total = 0
        truncated = False

        for section in sections:
            tokens = section.token_count or self._estimate(section.content)
            if total + tokens <= self._budget:
                allocated.append(section)
                total += tokens
            else:
                remaining = self._budget - total
                if remaining > 50:
                    section.content = section.content[:remaining * 4]
                    section.token_count = remaining
                    allocated.append(section)
                    total += remaining
                truncated = True
                break

        return TokenBudgetResult(
            allocated=allocated,
            total_tokens=total,
            truncated=truncated,
            remaining=self._budget - total,
        )

    def _estimate(self, text: str) -> int:
        return len(text) // 4

    def can_fit(self, text: str, current_used: int = 0) -> bool:
        tokens = self._estimate(text)
        return current_used + tokens <= self._budget
