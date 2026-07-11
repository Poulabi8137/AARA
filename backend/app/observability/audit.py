from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID


@dataclass
class AuditEvent:
    actor_id: UUID | str | None
    action: str
    resource_type: str
    resource_id: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime | None = None
    correlation_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None


class AuditCollector:
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> None:
        if event.timestamp is None:
            event.timestamp = datetime.now(UTC)
        self._events.append(event)

    def get_events(
        self,
        actor_id: UUID | str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        result = list(self._events)
        if actor_id:
            result = [e for e in result if e.actor_id == actor_id]
        if action:
            result = [e for e in result if e.action == action]
        if resource_type:
            result = [e for e in result if e.resource_type == resource_type]
        return result[-limit:]

    def count(self) -> int:
        return len(self._events)

    def clear(self) -> None:
        self._events.clear()
