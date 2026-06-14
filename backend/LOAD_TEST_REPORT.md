# AgentWatch Load Test Report

**Date:** June 13, 2026
**Version:** 0.1.0
**Prepared For:** Production Certification

---

## Table of Contents

1. Test Methodology
2. Architecture Model
3. Expected Performance at Scale
4. Scenarios to Test
5. k6 Test Script
6. Locust Test Script
7. Infrastructure Sizing
8. Bottleneck Analysis
9. Scaling Recommendations

---

## 1. Test Methodology

### 1.1 Tool Selection

Load testing is performed using **k6** (primary) and **Locust** (secondary) to cover both script-based and interactive testing needs. k6 provides high throughput, low overhead, and excellent threshold assertions. Locust provides real-time web UI and Python-native test authoring.

### 1.2 Test Environment

| Parameter | Value |
|-----------|-------|
| Protocol | HTTP/1.1 (upgraded to HTTP/2 if supported) |
| Load generator location | Same region as target (us-east-1) |
| Load generator instances | 2 x c6i.4xlarge (16 vCPU, 32 GB each) |
| Target environment | Staging (identical to production spec) |
| Ramp-up period | 60 seconds |
| Steady-state hold | 300 seconds |
| Cool-down period | 30 seconds |
| Think time | Uniform 1-3s between user actions |

### 1.3 Key Metrics & Thresholds

| Metric | Acceptable | Target | Critical |
|--------|-----------|--------|----------|
| p50 API latency | < 200ms | < 100ms | > 500ms |
| p95 API latency | < 500ms | < 300ms | > 1s |
| p99 API latency | < 2s | < 1s | > 5s |
| Error rate | < 1% | < 0.1% | > 5% |
| Workflow completion rate | > 95% | > 99% | < 90% |
| Queue depth | < 100 | < 20 | > 500 |
| DB pool utilization | < 80% | < 60% | > 95% |
| Redis ops/sec | < 10,000 | < 5,000 | > 20,000 |

### 1.4 Test Sequence

1. **Baseline** — Single user, all endpoints (warm-up, 60s)
2. **Step load** — 10/50/100/250/500/1000 concurrent users (300s each step)
3. **Burst test** — 0→500 users in 10s, hold 60s
4. **Soak test** — 200 concurrent users for 4 hours
5. **Stress test** — Ramp to 2000+ users until errors exceed 5%

---

## 2. Architecture Model

### 2.1 System Components

```
                         ┌─────────────────────────────────────┐
                         │        AWS Application Load         │
                         │        Balancer (ALB)               │
                         └────────────┬────────────────────────┘
                                      │
                         ┌────────────┴────────────────────────┐
                         │     FastAPI / Uvicorn (4 workers)    │
                         │     per container, N containers     │
                         ├─────────────────────────────────────┤
                         │  Middleware Stack:                  │
                         │  1. CORS                            │
                         │  2. Security Headers (HSTS, CSP)    │
                         │  3. Request Logging (structured)    │
                         │  4. Rate Limit (Redis sliding win)  │
                         │  5. Metrics (Prometheus histograms) │
                         └──────┬──────────────┬───────────────┘
                                │              │
                  ┌─────────────┴──┐   ┌──────┴──────────────┐
                  │   PostgreSQL   │   │       Redis          │
                  │   16-alpine    │   │   (Cache + Queue)    │
                  │  pool:10/20    │   │   pool:10            │
                  │  max:100       │   │   max:10000 ops/s    │
                  └────────────────┘   └──────┬───────────────┘
                                              │
                                   ┌──────────┴──────────────┐
                                   │   Dramatiq Workers       │
                                   │   (4-16 processes)       │
                                   │   Queue: workflows       │
                                   │   Timeout: 600s          │
                                   └──────────┬───────────────┘
                                              │
                                   ┌──────────┴──────────────┐
                                   │     ChromaDB             │
                                   │     (single node)        │
                                   │     5 collections        │
                                   └─────────────────────────┘
```

### 2.2 Data Flow

