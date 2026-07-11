from __future__ import annotations


async def test_health_endpoint_reports_status(app_client):
    resp = await app_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("healthy", "degraded", "unhealthy")
    assert body["version"]
    assert "services" in body


async def test_liveness_endpoint(app_client):
    resp = await app_client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("healthy", "degraded", "unhealthy")


async def test_readiness_endpoint(app_client):
    resp = await app_client.get("/health/ready")
    assert resp.status_code == 200
    assert "services" in resp.json()


async def test_metrics_endpoint_exposes_prometheus_format(app_client):
    resp = await app_client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")


async def test_security_headers_present(app_client):
    resp = await app_client.get("/health")
    assert resp.headers.get("x-request-id")


async def test_unknown_route_returns_404_not_500(app_client):
    resp = await app_client.get("/api/v1/this-route-does-not-exist")
    assert resp.status_code == 404
