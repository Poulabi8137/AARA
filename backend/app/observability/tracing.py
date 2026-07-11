from __future__ import annotations

import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

current_span: ContextVar[str | None] = ContextVar("current_span", default=None)


@dataclass
class Span:
    span_id: str
    parent_id: str | None
    name: str
    start_time: float
    end_time: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    status: str = "ok"
    error: str | None = None

    @property
    def duration_ms(self) -> float:
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000


class Tracer:
    def __init__(self) -> None:
        self._spans: list[Span] = []

    @asynccontextmanager
    async def span(
        self, name: str, attributes: dict[str, Any] | None = None
    ) -> AsyncGenerator[Span, Any]:
        span_id = str(uuid.uuid4())
        parent_id = current_span.get()
        token = current_span.set(span_id)
        span = Span(
            span_id=span_id,
            parent_id=parent_id,
            name=name,
            start_time=time.time(),
            attributes=attributes or {},
        )
        try:
            yield span
            span.status = "ok"
        except Exception as exc:
            span.status = "error"
            span.error = str(exc)
            raise
        finally:
            span.end_time = time.time()
            self._spans.append(span)
            current_span.reset(token)

    def get_spans(self) -> list[Span]:
        return list(self._spans)

    def get_trace(self, span_id: str) -> list[Span]:
        result: list[Span] = []
        direct = [s for s in self._spans if s.span_id == span_id]
        result.extend(direct)
        children = [s for s in self._spans if s.parent_id == span_id]
        for child in children:
            result.extend(self.get_trace(child.span_id))
        return result

    def clear(self) -> None:
        self._spans.clear()