1. **Login flow**: Client → ALB → API → Redis (rate limit check) → DB (user lookup) → JWT issued → Response
2. **Document upload**: Client → API → Redis (rate limit) → File buffer → Ingestion pipeline (extract → chunk → embed → ChromaDB → DB record)
3. **Workflow start**: Client → API → Redis (rate limit) → DB (create execution record) → Dramatiq enqueue → Response (202 Accepted)
4. **Workflow progress**: Dramatiq worker → DB (status update) → LangGraph graph run (5-6 nodes) → LLM calls → ChromaDB queries → DB (store result)
5. **Poll execution status**: Client → API → DB (select execution) → Response
6. **Report retrieval**: Client → API → Redis (cache check) → DB (select report) → Response

### 2.3 Identified Bottlenecks

| # | Bottleneck | Location | Impact |
|---|-----------|----------|--------|
| B1 | LLM provider API call latency | LangGraph nodes | 5-30s per workflow |
| B2 | ChromaDB single-node throughput | Vectorstore | ~100 QPS max |
| B3 | PostgreSQL write master contention | DB | ~5000 TPS write limit |
| B4 | Dramatiq Redis broker throughput | Workers | ~2000 msg/s limit |
| B5 | Python GIL in sync agents | Worker processes | CPU-bound agents |
| B6 | Embedding model inference time | Ingestion/Retrieval | 100-500ms per call |

### 2.4 Resource Limits

| Resource | Limit per Container | Scaling Strategy |
|----------|--------------------|------------------|
| API connections | 1000 concurrent | Horizontal (N containers) |
| DB connections | 100 (pool+overflow) | PgBouncer + read replicas |
| Redis connections | 10 (pool) | Redis Cluster |
| Worker threads | 8 per process | Add worker processes |
| ChromaDB QPS | ~100 | Vertical (single node limit) |

---

## 3. Expected Performance at Scale

### 3.1 100 Concurrent Users (Light Load)

| Endpoint | RPS | p50 | p95 | p99 | Error Rate |
|----------|-----|-----|-----|-----|------------|
| GET /health | 5 | 5ms | 10ms | 20ms | 0% |
| POST /auth/login | 2 | 50ms | 120ms | 250ms | <0.1% |
| POST /auth/register | 0.5 | 80ms | 200ms | 400ms | <0.5% |
| POST /documents/upload | 1 | 500ms | 2s | 5s | <1% |
| POST /agents/run | 0.5 | 200ms | 500ms | 1s | <1% |
| GET /agents/{id}/status | 20 | 20ms | 50ms | 100ms | 0% |
| GET /reports/{id} | 5 | 30ms | 80ms | 150ms | 0% |
| POST /evaluation/run | 0.3 | 300ms | 800ms | 2s | <1% |

**Queue depth**: 0-5 (near real-time)
**DB pool utilization**: 10-20%
**Worker saturation**: 1-2 concurrent workflows
**Redis ops/s**: 200-500
**Cache hit ratio**: 40-60%

### 3.2 500 Concurrent Users (Medium Load)

| Endpoint | RPS | p50 | p95 | p99 | Error Rate |
|----------|-----|-----|-----|-----|------------|
| GET /health | 25 | 8ms | 20ms | 40ms | 0% |
| POST /auth/login | 10 | 80ms | 200ms | 500ms | <0.5% |
| POST /auth/register | 2.5 | 150ms | 400ms | 800ms | <1% |
| POST /documents/upload | 5 | 1s | 4s | 10s | <2% |
| POST /agents/run | 2.5 | 300ms | 800ms | 2s | <1% |
| GET /agents/{id}/status | 100 | 30ms | 80ms | 200ms | <0.1% |
| GET /reports/{id} | 25 | 40ms | 100ms | 250ms | <0.1% |
| POST /evaluation/run | 1.5 | 500ms | 1.5s | 4s | <2% |

**Queue depth**: 10-30 (some backlog expected)
**DB pool utilization**: 40-60%
**Worker saturation**: 5-10 concurrent workflows
**Redis ops/s**: 1,000-2,500
**Cache hit ratio**: 50-70%

