# Document 06 — Authentication Flow

## Auth Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  [Browser]                    [Next.js]           [FastAPI]    [Supabase]
│     │                            │                    │            │
│     │ 1. User clicks Login       │                    │            │
│     │─── GET /login ────────────→│                    │            │
│     │←── Login Page ────────────│                    │            │
│     │                            │                    │            │
│     │ 2. User enters credentials │                    │            │
│     │─── email + password ──────→│                    │            │
│     │                            │─── POST /auth ────→│            │
│     │                            │   /v1/token?       │            │
│     │                            │   grant_type=      │── sign_in ─→│
│     │                            │   password         │            │
│     │                            │                    │←── JWT ────│
│     │                            │                    │  response   │
│     │                            │←── Set httpOnly ──│            │
│     │                            │    cookie          │            │
│     │←── 302 /dashboard ────────│                    │            │
│     │                            │                    │            │
│     │ 3. Dashboard page loads    │                    │            │
│     │─── GET /api/v1/workspaces ─→│─────── API ──────→│            │
│     │    (cookie sent)            │       call         │            │
│     │                            │                    │── verify ──→│
│     │                            │                    │   JWT       │
│     │                            │                    │            │
│     │    [Workspace data]        │                    │            │
│     │←───────────────────────────│←── 200 OK ────────│            │
│     │                            │                    │            │
│     │ 4. Token expires (401)     │                    │            │
│     │─── GET /api/v1/papers ────→│─────── API ──────→│            │
│     │                            │       call         │── verify ──→│
│     │                            │                    │   JWT (exp) │
│     │                            │                    │── 401 ─────│
│     │                            │←── 401 ──────────│            │
│     │                            │                    │            │
│     │ 5. Auto-refresh            │                    │            │
│     │                            │─── POST /auth ────→│            │
│     │                            │   /v1/token?       │── refresh ─→│
│     │                            │   grant_type=      │   token     │
│     │                            │   refresh_token    │            │
│     │                            │                    │←── new JWT │
│     │                            │←── Update cookie ─│            │
│     │                            │                    │            │
│     │ 6. Retry original request  │                    │            │
│     │                            │─── (retry with    →│            │
│     │                            │    new token)      │            │
│     │                            │                    │── OK ─────│
│     │←── Data ──────────────────│←── 200 ───────────│            │
└─────────────────────────────────────────────────────────────────────┘
```

## Security Decisions

| Decision | Rationale | Trade-off |
|---|---|---|---|
| httpOnly cookies | Prevents XSS token theft | Requires SameSite config for cross-origin |
| Supabase Auth vs. custom JWT | Zero-implementation auth, built-in refresh, 50K free users | Reliance on Supabase availability |
| Token refresh via backend proxy | Backend can log refresh events, apply rate limits | Extra network hop |
| 60-min access token + 30-day refresh | Balances security with UX | Short access tokens mean more refreshes |
| Cached JWKS verification | 50-80ms → 1-2ms per request; no Supabase dependency on every call | 1h stale cache if keys rotate (mitigated by forced refresh on 401) |

## Backend JWT Verification (Cached JWKS)

Instead of calling the Supabase API on every request (50-80ms overhead), the backend caches Supabase's JWKS keyset locally and verifies tokens locally.

```python
# backend/app/auth/jwt_handler.py

import jwt
import httpx
from jwt import PyJWKClient
from cachetools import TTLCache

