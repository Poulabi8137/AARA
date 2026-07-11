# Repository Audit - Phase 8.3 Production Monitoring & Observability

## Current State Analysis

### ✅ Already Implemented (Reuse These)

| Component | File | Status |
|-----------|------|--------|
| In-memory Metrics Collector | `app/observability/metrics.py` | Basic counters/gauges/histograms |
| Health Checker | `app/observability/health.py` | Database, cache, AI service checks |
| Structured Logging | `app/observability/logging.py` + `app/core/logging_config.py` | **DUPLICATE** - Two implementations |
| Request Tracing | `app/observability/tracing.py` | Span-based tracing (no OpenTelemetry) |
| Audit Logging | `app/observability/audit.py` | In-memory audit events |
| Performance Timers | `app/observability/timers.py` | Async context manager for timing |
| Cost Collection | `app/observability/cost_collector.py` | AI inference cost tracking |
| Request ID Middleware | `app/core/middleware.py` | X-Request-ID header |
| Timing Middleware | `app/core/middleware.py` | X-Processing-Time-Ms header |
| Basic Health Endpoint | `app/main.py` | `/health` returns status/version/env |
| Prometheus Client | `pyproject.toml` | Dependency already declared |

### ❌ Missing / Incomplete (Need to Implement)

| Component | Gap | Required |
|-----------|-----|----------|
| Prometheus `/metrics` endpoint | No endpoint exists | ✅ Required |
| Prometheus metrics export | In-memory only, no Prometheus format | ✅ Required |
| HTTP Request Metrics | No request count, latency, status codes, active requests | ✅ Required |
| Business Metrics | No auth, research, papers, citations, AI, uploads, DB, cache, errors | ✅ Required |
| Liveness Probe | No `/health/live` endpoint | ✅ Required |
| Readiness Probe | No `/health/ready` endpoint | ✅ Required |
| Correlation ID in logs | Request ID not propagated to structured logs | ✅ Required |
| Grafana Dashboards | No dashboard JSON files | ✅ Required |
| Prometheus Alert Rules | No alerting configuration | ✅ Required |
| Background Task Metrics | No metrics for background jobs | ✅ Required |

### ⚠️ Duplicates to Consolidate

1. **Structured Logging** - Two implementations:
   - `app/observability/logging.py` - Has `inject_correlation_id`, `add_service_context`
   - `app/core/logging_config.py` - Used by events.py
   
   **Action**: Consolidate into single implementation in `app/observability/logging.py`

---

## Implementation Plan

### Phase 1: Consolidate & Fix Logging
- Merge logging implementations
- Add correlation ID injection from middleware to logs

### Phase 2: Prometheus Metrics
- Create `app/observability/prometheus.py` with Prometheus metrics
- Add HTTP middleware for request metrics
- Add business metrics for all required domains
- Create `/metrics` endpoint

### Phase 3: Health Endpoints
- Add `/health/live` (liveness probe)
- Add `/health/ready` (readiness probe)
- Enhance `/health` with detailed checks

### Phase 4: Dashboards & Alerts
- Create Grafana dashboard JSON files
- Create Prometheus alert rules

### Phase 5: Validation & Documentation
- Validate all endpoints
- Generate required reports