### 3.3 1000 Concurrent Users (Heavy Load)

| Endpoint | RPS | p50 | p95 | p99 | Error Rate |
|----------|-----|-----|-----|-----|------------|
| GET /health | 50 | 10ms | 30ms | 60ms | 0% |
| POST /auth/login | 20 | 150ms | 400ms | 1s | <1% |
| POST /auth/register | 5 | 250ms | 600ms | 1.5s | <2% |
| POST /documents/upload | 10 | 2s | 6s | 15s | <3% |
| POST /agents/run | 5 | 500ms | 1.5s | 3s | <2% |
| GET /agents/{id}/status | 200 | 50ms | 150ms | 300ms | <0.5% |
| GET /reports/{id} | 50 | 60ms | 200ms | 400ms | <0.5% |
| POST /evaluation/run | 3 | 800ms | 2.5s | 6s | <3% |

**Queue depth**: 50-150 (significant backlog)
**DB pool utilization**: 75-95% (approaching saturation)
**Worker saturation**: 15-25 concurrent workflows
**Redis ops/s**: 2,000-5,000
**Cache hit ratio**: 55-75%

---

## 4. Scenarios to Test

### 4.1 Scenario 1: Login Burst

**Objective**: Verify rate limiting and auth DB performance under burst.

**Profile**:
- 500 users attempting login simultaneously (ramp in 5s)
- 50% correct credentials, 50% incorrect
- Each user repeats login 3 times with 2s think time

**Pass Criteria**:
- Rate limiter activates at 5 req/min per user (status 429)
- p95 auth latency < 300ms
- No DB connection pool exhaustion
- No false negatives (valid credentials should never 429)

### 4.2 Scenario 2: Document Upload

**Objective**: Test ingestion pipeline throughput.

**Profile**:
- 5 PDF files (100KB-5MB each) per user
- 50 concurrent users uploading
- Each upload followed by status poll (every 2s until indexed)

**Pass Criteria**:
- Upload p95 < 5s for files < 1MB
- Ingestion pipeline completes within 30s for 5MB files
- ChromaDB ingestion rate > 50 chunks/s
- No document corruption or partial ingestion
- DB write throughput handles chunk metadata

### 4.3 Scenario 3: Workflow Start + Poll

**Objective**: Test async workflow execution pipeline.

**Profile**:
- 30 concurrent users submitting workflows
- Each submits a research query (50-200 chars)
- Poll execution status every 3s for up to 5 minutes
- Workflow uses MockProvider (no LLM latency)

**Pass Criteria**:
- 100% of workflows accepted (HTTP 202)
- p50 workflow completion time < 30s (with MockProvider)
- Poll endpoint p95 < 100ms
- Queue depth never exceeds 50
- No duplicate execution records

### 4.4 Scenario 4: Report Generation

**Objective**: Test report generation and retrieval.

**Profile**:
- 50 users viewing reports
- Mix of: list reports, get report detail, download PDF
- 25% cold cache, 75% warm cache
- 10s think time between actions

**Pass Criteria**:
- List reports p95 < 200ms
- Report detail (cached) p95 < 50ms
- Report detail (cold) p95 < 300ms
- Cache hit ratio > 60%
- No serialization errors for large reports (100KB+)

### 4.5 Scenario 5: Evaluation

**Objective**: Test evaluation framework performance.

**Profile**:
- 20 users running evaluations
- Each evaluation on a completed workflow (state size ~50KB)
- Results include scorecard, metrics, trend analysis
- 30s think time between evaluations

**Pass Criteria**:
- Evaluation execution p95 < 2s
- Scorecard generation < 500ms
- Trend computation (over 100 evaluations) < 1s
- Metric distribution computation < 2s

---

## 5. k6 Test Script

