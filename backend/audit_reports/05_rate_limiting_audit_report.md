# Phase 5: Rate Limiting Audit Report

## Scope
Audited `middleware/rate_limit.py`, `redis/client.py`, and the `RateLimitDependency` class.

## Findings

### HIGH — TOCTOU race condition (FIXED)
- `sliding_window_counter()` had a time-of-check-to-time-of-use bug: ZCARD check then separate ZADD call
- Between check and increment, a concurrent request could sneak in and exceed limit
- **FIXED**: Replaced with atomic Lua script that atomically checks ZCARD and ZADD

### MEDIUM — No X-Real-IP fallback
- Only `X-Forwarded-For` is parsed, not `X-Real-IP`
- **Fix**: Accept both headers in rate limiter, preferring X-Forwarded-For

### MEDIUM — No proxy trust middleware
- No `TrustedHostMiddleware` or `ProxyHeadersMiddleware` configured
- Proxy deployments see proxy IP instead of client IP
- **Recommendation**: Add `ProxyHeadersMiddleware` for production

### LOW — Memory mode is default
- `redis_url: str = "memory"` — multi-worker deployments will have per-worker counters
- Works correctly with actual Redis; memory mode suitable for dev only

### PASS — Rate limit scope
- User-based (JWT subject) with IP fallback
- Separate rate limit counters for different resources
- Clean separation of concerns

## Fixes Applied
1. Replaced `sliding_window_counter` with atomic Lua script
2. Added `X-Real-IP` header support alongside `X-Forwarded-For`
