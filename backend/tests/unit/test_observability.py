from __future__ import annotations

import pytest

from app.observability.audit import AuditCollector, AuditEvent
from app.observability.cost_collector import CostMetricsCollector
from app.observability.metrics import MetricsCollector
from app.observability.timers import PerformanceTimer
from app.observability.tracing import Tracer


class TestMetricsCollector:
    def test_increment(self):
        m = MetricsCollector()
        m.increment("requests")
        assert m.get_counter("requests") == 1.0
        m.increment("requests", 5.0)
        assert m.get_counter("requests") == 6.0

    def test_gauge(self):
        m = MetricsCollector()
        m.gauge("memory", 512.0)
        assert m.get_gauge("memory") == 512.0

    def test_observe(self):
        m = MetricsCollector()
        m.observe("latency", 100.0)
        m.observe("latency", 200.0)
        hist = m.get_histogram("latency")
        assert len(hist) == 2

    def test_tagged_keys(self):
        m = MetricsCollector()
        m.increment("requests", tags={"endpoint": "/api"})
        assert m.get_counter("requests", tags={"endpoint": "/api"}) == 1.0
        assert m.get_counter("requests") == 0.0

    def test_snapshot(self):
        m = MetricsCollector()
        m.increment("r", 1)
        snap = m.snapshot()
        assert "counters" in snap

    def test_reset(self):
        m = MetricsCollector()
        m.increment("r", 1)
        m.reset()
        assert m.get_counter("r") == 0.0


class TestTracer:
    @pytest.mark.asyncio
    async def test_span_context(self):
        tracer = Tracer()
        async with tracer.span("op1") as span:
            assert span.name == "op1"
            assert span.span_id is not None
        assert len(tracer.get_spans()) == 1

    @pytest.mark.asyncio
    async def test_nested_spans(self):
        tracer = Tracer()
        async with tracer.span("parent"), tracer.span("child"):
            pass
        spans = tracer.get_spans()
        assert len(spans) == 2
        child = [s for s in spans if s.name == "child"][0]
        assert child.parent_id is not None

    @pytest.mark.asyncio
    async def test_span_error(self):
        tracer = Tracer()
        with pytest.raises(ValueError):
            async with tracer.span("failing"):
                raise ValueError("boom")
        spans = tracer.get_spans()
        assert spans[0].status == "error"

    def test_get_trace(self):
        tracer = Tracer()
        tracer._spans = [
            type("S", (), {"span_id": "a", "parent_id": None})(),
            type("S", (), {"span_id": "b", "parent_id": "a"})(),
        ]
        trace = tracer.get_trace("a")
        assert len(trace) == 2

    def test_clear(self):
        tracer = Tracer()
        tracer._spans.append(type("S", (), {"span_id": "a", "parent_id": None, "name": "t", "start_time": 0.0, "end_time": None, "attributes": {}, "status": "ok", "error": None, "duration_ms": 0.0})())  # noqa: E501
        tracer.clear()
        assert len(tracer.get_spans()) == 0


class TestPerformanceTimer:
    @pytest.mark.asyncio
    async def test_measure(self):
        timer = PerformanceTimer()
        async with timer.measure("op"):
            pass
        measurements = timer.get_measurements()
        assert len(measurements) == 1
        assert measurements[0].duration_ms > 0

    @pytest.mark.asyncio
    async def test_get_average(self):
        timer = PerformanceTimer()
        async with timer.measure("op"):
            pass
        async with timer.measure("op"):
            pass
        avg = timer.get_average("op")
        assert avg > 0

    def test_clear(self):
        timer = PerformanceTimer()
        timer._measurements.append(type("M", (), {"name": "t", "duration_ms": 1.0, "tags": {}, "success": True})())  # noqa: E501
        timer.clear()
        assert len(timer.get_measurements()) == 0


class TestCostMetricsCollector:
    def test_record_inference(self):
        from decimal import Decimal
        c = CostMetricsCollector()
        c.record_inference("openai", "gpt-4", 100, 50, Decimal("0.01"), "wf-1")
        assert c.total_cost() == Decimal("0.01")

    def test_get_spend(self):
        from decimal import Decimal
        c = CostMetricsCollector()
        c.record_inference("openai", "gpt-4", 100, 50, Decimal("0.01"), "wf-1")
        assert c.get_spend("wf-1") == Decimal("0.01")
        assert c.get_spend("wf-2") == Decimal("0.00")

    def test_budget(self):
        from decimal import Decimal
        c = CostMetricsCollector()
        c.set_budget("*", Decimal("10.00"))
        assert c.get_budget("*") == Decimal("10.00")
        assert c.is_over_budget("*") is False

    def test_get_records_filter(self):
        from decimal import Decimal
        c = CostMetricsCollector()
        c.record_inference("openai", "gpt-4", 100, 50, Decimal("0.01"), "wf-1")
        c.record_inference("gemini", "gemini-pro", 100, 50, Decimal("0.02"), "wf-2")
        assert len(c.get_records(provider_id="openai")) == 1

    def test_clear(self):
        from decimal import Decimal
        c = CostMetricsCollector()
        c.record_inference("o", "m", 0, 0, Decimal("0"), "w")
        c.clear()
        assert c.total_cost() == Decimal("0.00")


class TestAuditCollector:
    def test_record(self):
        a = AuditCollector()
        a.record(AuditEvent(actor_id="u1", action="create", resource_type="workspace", resource_id="1"))  # noqa: E501
        assert a.count() == 1

    def test_get_events_filter(self):
        a = AuditCollector()
        a.record(AuditEvent(actor_id="u1", action="create", resource_type="workspace", resource_id="1"))  # noqa: E501
        a.record(AuditEvent(actor_id="u2", action="delete", resource_type="workspace", resource_id="2"))  # noqa: E501
        events = a.get_events(action="create")
        assert len(events) == 1

    def test_clear(self):
        a = AuditCollector()
        a.record(AuditEvent(actor_id="u1", action="create", resource_type="w", resource_id="1"))
        a.clear()
        assert a.count() == 0
