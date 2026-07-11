# Dashboard Documentation

## Overview

This report documents all Grafana dashboards configured for monitoring the AARA application. Dashboard JSON files are located in `monitoring/dashboards/`.

---

## Dashboard: API Performance

| Property | Value |
|----------|-------|
| **File** | `monitoring/dashboards/api-performance.json` |
| **UID** | `api-performance` |
| **Purpose** | Monitor HTTP request performance and error rates |

### Panels

| Panel | Type | Metrics |
|-------|------|---------|
| HTTP Request Rate | Graph | `rate(http_requests_total[5m])` |
| Request Latency (P50/P95/P99) | Graph | `http_request_duration_seconds` histogram quantiles |
| Active Requests | Graph | `http_requests_active` |
| HTTP Status Codes | Graph | `sum by (status) (rate(http_requests_total[5m]))` |
| Error Rate | Graph | `sum(rate(errors_total[5m]))` |
| Background Tasks | Stat | `background_tasks_active` |

## Dashboard: Database

| Property | Value |
|----------|-------|
| **File** | `monitoring/dashboards/database.json` |
| **UID** | `database` |
| **Purpose** | Monitor database performance and cache efficiency |

### Panels

| Panel | Type | Metrics |
|-------|------|---------|
| Active Connections | Graph | `db_connections_active` |
| Query Duration (P50/P95) | Graph | `db_query_duration_seconds` histogram quantiles |
| Cache Hit/Miss Rate | Graph | `cache_hits_total`, `cache_misses_total` rates |
| Cache Size by Name | Graph | `cache_size_bytes` |

## Dashboard: Authentication

| Property | Value |
|----------|-------|
| **File** | `monitoring/dashboards/authentication.json` |
| **UID** | `authentication` |
| **Purpose** | Monitor authentication request patterns and failures |

### Panels

| Panel | Type | Metrics |
|-------|------|---------|
| Auth Request Rate | Graph | `rate(auth_requests_total[5m])` |
| Auth Failure Rate | Graph | `rate(auth_failures_total[5m])` |
| Auth Success vs Failure | Stat | `sum(auth_requests_total)`, `sum(auth_failures_total)` |

## Dashboard: AI Providers

| Property | Value |
|----------|-------|
| **File** | `monitoring/dashboards/ai-providers.json` |
| **UID** | `ai-providers` |
| **Purpose** | Monitor AI provider usage, cost, and error rates |

### Panels

| Panel | Type | Metrics |
|-------|------|---------|
| AI Request Rate by Provider | Graph | `rate(ai_requests_total[5m])` |
| Token Consumption | Graph | `rate(ai_tokens_total[5m])` |
| AI Request Status | Graph | `sum by (status) (rate(ai_requests_total[5m]))` |

## Dashboard: Uploads

| Property | Value |
|----------|-------|
| **File** | `monitoring/dashboards/uploads.json` |
| **UID** | `uploads` |
| **Purpose** | Monitor file upload volume and success rates |

### Panels

| Panel | Type | Metrics |
|-------|------|---------|
| Upload Rate by File Type | Graph | `rate(uploads_total[5m])` |
| Total Uploaded Bytes | Graph | `rate(upload_bytes_total[5m])` |
| Upload Success vs Failure | Stat | `sum(uploads_total{status="success"})`, `sum(uploads_total{status="failed"})` |

## Dashboard: Application Health

| Property | Value |
|----------|-------|
| **File** | `monitoring/dashboards/application-health.json` |
| **UID** | `application-health` |
| **Purpose** | Monitor overall application health and error rates |

### Panels

| Panel | Type | Metrics |
|-------|------|---------|
| Overall Health Status | Stat | `up{job="aara-backend"}` |
| Error Rate by Type | Graph | `sum by (type) (rate(errors_total[5m]))` |
| Active Background Tasks | Graph | `background_tasks_active` |
| Background Tasks Completed | Graph | `rate(background_tasks_completed_total[5m])` |

## Dashboard: Infrastructure

| Property | Value |
|----------|-------|
| **File** | `monitoring/dashboards/infrastructure.json` |
| **UID** | `infrastructure` |
| **Purpose** | Monitor system resource usage (memory, CPU, etc.) |

### Panels

| Panel | Type | Metrics |
|-------|------|---------|
| Memory Usage | Graph | `process_resident_memory_bytes`, `process_virtual_memory_bytes` |
| CPU Usage | Graph | `rate(process_cpu_seconds_total[5m])` |
| Open File Descriptors | Graph | `process_open_fds` |
| Start Time | Stat | `time() - process_start_time_seconds` |

---

## Dashboard Summary

| Dashboard | Panels | Focus Area | Refresh Rate |
|-----------|--------|------------|-------------|
| API Performance | 6 | HTTP metrics & errors | 15s |
| Database | 4 | DB & cache performance | 15s |
| Authentication | 3 | Auth patterns & failures | 30s |
| AI Providers | 3 | AI usage & errors | 30s |
| Uploads | 3 | File upload metrics | 30s |
| Application Health | 4 | Overall system health | 10s |
| Infrastructure | 4 | System resources | 15s |

**Total Dashboards: 7**
**Total Panels: 27**