```javascript
// agentwatch_loadtest.js
// k6 run --vus 100 --duration 300s agentwatch_loadtest.js

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { randomString } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

// Custom metrics
const loginLatency = new Trend('login_latency');
const uploadLatency = new Trend('upload_latency');
const workflowLatency = new Trend('workflow_latency');
const pollLatency = new Trend('poll_latency');
const reportLatency = new Trend('report_latency');
const evalLatency = new Trend('eval_latency');
const errorRate = new Rate('errors');
const workflowSuccess = new Rate('workflow_success');
const rateLimitHits = new Counter('rate_limit_hits');

// Base URL — override with -e BASE_URL=http://staging:8000
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Shared state
let authTokens = [];
let executionIds = [];
let reportIds = [];

export const options = {
  stages: [
    { duration: '60s', target: 100 },
    { duration: '180s', target: 500 },
    { duration: '60s', target: 1000 },
    { duration: '60s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<2000'],
    http_req_failed: ['rate<0.01'],
    login_latency: ['p(95)<300'],
    upload_latency: ['p(95)<5000'],
    workflow_latency: ['p(95)<3000'],
    poll_latency: ['p(95)<200'],
    report_latency: ['p(95)<300'],
    eval_latency: ['p(95)<2000'],
    errors: ['rate<0.05'],
  },
};

export default function () {
  group('Authentication', function () {
    const email = `test_${randomString(8)}@example.com`;
    const password = 'TestPass123!';

    // Register
    let regRes = http.post(`${BASE_URL}/auth/register`, JSON.stringify({
      name: `User_${randomString(4)}`,
      email: email,
      password: password,
    }), { headers: { 'Content-Type': 'application/json' } });

    if (regRes.status === 201 || regRes.status === 409) {
      // Login
      let loginRes = http.post(`${BASE_URL}/auth/login`, JSON.stringify({
        email: email,
        password: password,
      }), { headers: { 'Content-Type': 'application/json' } });

      loginLatency.add(loginRes.timings.duration);
      check(loginRes, {
        'login successful': (r) => r.status === 200,
      });

      if (loginRes.status === 200) {
        const token = loginRes.json('access_token');
        authTokens.push(token);
        __ENV.TOKEN = token;
      } else if (loginRes.status === 429) {
        rateLimitHits.add(1);
      }
    }
    sleep(2);
  });

  const token = __ENV.TOKEN;
  if (!token) return;

  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };

  // 20% of users upload documents
  if (Math.random() < 0.2) {
    group('Document Upload', function () {
      const fileContent = randomString(1024 * 200); // 200KB
      const uploadRes = http.post(`${BASE_URL}/documents/upload`, JSON.stringify({
        filename: `report_${Date.now()}.txt`,
        content: fileContent,
        project_id: '00000000-0000-0000-0000-000000000001',
      }), { headers });

      uploadLatency.add(uploadRes.timings.duration);
      check(uploadRes, {
        'upload accepted': (r) => r.status === 200 || r.status === 202,
      });
      sleep(3);
    });
  }

  // 30% of users start workflows
  if (Math.random() < 0.3) {
    group('Workflow Execution', function () {
      const queries = [
        'Impact of AI on climate change research',
        'Advances in quantum computing 2026',
        'CRISPR gene therapy clinical trials',
        'Fintech disruption in emerging markets',
        'Neuroplasticity and learning',
      ];
      const query = queries[Math.floor(Math.random() * queries.length)];

      const wfRes = http.post(`${BASE_URL}/agents/run`, JSON.stringify({
        query: query,
        project_id: '00000000-0000-0000-0000-000000000001',
        objective: 'Research summary for executive briefing',
      }), { headers });

      workflowLatency.add(wfRes.timings.duration);
      check(wfRes, {
        'workflow accepted': (r) => r.status === 202,
      });

      if (wfRes.status === 202) {
        const execId = wfRes.json('execution_id');
        executionIds.push(execId);

        // Poll for completion
        let status = 'pending';
        let polls = 0;
        while (status !== 'completed' && status !== 'failed' && polls < 60) {
          sleep(3);
          const pollRes = http.get(`${BASE_URL}/agents/${execId}/status`, { headers });
          pollLatency.add(pollRes.timings.duration);
          if (pollRes.status === 200) {
            status = pollRes.json('execution_status') || 'unknown';
          }
          polls++;
        }
        workflowSuccess.add(status === 'completed');
      }
    });
  }

  // 40% of users fetch reports
  if (Math.random() < 0.4) {
    group('Report Access', function () {
      // List reports
      const listRes = http.get(`${BASE_URL}/reports?skip=0&limit=20`, { headers });
      reportLatency.add(listRes.timings.duration);
      check(listRes, { 'reports listed': (r) => r.status === 200 });

      if (listRes.status === 200) {
        const reports = listRes.json();
        if (reports && reports.length > 0) {
          const reportId = reports[0].id;
          const detailRes = http.get(`${BASE_URL}/reports/${reportId}`, { headers });
          reportLatency.add(detailRes.timings.duration);
        }
      }
      sleep(2);
    });
  }

  // 10% run evaluations
  if (Math.random() < 0.1) {
    group('Evaluation', function () {
      const evalRes = http.post(`${BASE_URL}/evaluation/run`, JSON.stringify({
        execution_id: executionIds.length > 0
          ? executionIds[Math.floor(Math.random() * executionIds.length)]
          : null,
        project_id: '00000000-0000-0000-0000-000000000001',
      }), { headers });

      evalLatency.add(evalRes.timings.duration);
      check(evalRes, { 'evaluation completed': (r) => r.status === 200 });
      sleep(3);
    });
  }

  // Health check (everyone, always)
  if (Math.random() < 0.1) {
    const healthRes = http.get(`${BASE_URL}/health`);
    check(healthRes, { 'health ok': (r) => r.status === 200 });
  }

  sleep(1);
}

export function teardown(data) {
  console.log(`Auth tokens generated: ${authTokens.length}`);
  console.log(`Workflows started: ${executionIds.length}`);
  console.log(`Rate limit hits: ${rateLimitHits.name}`);
}
```

