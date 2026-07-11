# Metrics Report

## Overview

This report documents all Prometheus metrics exposed by the AARA backend application. Metrics are available at the `/metrics` endpoint in Prometheus text format.

---

## HTTP Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `http_requests_total` | Counter | `method`, `endpoint`, `status` | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | `method`, `endpoint` | HTTP request latency in seconds |
| `http_requests_active` | Gauge | `method` | Currently active HTTP requests |

## Authentication Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `auth_requests_total` | Counter | `method`, `status` | Total authentication requests |
| `auth_failures_total` | Counter | `reason` | Total authentication failures |

## Research & Content Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `research_requests_total` | Counter | `action`, `status` | Total research requests |
| `papers_total` | Gauge | - | Total number of papers |
| `citations_total` | Gauge | - | Total number of citations |

## AI Provider Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `ai_requests_total` | Counter | `provider`, `model`, `status` | Total AI provider requests |
| `ai_tokens_total` | Counter | `provider`, `model`, `type` | Total AI tokens consumed |

## Upload Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `uploads_total` | Counter | `file_type`, `status` | Total file uploads |
| `upload_bytes_total` | Counter | `file_type` | Total bytes uploaded |

## Database & Cache Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `db_query_duration_seconds` | Histogram | `operation` | Database query duration in seconds |
| `db_connections_active` | Gauge | - | Active database connections |
| `cache_hits_total` | Counter | `cache_name` | Total cache hits |
| `cache_misses_total` | Counter | `cache_name` | Total cache misses |
| `cache_size_bytes` | Gauge | `cache_name` | Cache size in bytes |

## Error Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `errors_total` | Counter | `type`, `severity` | Total errors |

## Background Task Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `background_tasks_active` | Gauge | - | Currently active background tasks |
| `background_tasks_completed_total` | Counter | `status` | Completed background tasks |

---

## Business Domain Coverage

| Domain | Metrics | Status |
|--------|---------|--------|
| Authentication | 2 | ✅ Covered |
| Research | 3 | ✅ Covered |
| Papers | 1 | ✅ Covered |
| Citations | 1 | ✅ Covered |
| AI Requests | 2 | ✅ Covered |
| Uploads | 2 | ✅ Covered |
| Database | 2 | ✅ Covered |
| Cache | 3 | ✅ Covered |
| Errors | 1 | ✅ Covered |
| HTTP Request Count | 1 | ✅ Covered |
| HTTP Status Codes | (via `http_requests_total`) | ✅ Covered |
| Request Latency | 1 | ✅ Covered |
| Active Requests | 1 | ✅ Covered |
| Background Tasks | 2 | ✅ Covered |

**Total Metrics: 22** (excluding label combinations)
