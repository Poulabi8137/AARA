from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any


@dataclass
class CostRecord:
    workflow_id: str | None = None
    agent_id: str | None = None
    provider_id: str | None = None
    model: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost: Decimal = Decimal("0.00")
    duration_ms: float = 0.0
    timestamp: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class CostMetricsCollector:
    def __init__(self) -> None:
        self._records: list[CostRecord] = []
        self._budgets: dict[str, Decimal] = {}

    def record(self, record: CostRecord) -> None:
        self._records.append(record)

    def record_inference(
        self,
        provider_id: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost: Decimal,
        workflow_id: str | None = None,
        agent_id: str | None = None,
    ) -> None:
        self._records.append(CostRecord(
            workflow_id=workflow_id,
            agent_id=agent_id,
            provider_id=provider_id,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=cost,
            timestamp=datetime.now(UTC),
        ))

    def set_budget(self, scope: str, amount: Decimal) -> None:
        self._budgets[scope] = amount

    def get_spend(self, scope: str) -> Decimal:
        total = Decimal("0.00")
        for record in self._records:
            if scope in ("*", record.workflow_id, record.agent_id, record.provider_id):
                total += record.cost
        return total

    def get_budget(self, scope: str) -> Decimal | None:
        return self._budgets.get(scope) or self._budgets.get("*")

    def is_over_budget(self, scope: str) -> bool:
        budget = self.get_budget(scope)
        if budget is None:
            return False
        return self.get_spend(scope) > budget

    def get_records(
        self,
        workflow_id: str | None = None,
        agent_id: str | None = None,
        provider_id: str | None = None,
    ) -> list[CostRecord]:
        result = list(self._records)
        if workflow_id:
            result = [r for r in result if r.workflow_id == workflow_id]
        if agent_id:
            result = [r for r in result if r.agent_id == agent_id]
        if provider_id:
            result = [r for r in result if r.provider_id == provider_id]
        return result

    def total_cost(self) -> Decimal:
        return sum((r.cost for r in self._records), Decimal("0.00"))

    def clear(self) -> None:
        self._records.clear()