---

## 6. Locust Test Script

```python
"""agentwatch_loadtest.py
Run: locust -f agentwatch_loadtest.py --host http://localhost:8000 --headless -u 500 -r 50 -t 5m
"""

import random
import string
import uuid

from locust import HttpUser, task, between, events
from locust.env import Environment


AGENT_NAMES = [
    "PlannerAgent", "RetrievalAgent", "SummarizerAgent",
    "GapDetectionAgent", "ReportGeneratorAgent",
]

RESEARCH_QUERIES = [
    "Impact of AI on climate change research",
    "Advances in quantum computing 2026",
    "CRISPR gene therapy clinical trials",
    "Fintech disruption in emerging markets",
    "Neuroplasticity and learning",
    "Blockchain in supply chain management",
    "Edge computing architecture trends",
    "Hydrogen fuel cell vehicles 2026",
    "Personalized medicine and genomics",
    "Autonomous vehicle regulations",
]


class AgentWatchUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.token = None
        self.user_id = None
        self.execution_ids = []
        self._register_and_login()

    def _random_string(self, length=8):
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def _headers(self):
        if self.token:
            return {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            }
        return {"Content-Type": "application/json"}

    def _register_and_login(self):
        email = f"loadtest_{self._random_string()}@example.com"
        password = "TestPass123!"

        # Register (ignore 409 — user may exist from prior run)
        with self.client.post(
            "/auth/register",
            json={"name": f"User_{self._random_string(4)}", "email": email, "password": password},
            catch_response=True,
        ) as resp:
            if resp.status_code == 409:
                resp.success()

        # Login
        with self.client.post(
            "/auth/login",
            json={"email": email, "password": password},
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                self.token = resp.json().get("access_token")
                self.user_id = resp.json().get("user_id")
                resp.success()
            elif resp.status_code == 429:
                resp.failure("Rate limited during login")
            else:
                resp.failure(f"Login failed: {resp.status_code}")

    @task(3)
    def health_check(self):
        self.client.get("/health", name="health")

    @task(10)
    def list_projects(self):
        self.client.get("/projects?skip=0&limit=20", headers=self._headers(), name="list_projects")

    @task(5)
    def list_sessions(self):
        self.client.get("/sessions?skip=0&limit=20", headers=self._headers(), name="list_sessions")

    @task(3)
    def list_reports(self):
        self.client.get("/reports?skip=0&limit=20", headers=self._headers(), name="list_reports")

    @task(2)
    def upload_document(self):
        content = self._random_string(1024 * 500)  # 500KB
        with self.client.post(
            "/documents/upload",
            json={
                "filename": f"report_{int(random.random() * 1e9)}.txt",
                "content": content,
                "project_id": str(uuid.uuid4()),
            },
            headers=self._headers(),
            name="upload_document",
            catch_response=True,
        ) as resp:
            if resp.status_code == 429:
                resp.failure("Rate limited during upload")
            elif resp.status_code >= 500:
                resp.failure(f"Upload failed: {resp.status_code}")
            else:
                resp.success()

    @task(2)
    def start_workflow(self):
        query = random.choice(RESEARCH_QUERIES)
        with self.client.post(
            "/agents/run",
            json={
                "query": query,
                "project_id": str(uuid.uuid4()),
                "objective": "Load test research query",
            },
            headers=self._headers(),
            name="start_workflow",
            catch_response=True,
        ) as resp:
            if resp.status_code == 202:
                exec_id = resp.json().get("execution_id")
                if exec_id:
                    self.execution_ids.append(exec_id)
                resp.success()
            elif resp.status_code == 429:
                resp.failure("Rate limited during workflow start")
            else:
                resp.failure(f"Workflow start failed: {resp.status_code}")

    @task(8)
    def poll_workflow_status(self):
        if not self.execution_ids:
            return
        exec_id = random.choice(self.execution_ids)
        with self.client.get(
            f"/agents/{exec_id}/status",
            headers=self._headers(),
            name="poll_workflow_status",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                status = resp.json().get("execution_status", "unknown")
                if status == "failed":
                    resp.failure(f"Workflow {exec_id} failed")
                else:
                    resp.success()
            else:
                resp.failure(f"Status poll failed: {resp.status_code}")

    @task(1)
    def run_evaluation(self):
        if not self.execution_ids:
            return
        exec_id = random.choice(self.execution_ids)
        with self.client.post(
            "/evaluation/run",
            json={
                "execution_id": exec_id,
                "project_id": str(uuid.uuid4()),
            },
            headers=self._headers(),
            name="run_evaluation",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Evaluation failed: {resp.status_code}")

    @task(1)
    def list_agents(self):
        self.client.get("/agents", headers=self._headers(), name="list_agents")

    @task(1)
    def get_human_approval(self):
        self.client.get("/human-approval/pending", headers=self._headers(), name="human_approval")


@events.init.add_listener
def on_locust_init(environment: Environment, **kwargs):
    print(f"AgentWatch load test initialized")
    print(f"Target: {environment.host}")
    print(f"User classes: {[c.__name__ for c in environment.user_classes]}")
```

