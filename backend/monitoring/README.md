# Monitoring & Observability

## Overview

AARA uses Prometheus + Grafana for metrics and monitoring, with Sentry for error tracking.

## Quick Start

With the staging stack:

```bash
docker compose -f docker-compose.staging.yml up -d prometheus grafana
```

Then access:
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)

## Metrics

Exposed at `GET /metrics` (Prometheus text format).

### HTTP Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `http_requests_total` | Counter | method, path, status | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | method, path | Request latency distribution |

### Business Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `workflow_duration_seconds` | Histogram | status | LangGraph workflow duration |
| `agent_duration_seconds` | Histogram | agent_name, status | Per-agent execution time |
| `llm_request_duration_seconds` | Histogram | provider | LLM provider latency |
| `db_query_duration_seconds` | Histogram | operation | Database query latency |

### Error & Security Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `errors_total` | Counter | error_type, service | Errors by category |
| `auth_failures_total` | Counter | reason | Auth failure reasons |
| `rate_limit_violations_total` | Counter | client_type, path | Rate limit hits |

### Resource Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `queue_depth` | Gauge | queue_name | Dramatiq queue depth |
| `active_workflows` | Gauge | — | Concurrent workflow count |

## Health Endpoints

| Endpoint | Purpose | Expected Status |
|----------|---------|-----------------|
| `GET /health` | Detailed health (DB, Redis, uptime) | `healthy` |
| `GET /ready` | Readiness probe for k8s/docker | `ready` |
| `GET /live` | Liveness probe for k8s/docker | `alive` |

## Grafana Dashboards

Pre-configured dashboards are in `monitoring/grafana/dashboards/`:
- **AgentWatch Overview** (`agentwatch_overview.json`): Global system metrics
- **AgentWatch Alerts** (`agentwatch_alerts.json`): Alerting dashboard

## Prometheus Alerts

Pre-configured alerts in `monitoring/prometheus/alerts.yml`:
- High error rate (>5%)
- High latency (p95 > 5s)
- Service down
- Rate limit violations spike
- Queue depth growing

## Sentry Integration

Configure via environment variables:
- `SENTRY_DSN`: Your Sentry DSN
- `SENTRY_ENVIRONMENT`: Environment name (production/staging)

## Key Queries

```promql
# Request rate (last 5m)
rate(http_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(errors_total[5m]) / rate(http_requests_total[5m]) * 100

# Active workflows
active_workflows
```
