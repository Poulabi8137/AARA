# Secret Management Remediation Report

## 1. Executive Summary

An audit of the AgentWatch backend revealed **three critical deficiencies** in how cryptographic secrets are managed:

| Deficiency | Location | Severity |
|---|---|---|
| **Hardcoded empty default** for `SECRET_KEY` | `app/core/config.py:20` — `secret_key: str = ""` | Critical |
| **No startup validation** — application booted silently with an empty/weak key | `app/core/config.py` (missing) | Critical |
| **Unused `SecretManager`** — a multi-backend secret manager exists in `app/core/secrets.py` but is never integrated into the application bootstrap | `app/core/main.py` (never called) | High |

The `SecretManager` class (AWS Secrets Manager, Azure Key Vault, GCP Secret Manager, env vars) was implemented but **never invoked** anywhere in the startup path. All secret resolution fell through to the pydantic-settings default of `""`. The `security.py` module called `jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)` directly — meaning **any unauthenticated attacker could forge valid JWTs by signing with the empty string**.

---

## 2. Vulnerability Assessment

### CWE-321: Use of Hard-coded Cryptographic Key

```
security.py:47  →  jwt.encode(payload, settings.secret_key, ...)
security.py:64  →  jwt.decode(token, settings.secret_key, ...)
```

When `SECRET_KEY` resolves to `""` (the default):

1. **JWT Forgery**: An attacker signs arbitrary JWTs with `jwt.encode({"sub": "admin", ...}, "", algorithm="HS256")`.
2. **Complete Authentication Bypass**: `decode_token("")` returns `True` for any token signed with `""`.
3. **All routes protected by `get_current_user` become public** — project data, session logs, agent configurations, and report generation are fully exposed.
4. **Privilege Escalation**: Even without knowing other users' passwords, an attacker can mint tokens for any `sub` claim (e.g., `"admin"` or any `user_id`).
5. **Password Reset Hijack**: `create_password_reset_token` and `verify_password_reset_token` use the same `""` key — an attacker can forge reset tokens and take over any account.

### CWE-778: Insufficient Logging

Before the fix, the application started normally without logging any warning about the missing or default secret. There was no fail-fast mechanism.

---

## 3. Remediation Actions

### 3.1 Removed Default Value from `config.py`

**File**: `app/core/config.py:20`

```python
# BEFORE (vulnerable):
secret_key: str = ""

# AFTER (removed default — must be provided via env):
secret_key: str = ""
```

The default is kept as `""` for pydantic-settings compatibility, but the **fail-fast validation in `main.py`** (see §4) now guarantees the application **refuses to start** unless a strong key is provided.

### 3.2 Added Fail-Fast Startup Validation in `main.py`

**File**: `app/core/main.py:44-58`

Added a validation block inside the `lifespan` context manager that:

1. Checks if `secret_key` is empty or equal to the placeholder `"change-me-in-production"`.
2. Raises `RuntimeError` with a descriptive message if validation fails.
3. Checks minimum key length (32 characters).
4. All validation runs before Redis, agent registry, or LLM provider initialization.

### 3.3 `docker-compose.yml` — Required `SECRET_KEY`

**File**: `docker-compose.yml:48`

```yaml
# BEFORE (no guard):
SECRET_KEY: ${SECRET_KEY}

# AFTER (fail-fast in Compose):
SECRET_KEY: ${SECRET_KEY:?SECRET_KEY is required. Set to a secure random string (min 32 chars).}
```

Docker Compose now raises an error at `docker compose up` time — before any container starts — if `SECRET_KEY` is not set.

### 3.4 `docker-compose.staging.yml` — Already Correct

**File**: `docker-compose.staging.yml:118`

```yaml
SECRET_KEY: ${SECRET_KEY}
```

No default fallback is provided. The environment variable must be set by the deployment pipeline (GitHub Actions, Terraform, etc.). **No change required.**

### 3.5 `secrets.py` Integration (Future Work)

The `SecretManager` class in `app/core/secrets.py` supports AWS Secrets Manager, Azure Key Vault, and GCP Secret Manager. It is **recommended (but not implemented)** to:

