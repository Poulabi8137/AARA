# AgentWatch Security Audit (OWASP Top 10 - 2021)

**Audit Date:** 2026-06-13
**Scope:** Backend API (`app/` directory)
**Classification:** Internal — Confidential

---

## A01:2021 – Broken Access Control

### [CRITICAL] Missing Authorization on All Private Endpoints
- **Location:** `app/api/projects.py`, `app/api/sessions.py`, `app/api/reports.py`, `app/api/documents.py`, `app/api/agents.py`, `app/api/evaluation.py`
- **Risk:** Most API routes lack explicit authorization checks verifying the authenticated user owns or has permission to access the requested resource. An authenticated user can enumerate or access other users' projects, sessions, documents, and reports by changing IDs in the URL path.
- **Impact:** Horizontal privilege escalation — any authenticated user can read, modify, or delete arbitrary resources belonging to other tenants. Complete data breach of all projects, sessions, reports, and agent configurations.
- **Remediation:** Implement a reusable dependency (`get_owned_project`, `get_owned_session`, etc.) that cross-references `request.user.id` with the resource owner in every handler that accepts a resource ID parameter. Apply the principle of least privilege and test with negative scenarios (attempting access to another user's resource).
- **Priority:** P0

### [CRITICAL] No Role-Based Access Control (RBAC)
- **Location:** `app/api/auth.py`, `app/models/user.py`
- **Risk:** The User model and auth system do not define roles (admin, viewer, editor, etc.). Every authenticated user has implicit full access to all features.
- **Impact:** No segregation of duties. A compromised low-privilege token (e.g., a read-only API key) can delete agents, modify governance policies, and access billing data.
- **Remediation:** Add a `role` field to the User/Session model. Create an RBAC dependency (`require_role("admin")`). Audit all endpoints and assign minimum required roles. Reject requests lacking the required role with 403 Forbidden.
- **Priority:** P0

### [HIGH] IDOR in Debug Routes
- **Location:** `app/api/retrieval_debug.py`, `app/api/summarizer_debug.py`, `app/api/gap_debug.py`
- **Risk:** Debug endpoints accept session/project IDs without ownership verification. These endpoints may expose full internal state, raw LLM prompts, and retrieval context.
- **Impact:** Information disclosure — internal prompt structures, RAG chunk contents, and gap analysis internals leaked to unauthorized users.
- **Remediation:** Apply the same ownership verification dependency used in production endpoints. Remove or gate debug routes behind a feature flag / admin-only role in production deployments.
- **Priority:** P1

### [HIGH] Admin Endpoints Without Admin Checks
- **Location:** Any route that performs system-level operations
- **Risk:** No mechanism exists to designate admin users or protect admin-only functionality.
- **Impact:** Any registered user can potentially access system administration functions if exposed.
- **Remediation:** Introduce an `is_admin` boolean or `role` field. Create an `admin_required` dependency. Audit all routes and classify them as user-facing vs. admin-only.
- **Priority:** P1

---

## A02:2021 – Cryptographic Failures

### [CRITICAL] Hardcoded Secret Key
- **Location:** `app/core/config.py:20`
- **Risk:** Secret key hardcoded with default value `"change-me-in-production"`. If a production deployment does not override this via environment variable, the JWT signing key is identical to every other default deployment.
- **Impact:** Complete JWT forgery — an attacker can craft arbitrary valid access and refresh tokens, leading to full account takeover, privilege escalation, and data access for every user in the system.
- **Remediation:** Move to a strong auto-generated default only for local development. In production, require `SECRET_KEY` via environment variable with a validation check at startup that rejects weak or default keys. Generate via `openssl rand -hex 32` or equivalent.
- **Priority:** P0

### [HIGH] Weak JWT Algorithm (HS256 with Short Key)
- **Location:** `app/core/config.py:23`, `app/core/security.py`
- **Risk:** HS256 is a symmetric algorithm. If the secret key is compromised (see above), the entire auth system is compromised. Additionally, no validation restricts the algorithm — an attacker could change the JWT header algorithm to `none` and bypass verification entirely if the library does not enforce algorithm whitelisting.
- **Impact:** JWT signature bypass, token forgery, session hijacking.
- **Remediation:** (1) Enforce algorithm whitelist — only accept `HS256`. (2) Use `jose.jwt.decode(..., algorithms=["HS256"])` explicitly. (3) Migrate to RS256 (asymmetric) for production, using a private key for signing and a public key for verification. This limits the blast radius of key compromise.
- **Priority:** P1

### [MEDIUM] No Key Rotation Mechanism
- **Location:** `app/core/security.py`
- **Risk:** There is no support for key rotation. If the signing key is rotated, all existing tokens become invalid immediately, causing mass logout. If a key is compromised, there is no mechanism to revoke and reissue.
- **Impact:** Operational disruption during key rotation. Extended window of vulnerability if key is compromised.
- **Remediation:** Implement JWKS (JSON Web Key Set) support with `kid` header. Maintain a list of valid keys with expiry. Support key rotation by adding new keys and retiring old ones with a grace period for token refresh.
- **Priority:** P2

### [MEDIUM] Tokens Not Revocable
- **Location:** `app/core/security.py`
- **Risk:** JWT tokens, once issued, are valid until expiry. There is no blocklist or revocation list (e.g., Redis-based token denylist).
- **Impact:** Compromised tokens cannot be invalidated before their natural expiry (30 min for access, 7 days for refresh). A stolen refresh token grants a week of access.
- **Remediation:** Maintain a token blocklist in Redis (`{jti: revoked_at}`). Check every request. On password change, logout-all, or admin revocation, add the token's `jti` to the blocklist.
- **Priority:** P1

### [MEDIUM] Password Stored with Only bcrypt (No Pepper)
- **Location:** `app/models/user.py`, `app/core/security.py`
- **Risk:** Passwords are hashed with bcrypt (assumed from industry convention in the codebase), which is acceptable. However, no application-level pepper is used. If the database is compromised, offline brute-force of bcrypt hashes is feasible for weak passwords.
- **Impact:** User password compromise in the event of a database breach.
- **Remediation:** Add an HMAC-based pepper derived from a separate secret key before bcrypt. Use `hashlib.pbkdf2_hmac` or equivalent with the pepper key before passing to bcrypt.
- **Priority:** P2

---

## A03:2021 – Injection

### [HIGH] Potential NoSQL Injection in MongoDB Queries
- **Location:** `app/repositories/*.py`, `app/api/*.py`
- **Risk:** If MongoDB is used as the database (or any document store that accepts query operators), unsanitized user input passed directly to query filters can lead to NoSQL injection. For example, `{"$ne": ""}` bypasses equality checks.
- **Impact:** Authentication bypass, unauthorized data access, data exfiltration.
- **Remediation:** (1) Use a statically typed query builder that rejects operator injection. (2) Sanitize all string inputs and reject objects/arrays where scalars are expected. (3) Use PostgreSQL with parameterized queries instead of MongoDB to eliminate this class entirely. (4) Audit all repository methods to ensure user-controlled values are never passed directly into query operators.
- **Priority:** P1

### [MEDIUM] GraphQL Injection Risk
- **Location:** If GraphQL endpoints exist or are planned
- **Risk:** GraphQL introspection queries and nested mutation depth can lead to denial of service or data leakage if not properly hardened.
- **Impact:** Data exfiltration via nested queries, DoS via deep query chains.
- **Remediation:** Implement query depth limiting, rate limiting per operation type, and disable introspection in production.
- **Priority:** P2

### [LOW] Command Injection via LLM Provider Configuration
- **Location:** `app/llm/factory.py`
- **Risk:** If the LLM provider configuration (e.g., custom endpoint URL) is user-controllable and used in subprocess calls or HTTP requests without validation, command injection or SSRF may be possible.
- **Impact:** Remote code execution or internal network scanning.
- **Remediation:** Validate all URL inputs against an allowlist of schemes (`https://` only) and known hostnames. Never pass user input to shell commands.
- **Priority:** P2

---

## A04:2021 – Insecure Design

### [HIGH] No Rate Limiting on Auth Endpoints
- **Location:** `app/api/auth.py`
- **Risk:** Login, registration, and password reset endpoints have no rate limiting, account lockout, or progressive delay. This enables credential stuffing, brute-force attacks, and enumeration attacks.
- **Impact:** Account takeover via brute-force. User enumeration via timing or response differences.
- **Remediation:** (Mitigated by this PR) Implement sliding window rate limiting with Redis. Additionally: (1) Implement account lockout after N failed attempts (e.g., 5 attempts = 15 min lockout). (2) Add CAPTCHA for repeated attempts. (3) Return generic error messages to prevent enumeration. (4) Log all auth failures with IP, user ID, and timestamp.
- **Priority:** P0

### [HIGH] No Account Lockout Mechanism
- **Location:** `app/api/auth.py`, `app/models/user.py`
- **Risk:** Failed login attempts are not tracked. An attacker can make unlimited login attempts without triggering any lockout or delay.
- **Impact:** Successful credential stuffing attack against weak or reused passwords.
- **Remediation:** Add a `failed_login_attempts` and `locked_until` field to the User model. On failed login, increment the counter. If the threshold is exceeded (e.g., 5 attempts), set `locked_until = now + 15 minutes`. Clear the counter on successful login.
- **Priority:** P0

### [HIGH] No Email Verification
- **Location:** `app/api/auth.py`, `app/models/user.py`
- **Risk:** User registration does not require email verification. Anyone can register with any email address, including disposable/temporary emails.
- **Impact:** Fake accounts, spam, abuse of free-tier resources. Difficulty enforcing identity and accountability for audit trails.
- **Remediation:** (1) Add an email verification flow: send a signed token to the user's email, require the user to confirm before activating the account. (2) Set unverified accounts to an inactive state. (3) Optionally integrate with a disposable email blocklist.
- **Priority:** P1

### [MEDIUM] No Password Strength Enforcement
- **Location:** `app/api/auth.py`, `app/models/user.py`
- **Risk:** No minimum password complexity requirements, length checks, or common-password blocklist are enforced.
- **Impact:** Users may choose weak passwords (e.g., `password123`), making brute-force and credential-stuffing attacks trivial.
- **Remediation:** Enforce minimum length (12+ characters), require mixed case + digits + symbols, and check against a known-bad-passwords list (e.g., HaveIBeenPwned API or a local NCSC list).
- **Priority:** P1

### [MEDIUM] No MFA Support
- **Location:** `app/api/auth.py`
- **Risk:** The authentication system supports only password-based login. No multi-factor authentication is available.
- **Impact:** A compromised password is sufficient for full account access.
- **Remediation:** Add TOTP-based MFA support. Store an `mfa_secret` and `mfa_enabled` flag on the User model. Add an MFA verification step during login. Optionally support backup codes for recovery.
- **Priority:** P2

---

## A05:2021 – Security Misconfiguration

### [HIGH] CORS Too Permissive for Production
- **Location:** `app/core/config.py:25`, `app/middleware/setup.py`
- **Risk:** `allowed_origins` defaults to `["http://localhost:3000", "http://localhost:8000"]`. If not overridden for production, the application will accept cross-origin requests from these origins.
- **Impact:** In production, this is likely misconfigured. If set to `["*"]` or left with localhost origins, it enables CSRF-like attacks and data exfiltration from any page the victim visits.
- **Remediation:** In production, set `ALLOWED_ORIGINS` to the exact production frontend domain. Never use wildcards with credentials. Add startup validation that rejects insecure CORS configurations (localhost in non-dev environments, wildcard, null origin).
- **Priority:** P1

### [MEDIUM] Debug Endpoints Exposed in Production
- **Location:** `app/api/retrieval_debug.py`, `app/api/summarizer_debug.py`, `app/api/gap_debug.py`
- **Risk:** Debug routers are unconditionally included in the app without a feature flag.
- **Impact:** Internal system state, prompts, retrieval chunks, and analysis internals exposed to all users. Increases attack surface.
- **Remediation:** Gate debug routers behind `settings.debug == True` or an environment variable. Return 404 when debug mode is off.
- **Priority:** P1

### [MEDIUM] Verbose Error Messages in Production
- **Location:** `app/middleware/error_handler.py`
- **Risk:** Error responses may leak internal details (stack traces, database errors, library versions, file paths).
- **Impact:** Information disclosure aiding further attacks.
- **Remediation:** In production mode, return generic error responses (e.g., "Internal server error") and log full details server-side. Ensure `debug=False` in production settings to suppress Pydantic/FastAPI debug pages.
- **Priority:** P1

### [MEDIUM] No HTTP Security Headers
- **Location:** All responses
- **Risk:** No security headers (CSP, HSTS, X-Frame-Options, etc.) are set on responses.
- **Impact:** Vulnerable to clickjacking, MIME-type sniffing, XSS, and missing HTTPS enforcement.
- **Remediation:** (Mitigated by this PR) Implement `SecurityHeadersMiddleware` to set CSP, HSTS, X-Content-Type-Options, X-Frame-Options, and other headers on all responses.
- **Priority:** P1

### [MEDIUM] Default Secret Key During Startup
- **Location:** `app/core/config.py:20`
- **Risk:** There is no startup validation that rejects default or weak `SECRET_KEY` values.
- **Impact:** Accidental production deployment with weak key.
- **Remediation:** Add a startup check in lifespan that logs a CRITICAL-level warning (or raises an error) if the secret key is `"change-me-in-production"` or shorter than 32 characters.
- **Priority:** P1

### [LOW] Swagger/OpenAPI UI Exposed in Production
- **Location:** `app/main.py:66-67`
- **Risk:** `/docs` and `/redoc` are always enabled.
- **Impact:** Exposes full API schema, model schemas, and endpoint documentation to anyone. Useful for reconnaissance.
- **Remediation:** Disable `/docs` and `/redoc` in production by setting `docs_url=None, redoc_url=None` when `settings.debug == False`. Or protect behind authentication.
- **Priority:** P2

---

## A06:2021 – Vulnerable and Outdated Components

### [HIGH] No Dependency Scanning / Dependabot
- **Location:** Project root
- **Risk:** Dependencies are not automatically scanned for known vulnerabilities (CVEs). There is no Dependabot, Snyk, or `pip-audit` configuration.
- **Impact:** Vulnerable libraries may be deployed without the team's knowledge.
- **Remediation:** (1) Add `pip-audit` to the CI pipeline. (2) Enable GitHub Dependabot / Renovate for automated PRs. (3) Pin exact versions in `requirements.txt` or lock files. (4) Run `pip-audit` as a pre-commit hook.
- **Priority:** P1

### [MEDIUM] Potential Outdated FastAPI / Starlette Version
- **Location:** `requirements.txt`
- **Risk:** If running an outdated FastAPI or Starlette version, known vulnerabilities (e.g., CVE-2024-24762 for Starlette CSRF, various path traversal issues) may be exploitable.
- **Impact:** Varies by CVE — ranging from information disclosure to RCE.
- **Remediation:** Run `pip list --outdated` and update to the latest stable versions. Use `pip-audit` to identify specific CVEs.
- **Priority:** P1

### [MEDIUM] `python-jose` vs `PyJWT` Considerations
- **Location:** `app/core/security.py`
- **Risk:** The `python-jose` library has had slower update cycles compared to `PyJWT`. Some CVEs around JWT validation bypass (CVE-2022-23529 in `PyJWT`, similar issues in `jose`) require careful handling.
- **Impact:** JWT signature bypass if algorithm validation is not explicit.
- **Remediation:** (1) Ensure explicit `algorithms=["HS256"]` is passed to every decode call. (2) Consider migrating to `PyJWT` with `cryptography` backend for better maintenance.
- **Priority:** P2

---

## A07:2021 – Identification and Authentication Failures

### [CRITICAL] No Rate Limiting on Login
- **Location:** `app/api/auth.py`
- **Risk:** The login endpoint accepts unlimited requests, enabling credential stuffing at thousands of attempts per minute.
- **Impact:** Account takeover for users with weak or reused passwords.
- **Remediation:** (Mitigated by this PR) Apply strict per-IP and per-account rate limits (5 requests/minute). Implement progressive delays and account lockout after repeated failures.
- **Priority:** P0

### [HIGH] Weak Default Password Policy
- **Location:** `app/models/user.py`, `app/api/auth.py`
- **Risk:** No password strength requirements are enforced at registration or password change.
- **Impact:** Users can set weak passwords, making them trivially brute-forced.
- **Remediation:** Enforce: minimum 12 characters, at least one uppercase, one lowercase, one digit, one special character. Check against a blocklist of common passwords. Use zxcvbn or similar for strength estimation.
- **Priority:** P1

### [HIGH] No Refresh Token Rotation
- **Location:** `app/core/security.py`
- **Risk:** Refresh tokens are long-lived (7 days) and are not rotated on each use. A stolen refresh token remains valid for the full window.
- **Impact:** Persistent unauthorized access after token theft.
- **Remediation:** Implement refresh token rotation — issue a new refresh token with each refresh request and invalidate the old one. Store a family identifier to detect replay attacks.
- **Priority:** P1

### [MEDIUM] Session Tokens Not Bound to Device/Fingerprint
- **Location:** `app/core/security.py`
- **Risk:** Access tokens are not bound to client characteristics (IP, User-Agent, device fingerprint).
- **Impact:** A stolen token is usable from any device, anywhere.
- **Remediation:** Embed a hash of the client's IP and User-Agent into the JWT payload. Validate on each request. This reduces the window for token abuse.
- **Priority:** P2

### [MEDIUM] No Logout-All-Devices Capability
- **Location:** `app/core/security.py`
- **Risk:** No mechanism exists to invalidate all user sessions (e.g., password change does not revoke existing tokens).
- **Impact:** After a password change, an attacker with a previously stolen token retains access for up to 7 days.
- **Remediation:** Increment a `token_version` integer on the User model on password change / logout-all. Include `token_version` in the JWT payload and validate it on every request.
- **Priority:** P2

---

## A08:2021 – Software and Data Integrity Failures

### [MEDIUM] Unsigned JWT Without `kid` Verification
- **Location:** `app/core/security.py`
- **Risk:** JWT tokens lack a `kid` (key ID) header, making key rotation and key-pinning impossible.
- **Impact:** If multiple signing keys exist or are rotated, there is no way to identify which key was used.
- **Remediation:** Add a `kid` claim to every token and maintain a key registry with validity periods.
- **Priority:** P2

### [LOW] Unsafe Deserialization in Workflow State
- **Location:** `app/redis/client.py` (`get_workflow_state`)
- **Risk:** Workflow state is serialized/deserialized with `json.loads`. While JSON is generally safe, if the state contains user-controlled data that influences code paths, unsafe evaluation could occur elsewhere.
- **Impact:** Limited — JSON is not executable. However, if the deserialized data is later used in `eval()` or `exec()`, it becomes an RCE vector.
- **Remediation:** Ensure deserialized workflow state is validated against a schema before use. Never pass user-controlled data to `eval()` or `exec()`.
- **Priority:** P2

### [LOW] No Integrity Check on Static Files / Uploaded Documents
- **Location:** `app/api/documents.py`
- **Risk:** Uploaded documents are not checksummed or integrity-verified on download.
- **Impact:** Undetected corruption or tampering of stored documents.
- **Remediation:** Compute SHA-256 hash on upload, store in metadata, and verify on download.
- **Priority:** P2

---

## A09:2021 – Security Logging and Monitoring Failures

### [HIGH] No Security-Relevant Audit Logging
- **Location:** System-wide
- **Risk:** The existing `RequestLoggingMiddleware` logs request metadata but does not log security-relevant events: failed logins, password changes, role changes, data access patterns, privilege escalations.
- **Impact:** No ability to detect, investigate, or respond to security incidents. Violation of compliance requirements (SOC 2, GDPR, HIPAA).
- **Remediation:** (1) Implement a structured `audit_log` event system. Log: login success/failure with user ID, source IP, and timestamp; password changes; resource access denials; role/permission changes; data export events. (2) Send audit logs to a centralized, immutable log store (S3, SIEM, ELK).
- **Priority:** P1

### [HIGH] No Alerting on Anomalous Behavior
- **Location:** System-wide
- **Risk:** There are no automated alerts for: repeated login failures (>N from same IP), high-volume API calls, access denied spikes, or unusual geographic access patterns.
- **Impact:** Attacks progress undetected until significant damage is done.
- **Remediation:** Integrate with a monitoring/alerting system (e.g., Prometheus + Alertmanager, Datadog, Sentry). Define alert rules for: >10 failed logins per minute from an IP, >1000 requests/minute from a user, >5% error rate, admin account access outside business hours.
- **Priority:** P1

### [MEDIUM] No Structured Audit Trail for Data Access
- **Location:** `app/repositories/*.py`
- **Risk:** No logging of which user accessed which resource at what time. Compliance requirements (HIPAA, SOC 2) mandate this.
- **Impact:** Non-compliance. Inability to investigate data breaches.
- **Remediation:** Add an `AuditLog` model and repository. Log every resource READ, CREATE, UPDATE, DELETE operation with user ID, resource type, resource ID, action, timestamp, and source IP.
- **Priority:** P2

### [MEDIUM] Request IDs Not Propagated Downstream
- **Location:** `app/middleware/setup.py`
- **Risk:** While `X-Request-ID` is set on responses, it is not propagated to external calls (LLM providers, database queries, downstream services).
- **Impact:** Hard to correlate a user-facing issue with backend failures.
- **Remediation:** Pass the `request_id` as a header to all downstream calls. Include it in database connection metadata and log contexts.
- **Priority:** P2

### [LOW] No Log Rotation / Retention Policy Configured
- **Location:** `app/core/logging.py`
- **Risk:** Log files may grow unbounded, filling disks and causing service disruption. There is no documented retention policy.
- **Impact:** Operational disruption. Non-compliance with data retention regulations.
- **Remediation:** Configure `RotatingFileHandler` or `TimedRotatingFileHandler` with maxBytes / backupCount. Document retention policy (e.g., 90 days for operational logs, 1 year for audit logs).
- **Priority:** P2

---

## A10:2021 – Server-Side Request Forgery (SSRF)

### [HIGH] Agent Workflow Execution May Fetch Arbitrary URLs
- **Location:** `app/agents/`, `app/workflow/`
- **Risk:** If agents or workflow nodes can be configured to fetch user-provided URLs (e.g., web scraping, API calls, OAuth callbacks), an unvalidated URL can be used to probe internal services (metadata endpoints, internal APIs, cloud provider instance metadata).
- **Impact:** Access to cloud metadata endpoints (e.g., `http://169.254.169.254/latest/meta-data/` for AWS credentials), internal service scanning, potential RCE via internal service exploitation.
- **Remediation:** (1) Maintain a strict allowlist of permitted external hosts/domains. (2) Block private and link-local IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, 169.254.0.0/16, ::1/128). (3) Use a dedicated proxy or egress gateway with deny-by-default rules. (4) Validate and sanitize all user-supplied URLs before HTTP requests.
- **Priority:** P0

