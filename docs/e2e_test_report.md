# End-to-End Test Report

## Current State

371 unit + integration tests exist across 13 test files. These cover individual components in isolation with mocked dependencies. No true end-to-end workflow tests exist.

## What End-to-End Tests Would Validate

A proper E2E test would:

1. **Create a user** via `POST /auth/register`
2. **Login** via `POST /auth/login` → get JWT
3. **Create a project** via `POST /projects` → get project ID
4. **Upload a document** via `POST /documents/upload`
5. **Run the research workflow** via `POST /agents/run`
6. **Poll for agent completion** via `GET /agents/{id}`
7. **Generate a report** via `POST /reports/generate`
8. **Export the report** via `POST /reports/export`
9. **Verify citations** in the generated report

## E2E Test Script

```python
"""Placeholder for true end-to-end workflow tests.

Requirements to run:
- PostgreSQL running with migrated schema
- ChromaDB running
- Redis running (optional)
- SECRET_KEY env var set

Usage:
    pytest tests/test_e2e_workflow.py -v
"""

import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_full_research_workflow(client: AsyncClient) -> None:
    """User creates project, runs agents, generates report."""
    # 1. Register
    email = f"e2e_{uuid.uuid4().hex[:8]}@test.com"
    register_res = await client.post("/auth/register", json={
        "name": "E2E Tester",
        "email": email,
        "password": "E2eTest123!",
    })
    assert register_res.status_code == 201
    token = register_res.json().get("access_token")

    # 2. Login
    login_res = await client.post("/auth/login", json={
        "email": email,
        "password": "E2eTest123!",
    })
    assert login_res.status_code == 200

    # 3. Create project
    headers = {"Authorization": f"Bearer {token}"}
    project_res = await client.post("/projects", json={
        "title": "E2E Test: AI Ethics",
        "description": "Testing the full research workflow",
    }, headers=headers)
    assert project_res.status_code == 200
    project_id = project_res.json().get("id")

    # 4. Run research workflow
    run_res = await client.post("/agents/run", json={
        "query": "Ethical considerations in AI transparency",
        "project_id": project_id,
        "objective": "Test end-to-end workflow",
    }, headers=headers)
    assert run_res.status_code == 200

    # 5. Generate report
    report_res = await client.post("/reports/generate", json={
        "query": "AI Ethics",
        "planner_output": None,
        "summaries": [],
        "research_gaps": [],
    }, headers=headers)
    assert report_res.status_code == 200
    report = report_res.json()
    assert len(report.get("sections", [])) > 0


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_report_export_workflow(client: AsyncClient) -> None:
    """Generate report and export in supported formats."""
    headers = {"Authorization": "Bearer test"}

    # Generate a report first
    report_res = await client.post("/reports/generate", json={
        "query": "Machine Learning in Healthcare",
        "planner_output": json.dumps({
            "research_goal": "Test goal",
            "research_questions": ["Q1?", "Q2?", "Q3?"],
            "keywords": ["ML", "healthcare", "AI"],
            "search_queries": ["ML healthcare"],
            "subtopics": ["Sub1", "Sub2", "Sub3"],
            "methodology": "literature review",
            "expected_deliverables": ["Report"],
            "priority_areas": ["Area 1"],
            "risk_areas": [],
            "estimated_steps": 3,
        }),
        "summaries": [],
        "research_gaps": [],
    }, headers=headers)
    assert report_res.status_code == 200

    # Export in markdown format
    export_res = await client.post("/reports/export", json={
        "report": report_res.json(),
        "format": "markdown",
    }, headers=headers)
    assert export_res.status_code == 200
    export_data = export_res.json()
    assert "content" in export_data


# Note: These tests are marked @pytest.mark.e2e so they can be excluded
# from the default test run. Run with:
#   pytest -m e2e tests/test_e2e_workflow.py -v
```

## Challenges Running E2E Tests

| Challenge | Impact | Workaround |
|-----------|--------|------------|
| PostgreSQL required | Tests fail without live DB | Use testcontainers or CI service |
| ChromaDB required | Vector search fails | Fall back to simulated results |
| Redis optional | Rate limiting disabled | Graceful degradation works |
| JWT token rotation | Must handle refresh in tests | Use short-lived test tokens |
| Agent execution async | Must poll for completion | Add polling loop with timeout |