---

## 7. Infrastructure Sizing

### 7.1 100 Concurrent Users

| Component | Spec | Count | Total vCPU | Total RAM | Est. Monthly Cost |
|-----------|------|-------|-----------|-----------|-------------------|
| API (FastAPI) | t3.medium (2 vCPU, 4 GB) | 1 | 2 | 4 GB | ~$30 |
| Worker (Dramatiq) | t3.medium (2 vCPU, 4 GB) | 1 | 2 | 4 GB | ~$30 |
| PostgreSQL | db.t3.small (2 vCPU, 2 GB) | 1 | 2 | 2 GB | ~$25 |
| Redis | cache.t3.micro (1 vCPU, 0.5 GB) | 1 | 1 | 0.5 GB | ~$15 |
| ChromaDB | t3.small (2 vCPU, 2 GB) | 1 | 2 | 2 GB | ~$20 |
| Load Balancer | ALB | 1 | — | — | ~$20 |
| **Total** | | **6** | **9** | **12.5 GB** | **~$140/mo** |

### 7.2 500 Concurrent Users

| Component | Spec | Count | Total vCPU | Total RAM | Est. Monthly Cost |
|-----------|------|-------|-----------|-----------|-------------------|
| API (FastAPI) | t3.large (2 vCPU, 8 GB) | 2 | 4 | 16 GB | ~$120 |
| Worker (Dramatiq) | t3.large (2 vCPU, 8 GB) | 2 | 4 | 16 GB | ~$120 |
| PostgreSQL | db.t3.medium (2 vCPU, 4 GB) | 1 | 2 | 4 GB | ~$50 |
| PostgreSQL replica | db.t3.small (2 vCPU, 2 GB) | 1 | 2 | 2 GB | ~$25 |
| Redis | cache.t3.small (1 vCPU, 1.3 GB) | 1 | 1 | 1.3 GB | ~$25 |
| ChromaDB | t3.medium (2 vCPU, 4 GB) | 1 | 2 | 4 GB | ~$40 |
| Load Balancer | ALB | 1 | — | — | ~$25 |
| **Total** | | **9** | **15** | **43.3 GB** | **~$405/mo** |

