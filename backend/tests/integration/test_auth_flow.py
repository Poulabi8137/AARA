from __future__ import annotations


async def test_register_login_me_flow(app_client):
    register_payload = {
        "email": "integration-user@example.com",
        "password": "StrongP@ssw0rd1",
        "display_name": "Integration User",
    }

    register_resp = await app_client.post("/api/v1/auth/register", json=register_payload)
    assert register_resp.status_code == 201
    tokens = register_resp.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"

    me_resp = await app_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == register_payload["email"]

    login_resp = await app_client.post(
        "/api/v1/auth/login",
        json={"email": register_payload["email"], "password": register_payload["password"]},
    )
    assert login_resp.status_code == 200
    login_tokens = login_resp.json()
    assert login_tokens["access_token"]

    refresh_resp = await app_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_tokens["refresh_token"]},
    )
    assert refresh_resp.status_code == 200
    assert refresh_resp.json()["access_token"]

    logout_resp = await app_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {login_tokens['access_token']}"},
    )
    assert logout_resp.status_code == 204


async def test_register_duplicate_email_rejected(app_client):
    payload = {
        "email": "dup@example.com",
        "password": "StrongP@ssw0rd1",
        "display_name": "Dup User",
    }
    first = await app_client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = await app_client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


async def test_login_wrong_password_rejected(app_client):
    payload = {
        "email": "wrongpw@example.com",
        "password": "StrongP@ssw0rd1",
        "display_name": "Wrong PW User",
    }
    reg = await app_client.post("/api/v1/auth/register", json=payload)
    assert reg.status_code == 201

    bad_login = await app_client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": "not-the-password"},
    )
    assert bad_login.status_code == 401


async def test_me_requires_authentication(app_client):
    resp = await app_client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)


async def test_forgot_password_returns_generic_message_for_unknown_email(app_client):
    resp = await app_client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "no-such-user@example.com"},
    )
    # Must not leak whether the account exists.
    assert resp.status_code == 200
    assert "message" in resp.json()


async def test_register_rejects_weak_password(app_client):
    resp = await app_client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "weak", "display_name": "Weak"},
    )
    assert resp.status_code == 422