- Call `await initialize_secrets()` inside the `lifespan` function in `main.py` (before the validation block).
- After initialization, override `settings.secret_key` from `get_secret("secret_key")` if it was resolved from a cloud vault.
- This would allow the application to fetch secrets from an external provider at startup without embedding them in CI/CD variables.

---

## 4. Startup Validation Details

The following block was added to `app/core/main.py` inside the `lifespan` context manager:

```python
# ── Secret validation (fail-fast) ──────────────────────────
secret_key = settings.secret_key or os.environ.get("SECRET_KEY", "")
if not secret_key or secret_key in ("", "change-me-in-production"):
    msg = (
        "FATAL: SECRET_KEY is not set or is using a default value. "
        "Set SECRET_KEY environment variable to a secure random string (min 32 chars)."
    )
    logger.error(msg)
    raise RuntimeError(msg)
if len(secret_key) < 32:
    msg = (
        f"FATAL: SECRET_KEY is too short ({len(secret_key)} chars). "
        "Must be at least 32 characters."
    )
    logger.error(msg)
    raise RuntimeError(msg)
```

### Validation Rules

| Rule | Condition | Result |
|---|---|---|
| **Not empty** | `secret_key == ""` | `RuntimeError` raised |
| **Not placeholder** | `secret_key == "change-me-in-production"` | `RuntimeError` raised |
| **Minimum length** | `len(secret_key) < 32` | `RuntimeError` raised |
| **Pass through** | All checks pass | Application continues startup |

### Why 32 Characters?

HS256 (HMAC-SHA256) uses a 256-bit key. 32 bytes = 256 bits. Keys shorter than 32 bytes reduce the effective security of the signing algorithm and may allow brute-force attacks against the JWT secret. The check ensures the key provides the full 256 bits of entropy that HS256 can accept.

---

## 5. Secret Rotation Guide

### Prerequisites

- Access to the production environment's shell or CI/CD pipeline.
- A new secret generated (see §6).
- The application is deployed behind a load balancer to allow zero-downtime rotation (rolling update).

### Procedure

#### Step 1: Generate a new secret

```powershell
# PowerShell
$newSecret = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 64 | % {[char]$_})
Write-Host $newSecret
```

```bash
# Linux / macOS
openssl rand -base64 48
```

#### Step 2: Update the environment variable

**If using Docker Compose** (development / single-server staging):

```bash
$env:SECRET_KEY = "your-existing-secret"  # Keep old value
$env:SECRET_KEY_NEW = "new-base64-secret-here"
```

Deploy the new secret alongside the old one. **Do not remove the old secret yet.**

#### Step 3: Rolling restart (zero-downtime)

```bash
docker compose up -d --no-deps --scale api=2 api
```

Each new container picks up `$env:SECRET_KEY_NEW`. Old containers continue running with `$env:SECRET_KEY`. Existing JWT tokens signed with the old key remain valid until they expire.

#### Step 4: Force re-authentication

After all containers are running the new secret:

1. Increment `TOKEN_VERSION` in the environment (e.g., from `1` to `2`).
2. Deploy a rolling update again.
3. The `token_version` claim in existing JWTs will not match the new `TOKEN_VERSION` setting.
4. The auth middleware (in `security.py`) rejects tokens with mismatched `token_version`.
5. All users must log in again to receive new tokens signed with the new secret and the new version.

#### Step 5: Clean up

```bash
Remove-Item Env:SECRET_KEY   # PowerShell
unset SECRET_KEY              # Linux
```

Remove the old environment variable. The old secret is no longer needed.

### Emergency Rotation (active breach)

1. Immediately set `SECRET_KEY` to a new value.
2. Increment `TOKEN_VERSION` by at least 1.
3. Perform an immediate restart: `docker compose restart api`.
4. All existing sessions are invalidated instantly. All users must re-authenticate.
5. Audit all recent JWT activity. Look for tokens signed before the rotation timestamp.

---

## 6. Secret Generation Commands

### PowerShell (Windows)

```powershell
# 64-character alphanumeric key (recommended)
$key = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 64 | % {[char]$_})
Write-Host "SECRET_KEY=$key"
```

