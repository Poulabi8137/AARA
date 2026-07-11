from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from prometheus_client.registry import REGISTRY

from app.observability.metrics import MetricsCollector


def _counter(name: str, documentation: str, labelnames: tuple[str, ...] = ()) -> Counter:
    if name in REGISTRY._names_to_collectors:
        return REGISTRY._names_to_collectors[name]
    return Counter(name, documentation, labelnames)


def _gauge(name: str, documentation: str, labelnames: tuple[str, ...] = ()) -> Gauge:
    if name in REGISTRY._names_to_collectors:
        return REGISTRY._names_to_collectors[name]
    return Gauge(name, documentation, labelnames)


def _histogram(name: str, documentation: str, labelnames: tuple[str, ...] = (), buckets: tuple[float, ...] = ()) -> Histogram:
    if name in REGISTRY._names_to_collectors:
        return REGISTRY._names_to_collectors[name]
    return Histogram(name, documentation, labelnames, buckets=buckets)

REQUEST_COUNT = _counter("http_requests_total", "Total HTTP requests", ("method", "endpoint", "status"))

REQUEST_LATENCY = _histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ("method", "endpoint"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

ACTIVE_REQUESTS = _gauge("http_requests_active", "Currently active HTTP requests", ("method",))

AUTH_REQUESTS = _counter("auth_requests_total", "Total authentication requests", ("method", "status"))

AUTH_FAILURES = _counter("auth_failures_total", "Total authentication failures", ("reason",))

RESEARCH_REQUESTS = _counter("research_requests_total", "Total research requests", ("action", "status"))

PAPERS_TOTAL = _gauge("papers_total", "Total number of papers")

CITATIONS_TOTAL = _gauge("citations_total", "Total number of citations")

AI_REQUESTS = _counter("ai_requests_total", "Total AI provider requests", ("provider", "model", "status"))

AI_TOKENS = _counter("ai_tokens_total", "Total AI tokens consumed", ("provider", "model", "type"))

UPLOADS_TOTAL = _counter("uploads_total", "Total file uploads", ("file_type", "status"))

UPLOAD_BYTES = _counter("upload_bytes_total", "Total bytes uploaded", ("file_type",))

DB_QUERY_DURATION = _histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ("operation",),
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)

DB_CONNECTIONS = _gauge("db_connections_active", "Active database connections")

CACHE_HITS = _counter("cache_hits_total", "Total cache hits", ("cache_name",))

CACHE_MISSES = _counter("cache_misses_total", "Total cache misses", ("cache_name",))

CACHE_SIZE = _gauge("cache_size_bytes", "Cache size in bytes", ("cache_name",))

ERROR_COUNT = _counter("errors_total", "Total errors", ("type", "severity"))

BACKGROUND_TASKS = _gauge("background_tasks_active", "Currently active background tasks")

BACKGROUND_TASKS_COMPLETED = _counter("background_tasks_completed_total", "Completed background tasks", ("status",))


class PrometheusExporter:
    def __init__(self, metrics_collector: MetricsCollector | None = None) -> None:
        self._metrics_collector = metrics_collector

    def export(self) -> bytes:
        if self._metrics_collector:
            for name, value in self._metrics_collector.get_all_counters().items():
                REQUEST_COUNT.labels(method="all", endpoint=name, status="200").inc(value)

            for name, value in self._metrics_collector.get_all_gauges().items():
                ACTIVE_REQUESTS.labels(method="all").set(value)

        return generate_latest(REGISTRY)

    def get_content_type(self) -> str:
        return CONTENT_TYPE_LATEST


prometheus_exporter = PrometheusExporter()


def get_prometheus_metrics() -> bytes:
    return prometheus_exporter.export()
