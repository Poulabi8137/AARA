# Alert Configuration

## Overview

This report documents all Prometheus alert rules configured for the AARA backend application. Rules are defined in `monitoring/alerts/prometheus-alerts.yml`.

---

## Alert Rules

### 1. High Error Rate

| Property | Value |
|----------|-------|
| **Name** | HighErrorRate |
| **Expression** | `rate(errors_total[5m]) > 10` |
| **For** | 2 minutes |
| **Severity** | critical |
| **Summary** | High error rate detected |
| **Description** | Error rate exceeded 10 errors/sec for more than 2 minutes |
| **Action** | Investigate root cause, check recent deployments, review error logs |

### 2. Database Unavailable

| Property | Value |
|----------|-------|
| **Name** | DatabaseUnavailable |
| **Expression** | `up{job="aara-backend"} == 0` |
| **For** | 1 minute |
| **Severity** | critical |
| **Summary** | Database service is unavailable |
| **Description** | Database endpoint is not reachable |
| **Action** | Check database connectivity, verify credentials, restart database service |

### 3. High Memory Usage

| Property | Value |
|----------|-------|
| **Name** | HighMemoryUsage |
| **Expression** | `process_resident_memory_bytes > 500MB` |
| **For** | 5 minutes |
| **Severity** | warning |
| **Summary** | High memory usage |
| **Description** | Memory usage exceeded 500MB for more than 5 minutes |
| **Action** | Review memory leaks, increase memory limits, restart service |

### 4. High CPU Usage

| Property | Value |
|----------|-------|
| **Name** | HighCPUUsage |
| **Expression** | `rate(process_cpu_seconds_total[5m]) > 0.8` |
| **For** | 5 minutes |
| **Severity** | warning |
| **Summary** | High CPU usage |
| **Description** | CPU usage exceeded 80% for more than 5 minutes |
| **Action** | Scale horizontally, optimize resource-intensive operations |

### 5. High Request Latency

| Property | Value |
|----------|-------|
| **Name** | HighRequestLatency |
| **Expression** | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2.0` |
| **For** | 5 minutes |
| **Severity** | warning |
| **Summary** | High request latency |
| **Description** | P95 latency exceeded 2 seconds |
| **Action** | Optimize slow endpoints, check database query performance, scale resources |

### 6. Repeated Authentication Failures

| Property | Value |
|----------|-------|
| **Name** | RepeatedAuthFailures |
| **Expression** | `rate(auth_failures_total[5m]) > 5` |
| **For** | 2 minutes |
| **Severity** | critical |
| **Summary** | Repeated authentication failures |
| **Description** | Auth failure rate exceeded 5/sec for more than 2 minutes |
| **Action** | Investigate potential brute-force attack, check auth provider, rotate credentials |

### 7. AI Provider Failures

| Property | Value |
|----------|-------|
| **Name** | AIProviderFailure |
| **Expression** | `rate(ai_requests_total{status="error"}[5m]) > 5` |
| **For** | 2 minutes |
| **Severity** | warning |
| **Summary** | AI provider failure rate elevated |
| **Description** | AI provider error rate exceeded 5 errors/sec |
| **Action** | Check AI provider status, verify API keys, fallback to alternative provider |

### 8. Application Down

| Property | Value |
|----------|-------|
| **Name** | ApplicationDown |
| **Expression** | `up{job="aara-backend"} == 0` |
| **For** | 30 seconds |
| **Severity** | critical |
| **Summary** | AARA backend is down |
| **Description** | Backend service unreachable for 30 seconds |
| **Action** | Restart service, check deployment, investigate crashes |

### 9. High Background Task Queue

| Property | Value |
|----------|-------|
| **Name** | HighBackgroundTaskQueue |
| **Expression** | `background_tasks_active > 20` |
| **For** | 5 minutes |
| **Severity** | warning |
| **Summary** | High number of active background tasks |
| **Description** | More than 20 background tasks active for over 5 minutes |
| **Action** | Scale workers, investigate stuck tasks, review job queue |

### 10. Storage Unavailable

| Property | Value |
|----------|-------|
| **Name** | StorageUnavailable |
| **Expression** | `rate(uploads_total{status="failed"}[5m]) > 3` |
| **For** | 2 minutes |
| **Severity** | critical |
| **Summary** | Storage service may be unavailable |
| **Description** | Upload failure rate exceeded 3/sec for more than 2 minutes |
| **Action** | Check storage service, verify disk space, investigate file system issues |

---

## Alert Summary

| Severity | Count | Priority |
|----------|-------|----------|
| critical | 6 | Immediate response required |
| warning | 4 | Investigation required within business hours |
| info | 0 | Informational only |

## Notification Channels

- **critical**: PagerDuty + Slack + Email
- **warning**: Slack + Email
- **info**: Slack (optional)

## Runbook References

| Alert | Runbook |
|-------|---------|
| HighErrorRate | [Error Investigation](../runbooks/error-investigation.md) |
| DatabaseUnavailable | [Database Recovery](../runbooks/database-recovery.md) |
| HighMemoryUsage | [Memory Optimization](../runbooks/memory-optimization.md) |
| HighCPUUsage | [CPU Optimization](../runbooks/cpu-optimization.md) |
| HighRequestLatency | [Performance Tuning](../runbooks/performance-tuning.md) |
| RepeatedAuthFailures | [Security Incident](../runbooks/security-incident.md) |
| AIProviderFailure | [AI Provider Fallback](../runbooks/ai-provider-fallback.md) |
| ApplicationDown | [Service Recovery](../runbooks/service-recovery.md) |
| HighBackgroundTaskQueue | [Task Queue Management](../runbooks/task-queue-management.md) |
| StorageUnavailable | [Storage Recovery](../runbooks/storage-recovery.md) |
