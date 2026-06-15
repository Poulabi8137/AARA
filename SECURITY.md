# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in AARA, please do **not** open a public issue. Instead, send a description of the issue to the project maintainers directly.

Please include:
- Type of issue (XSS, authentication bypass, privilege escalation, etc.)
- Steps to reproduce
- Impact assessment
- Any suggested fix (if known)

You should receive a response within 48 hours. If you don't, please follow up.

## What to Expect

- Confirmation of receipt within 48 hours
- An initial assessment of severity and impact within 5 business days
- A fix timeline based on severity (critical: 7 days, high: 14 days, medium: 30 days)
- Credit in release notes if you opt in

## Security Features

AARA includes the following security mechanisms:

### Authentication
- JWT with HMAC-SHA256 signature verification (access + refresh tokens)
- Refresh token rotation — every refresh call issues a new refresh token
- Silent token refresh with request queueing (concurrent 401s)
- Fail-closed proxy — missing `JWT_SECRET` blocks all requests
- Cross-tab auth synchronization via `storage` event listener

### Authorization
- Role-based access control (Admin, Researcher, Viewer)
- Resource ownership validation on every protected endpoint
- Token type enforcement (access tokens vs refresh tokens)
- Token version support for global invalidation

### Infrastructure
- Secrets validated at startup (backend rejects empty/default SECRET_KEY)
- CORS enforced by origin whitelist
- Structured logging for auditability
- Password hashing with bcrypt (72-byte truncation-safe)

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest  | Yes       |
| < latest| No        |