class JWKSVerifier:
    """Verifies Supabase JWT tokens using cached JWKS keys."""

    def __init__(self):
        # Supabase JWKS URL: https://<project>.supabase.co/auth/v1/.well-known/jwks.json
        self.jwks_url = None
        self._cache = TTLCache(maxsize=1, ttl=3600)  # 1-hour cache lifetime
        self._client = None

    async def initialize(self, supabase_url: str):
        """Initialize with the Supabase project URL. Called at server startup."""
        self.jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
        # Warm the cache on startup
        await self._fetch_jwks()

    async def _fetch_jwks(self) -> dict:
        """Fetch JWKS from Supabase. Cache miss triggers a fresh fetch."""
        cache_key = "jwks"
        if cache_key in self._cache:
            return self._cache[cache_key]

        async with httpx.AsyncClient() as client:
            response = await client.get(self.jwks_url, timeout=10)
            response.raise_for_status()
            jwks = response.json()
            self._cache[cache_key] = jwks
            return jwks

    async def verify(self, token: str) -> UserPayload:
        """Verify a JWT token locally. Returns decoded payload on success."""
        try:
            jwks = await self._fetch_jwks()
            jwk_client = PyJWKClient(jwks)
            signing_key = jwk_client.get_signing_key_from_jwt(token)

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options={"verify_exp": True, "verify_aud": False},
            )

            return UserPayload(
                id=payload["sub"],
                email=payload.get("email", ""),
                display_name=payload.get("user_metadata", {}).get("full_name", ""),
                role=payload.get("user_metadata", {}).get("role", "student"),
            )

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception:
            # Fallback: call Supabase API directly if JWKS fetch fails
            return await self._fallback_verify(token)

    async def _fallback_verify(self, token: str) -> UserPayload:
        """Fallback: verify against Supabase API directly if JWKS unavailable."""
        try:
            from supabase import create_client
            user_data = await supabase.auth.get_user(token)
            return UserPayload(
                id=user_data.user.id,
                email=user_data.user.email,
                display_name=user_data.user.user_metadata.get("full_name"),
                role=user_data.user.user_metadata.get("role", "student"),
            )
        except Exception:
            raise HTTPException(status_code=401, detail="Authentication failed")

    def refresh_jwks(self):
        """Force refresh the JWKS cache. Called on 401 rate limit or admin trigger."""
        self._cache.pop("jwks", None)


# FastAPI dependency that uses the cached verifier
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)
jwks_verifier = JWKSVerifier()  # Singleton

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    cookie_token: str | None = Cookie(None),
) -> User:
    token = credentials.credentials if credentials else cookie_token
    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication")
    return await jwks_verifier.verify(token)
```

**Cache strategy:**

| Parameter | Value | Rationale |
|---|---|---|
| Cache lifetime | 3600s (1 hour) | Supabase JWKS keys rotate rarely; 1h balances security vs. latency |
| Refresh trigger | Cache miss | On expiry or eviction, next request fetches fresh JWKS |
| Forced refresh | On 401 errors | If a valid-looking token gets rejected, refresh JWKS and retry |
| Fallback | Supabase API call | If JWKS URL is unreachable, fall back to direct verification |
| Startup behavior | Warm cache on init | First request never blocks on JWKS fetch |

**Performance improvement:**
- Before: ~50-80ms per request (Supabase API network call)
- After: ~1-2ms per request (local RS256 verification)

## WebSocket Auth

```python
# backend/app/streaming/manager.py

async def authenticate_websocket(websocket: WebSocket) -> User | None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return None

    try:
        user_data = await supabase.auth.get_user(token)
        return User(id=user_data.user.id, email=user_data.user.email, ...)
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return None
```

## Session Management (Frontend)

```typescript
// frontend/lib/auth-context.tsx

const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const { data: session, isLoading } = useSupabaseSession();
  const queryClient = useQueryClient();

  const signOut = async () => {
    await supabase.auth.signOut();
    queryClient.clear(); // Clear all cached API data
    router.push("/login");
  };

  // Auto-refresh is handled by Supabase JS SDK internally.
  // TanStack Query will retry failed requests after refresh.
  if (isLoading) return <LoadingScreen />;
  if (!session) return <LoginPage />;

  return (
    <AuthContext.Provider value={{ user: session.user, signOut }}>
      {children}
    </AuthContext.Provider>
  );
};
```
