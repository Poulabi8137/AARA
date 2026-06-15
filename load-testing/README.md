# Load Testing Framework

k6-based performance testing for AARA's API.

## Prerequisites

- [k6](https://k6.io/docs/get-started/installation/) installed
- Backend running locally or deployed

## Quick Start

```bash
# Smoke test (1 user, 30s)
k6 run smoke.js

# Average load (50 concurrent users)
k6 run average-load.js

# Stress test (escalating to 300+ users)
k6 run stress-test.js

# Spike test (10 -> 500 users in 10s)
k6 run spike-test.js

# Endurance test (60 min sustained load)
k6 run endurance-test.js
```

## Test Scenarios

| Scenario | Users | Duration | Goal |
|----------|-------|----------|------|
| Smoke | 1 | 30s | Verify basic endpoint functionality |
| Average Load | 50 | 6m | Simulate typical production traffic |
| Stress Test | 200-300 | 10m | Find breaking point and recovery |
| Spike Test | 10->500 | 2m | Test sudden traffic surge handling |
| Endurance | 30 | 70m | Detect memory leaks under sustained load |

## Customizing the Target

```bash
k6 run smoke.js -e BASE_URL=https://staging.example.com
k6 run average-load.js -e THINK_TIME=1.5
```

## Metrics Tracked

- Throughput (requests/sec)
- Latency (p50, p95, p99)
- Error rate
- Request duration by endpoint
- Failure rate thresholds

## Interpreting Results

After each run, k6 outputs:
- **http_req_duration** — request latency distribution
- **http_req_failed** — percentage of failed requests
- **vus** — virtual users over time
- **iterations** — total requests completed

Use these results to compare against the baseline in `performance_baseline.md`.