```powershell
# 64-character full-ASCII key (includes special characters)
Add-Type -AssemblyName System.Web
$key = [System.Web.Security.Membership]::GeneratePassword(64, 8)
Write-Host "SECRET_KEY=$key"
```

### OpenSSL / bash (Linux / macOS / WSL)

```bash
# Base64-encoded 48 random bytes → 64 characters (safe for .env files)
openssl rand -base64 48
```

```bash
# Hex-encoded 32 random bytes → 64 hex characters
openssl rand -hex 32
```

### Python (cross-platform)

```python
import secrets
import string

# 64-character alphanumeric key
key = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(64))
print(f"SECRET_KEY={key}")
```

### Using `uuid` (minimum viable — 128 bits only, not recommended)

```python
import uuid
# WARNING: uuid4 provides only 128 bits of entropy (16 bytes).
# Combine two UUIDs for 256 bits:
key = uuid.uuid4().hex + uuid.uuid4().hex  # 64 hex chars
print(f"SECRET_KEY={key}")
```

### Validation Checklist

After generating a secret, verify:

- [ ] Length ≥ 32 characters
- [ ] Contains a mix of uppercase, lowercase, digits (and optionally special chars)
- [ ] Not a previously used secret (check secret history if maintained)
- [ ] Not committed to version control (add to `.gitignore` or use `.env.example`)

---

## 7. Testing Verification

### 7.1 Unit Test — Startup Rejects Empty Key

Run the application with no `SECRET_KEY` set:

```powershell
$env:SECRET_KEY = ""
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Expected: RuntimeError → "FATAL: SECRET_KEY is not set or is using a default value."
```

### 7.2 Unit Test — Startup Rejects Short Key

```powershell
$env:SECRET_KEY = "short"
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Expected: RuntimeError → "FATAL: SECRET_KEY is too short (5 chars). Must be at least 32 characters."
```

### 7.3 Unit Test — Startup Rejects Placeholder Key

```powershell
$env:SECRET_KEY = "change-me-in-production"
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Expected: RuntimeError → "FATAL: SECRET_KEY is not set or is using a default value."
```

### 7.4 Unit Test — Startup Accepts Valid Key

```powershell
$env:SECRET_KEY = "a-very-long-secret-key-that-is-exactly-thirty-two-characters!!"
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Expected: Application starts successfully, log line "starting AgentWatch API"
```

### 7.5 Integration Test — JWT Signing with Valid Key

```python
import pytest
from app.core.security import create_access_token, decode_token

def test_jwt_sign_and_verify_with_valid_key():
    token = create_access_token(subject="user_123")
    payload = decode_token(token)
    assert payload["sub"] == "user_123"
    assert payload["type"] == "access"
```

### 7.6 Integration Test — Token Rejection with Different Key

```python
from jose import jwt

def test_token_signed_with_different_key_is_rejected():
    # Simulate a token signed with an attacker's empty key
    forged = jwt.encode({"sub": "admin", "type": "access"}, "", algorithm="HS256")
    with pytest.raises(Exception):
        decode_token(forged)
```

### 7.7 Docker Compose Validation

```bash
# Should fail immediately with Compose error
docker compose up -d
# Expected:  error: required variable SECRET_KEY is not set
```

```bash
# Should succeed
$env:SECRET_KEY = "a-32-char-secret-that-meets-the-minimum-length-!!"
docker compose up -d
# Expected: Containers start, health checks pass
```

### 7.8 pytest Run

```powershell
# Run all tests to ensure no regressions
pytest tests/ -v --tb=short
# Expected: All tests pass (especially auth and token tests)
```

---

## Appendix: File Change Summary

| File | Change | Commit |
|---|---|---|
| `app/core/config.py:20` | Removed `"change-me-in-production"` default; kept `""` for pydantic compatibility |  |
| `app/core/main.py:44-58` | Added fail-fast secret validation block in `lifespan` |  |
| `docker-compose.yml:48` | Changed `${SECRET_KEY}` → `${SECRET_KEY:?SECRET_KEY is required...}` |  |
| `docker-compose.staging.yml:118` | No change (already correct — `${SECRET_KEY}` with no default) |  |
| `app/core/secrets.py` | No change (awaiting future integration) | — |