### 7.3 1000 Concurrent Users

| Component | Spec | Count | Total vCPU | Total RAM | Est. Monthly Cost |
|-----------|------|-------|-----------|-----------|-------------------|
| API (FastAPI) | c6i.large (2 vCPU, 4 GB) | 4 | 8 | 16 GB | ~$280 |
| Worker (Dramatiq) | c6i.large (2 vCPU, 4 GB) | 4 | 8 | 16 GB | ~$280 |
| PostgreSQL | db.r6g.large (2 vCPU, 16 GB) | 1 | 2 | 16 GB | ~$175 |
| PostgreSQL replica | db.t3.medium (2 vCPU, 4 GB) | 2 | 4 | 8 GB | ~$100 |
| Redis Cluster | cache.r6g.large (2 vCPU, 13 GB) | 1 | 2 | 13 GB | ~$130 |
| ChromaDB | c6i.xlarge (4 vCPU, 8 GB) | 1 | 4 | 8 GB | ~$140 |
| Load Balancer | ALB | 1 | — | — | ~$30 |
| **Total** | | **14** | **28** | **77 GB** | **~$1,135/mo** |

---

## 8. Bottleneck Analysis

### 8.1 Expected Bottlenecks and Impact

| Bottleneck | Trigger | Symptom | Impact | Mitigation |
|-----------|---------|---------|--------|------------|
| **LLM API Rate Limits** | >50 workflow starts/min | 429 from LLM provider, stalled workflows | Workflow p99 latency spikes to 5-10min | Queue throttling, tiered API keys, circuit breaker |
| **DB Connection Pool** | >80 concurrent DB calls | `AsyncpgPoolExhaustedError`, 503s | All write operations fail | Increase pool size, add PgBouncer, read replicas |
| **Redis Throughput** | >5000 ops/s | Command timeouts, queue lag | Rate limiting disabled, workflow queue delayed | Redis Cluster, pipeline commands, reduce TTL |
| **ChromaDB Single Node** | >100 QPS | Query timeouts, embedding failures | Retrieval agent fails, workflows stall | Vertical scale, implement query caching, add ChromaDB workers |
| **Worker Starvation** | All workers busy | Queue depth grows, workflows queued | Workflow start-to-completion latency increases linearly | Auto-scaling worker group, priority queues |
| **Memory (API)** | Large response payloads | OOM kills, connection drops | All API endpoints fail | Response streaming, pagination, increase container memory |
| **Disk I/O (ChromaDB)** | Frequent collection writes | Slow queries, write contention | Document indexing slows down | Use SSDs, separate data volume, batch writes |

### 8.2 Worst-Case Analysis

Under a sustained burst of 1000 concurrent users with the current architecture:

