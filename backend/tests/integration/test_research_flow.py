from __future__ import annotations

import pytest


@pytest.fixture
async def auth_headers(app_client):
    payload = {
        "email": "researcher@example.com",
        "password": "StrongP@ssw0rd1",
        "display_name": "Researcher",
    }
    resp = await app_client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_workspace_project_session_creation_flow(app_client, auth_headers):
    workspace_resp = await app_client.post(
        "/api/v1/workspaces",
        json={"name": "AI Safety Research", "description": "Investigating alignment"},
        headers=auth_headers,
    )
    assert workspace_resp.status_code == 201
    workspace = workspace_resp.json()
    assert workspace["name"] == "AI Safety Research"

    project_resp = await app_client.post(
        "/api/v1/projects",
        json={
            "workspace_id": workspace["id"],
            "name": "Literature Review",
            "research_goal": "Survey recent alignment papers",
        },
        headers=auth_headers,
    )
    assert project_resp.status_code == 201
    project = project_resp.json()
    assert project["workspace_id"] == workspace["id"]

    session_resp = await app_client.get(
        "/api/v1/research/sessions",
        headers=auth_headers,
    )
    assert session_resp.status_code == 200
    assert session_resp.json()["items"] == []


async def test_workspace_requires_authentication(app_client):
    resp = await app_client.post(
        "/api/v1/workspaces",
        json={"name": "No Auth Workspace"},
    )
    assert resp.status_code in (401, 403)


async def test_dashboard_stats_no_500_for_authenticated_user_with_no_activity(app_client, auth_headers):
    resp = await app_client.get("/api/v1/dashboard/stats", headers=auth_headers)
    # No workflow activity yet for this fresh user -> 404, not a 500.
    assert resp.status_code in (200, 404)