### [HIGH] SSRF via Embedding Model / External API Calls
- **Location:** `app/llm/`, `app/vectorstore/`
- **Risk:** The system configures embedding models and LLM providers via URL. If these are user-controllable, SSRF is possible.
- **Impact:** Internal network probing, cloud metadata access.
- **Remediation:** Ensure model provider URLs are hardcoded in configuration, not user-controllable. Validate any dynamically configured URLs against an allowlist.
- **Priority:** P1

### [MEDIUM] No URL Validation in Document Ingestion
- **Location:** `app/api/documents.py`
- **Risk:** If the ingestion pipeline accepts URLs for web scraping or file downloads, unvalidated URLs can trigger SSRF.
- **Impact:** Internal network scanning, cloud metadata access.
- **Remediation:** Apply URL validation: allow only `https://` scheme, deny private IP ranges, validate against domain allowlist.
- **Priority:** P1

---

## Summary

| Severity | Count | P0 | P1 | P2 | P3 |
|----------|-------|----|----|----|----|
| Critical | 5     | 5  | 0  | 0  | 0  |
| High     | 12    | 0  | 11 | 1  | 0  |
| Medium   | 14    | 0  | 5  | 9  | 0  |
| Low      | 3     | 0  | 0  | 3  | 0  |
| **Total**| **34**| **5** | **16** | **13** | **0** |

### Immediate Actions (P0)
1. Implement authorization checks on all resource endpoints
2. Move `SECRET_KEY` from hardcoded default to env-var-only with startup validation
3. Apply rate limiting, account lockout, and progressive delay to auth endpoints
4. Implement SSRF protections on agent workflow URL fetching
5. Add RBAC with at minimum admin/non-admin roles

### Short-Term (P1 – next sprint)
6. Add email verification flow
7. Enforce password strength
8. Implement refresh token rotation
9. Add security audit logging and alerting
10. Dependency scanning in CI
11. CORS hardening
12. Gate debug endpoints behind feature flag

### Medium-Term (P2 – roadmap)
13. MFA/TOTP support
14. Token binding to device fingerprint
15. JWKS key rotation
16. Audit trail for all resource access
17. Migrate to RS256 asymmetric JWT signing
18. Add token revocation via Redis blocklist
