# Performance Baseline

Generated: {{DATE}}

## Environment

| Metric | Value |
|--------|-------|
| Host | TBD |
| CPU | TBD |
| Memory | TBD |
| Backend Workers | 4 |
| Database | PostgreSQL 16 |
| Vector Store | ChromaDB |
| Cache | Redis 7 |

## Baseline Results (Smoke Test)

| Endpoint | p50 | p95 | p99 | Error Rate |
|----------|-----|-----|-----|-----------|
| `GET /health` | TBD | TBD | TBD | 0% |
| `GET /openapi.json` | TBD | TBD | TBD | 0% |

## Average Load Results (50 concurrent users)

| Metric | Value |
|--------|-------|
| Throughput | TBD req/s |
| p50 Latency | TBD |
| p95 Latency | TBD |
| p99 Latency | TBD |
| Error Rate | TBD |

## Stress Test Results (200-300 users)

| Metric | Value |
|--------|-------|
| Max Throughput | TBD req/s |
| Breaking Point | TBD users |
| p95 at Peak | TBD |
| Error Rate | TBD |
| Recovery Time | TBD |

## Spike Test Results

| Metric | Value |
|--------|-------|
| Pre-spike Latency (p95) | TBD |
| Peak Latency (p95) | TBD |
| Recovery Time | TBD |
| Error Rate During Spike | TBD |

## Endurance Test Results (60 min)

| Metric | Value |
|--------|-------|
| Memory Drift | TBD MB/hr |
| Latency Drift | TBD ms/hr |
| Error Rate Trend | TBD |

## Capacity Planning

Based on these results, the system can handle approximately **TBD** concurrent users with an average latency under **TBD** ms.

## Recommendations

- TBD after baseline established