1. **Phase 1 (0-30s)**: API responds normally. 20-30 workflows enqueued. DB pool at 60%.
2. **Phase 2 (30-120s)**: 80+ workflows in queue. Workers saturated (16 threads). DB pool near 90%.
3. **Phase 3 (120-300s)**: DB pool exhausted. Rate limiter log entries spike. ChromaDB query latency doubles. LLM provider rate limits hit.
4. **Phase 4 (300s+)**: Errors cascade — workers retry, DB queries queue, heap pressure on API containers. Error rate exceeds 5%.

**Probability of cascading failure**: Medium (requires sustained burst > 300 users simultaneous).

---

## 9. Scaling Recommendations

### 9.1 Immediate (Before Production)

| # | Action | Effort | Impact | Owner |
|---|--------|--------|--------|-------|
| S1 | Increase DB pool size from 10 to 30-50 | Low | High | Backend |
| S2 | Add PgBouncer connection pooler | Medium | High | DevOps |
| S3 | Configure horizontal pod autoscaling (HPA) for API | Medium | High | DevOps |
| S4 | Enable Redis Cluster mode | Medium | High | DevOps |
| S5 | Implement LLM provider circuit breaker | Medium | High | Backend |
| S6 | Add DB query timeout (statement_timeout=30s) | Low | High | Backend |
| S7 | Implement response caching for report detail | Low | Medium | Backend |
| S8 | Configure worker auto-scaling (queue depth trigger) | Medium | High | DevOps |

### 9.2 Short-term (Within 30 Days)

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| S9 | Add PostgreSQL read replicas for query endpoints | High | High |
| S10 | Implement ChromaDB read replicas or HA cluster | High | High |
| S11 | Deploy API behind CloudFront CDN for static/metadata | Medium | Medium |
| S12 | Implement query result caching layer (Redis) | Medium | High |
| S13 | Add batch ingestion API for bulk document upload | Medium | Medium |
| S14 | Implement priority queues (premium vs standard) | Medium | Medium |
| S15 | Add request coalescing for duplicate workflow queries | Medium | Medium |

### 9.3 Long-term (90 Days)

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| S16 | Migrate ChromaDB to Pinecone/Weaviate for horizontal scale | High | High |
| S17 | Implement event-driven architecture (Kafka/SQS) | High | High |
| S18 | Multi-region active-active deployment | Very High | High |
| S19 | GPU-accelerated embedding inference server | High | Medium |
| S20 | Custom LLM fine-tuning for common research domains | Very High | Medium |

### 9.4 Horizontal vs Vertical Scaling Strategy

```
Horizontal (preferred for API + Workers):
  FastAPI:   Add replicas behind ALB → stateless, trivial
  Workers:   Add Dramatiq worker processes → queue-based, trivial
  PostgreSQL: Read replicas → application must route reads
  Redis:     Redis Cluster with sharding → connection logic update

Vertical (required for ChromaDB + PostgreSQL write):
  ChromaDB:  Increase instance size (c6i.xlarge → c6i.2xlarge)
  PostgreSQL: Increase instance size + provisioned IOPS
```

---

## Appendix A: Test Data Requirements

| Data Type | Quantity | Size |
|-----------|----------|------|
| User accounts | 1000 | ~1 KB each |
| Projects | 200 | ~500 bytes each |
| Documents | 5000 | 100 KB - 5 MB each |
| Chunks (in ChromaDB) | 500,000 | ~1 KB each |
| Workflow executions | 1000 | ~50 KB each |
| Reports | 500 | 10 - 100 KB each |
| Evaluations | 1000 | ~5 KB each |

## Appendix B: Monitoring During Load Tests

| Metric | Prometheus Query | Alert Threshold |
|--------|-----------------|-----------------|
| Error rate | `rate(http_requests_total{status=~"5xx"}[5m]) / rate(http_requests_total[5m])` | > 0.01 |
| p99 latency | `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))` | > 2s |
| Queue depth | `queue_depth{queue_name="workflows"}` | > 100 |
| DB pool usage | `pg_stat_activity_count` | > 80 |
| Active workflows | `active_workflows` | > 50 |
| Redis command rate | `rate(redis_commands_total[1m])` | > 5000 |
