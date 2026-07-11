# Document 34 — Configuration & Feature Flag Architecture

## Configuration Hierarchy

Configuration is resolved from highest priority to lowest. Higher priority sources override lower ones.

```
Priority 1 (highest):  Runtime API / Workspace settings
Priority 2:            User preferences (PostgreSQL)
Priority 3:            Workspace configuration (workspace_settings table)
Priority 4:            Environment variables
Priority 5:            .env file (local dev only)
Priority 6 (lowest):   Code defaults / fail-safe values
```

```python
class ConfigResolver:
    """Resolves configuration from multiple sources with priority."""

    def __init__(self):
        self._sources: list[ConfigSource] = []

    def add_source(self, source: ConfigSource, priority: int):
        self._sources.append((priority, source))
        self._sources.sort(key=lambda x: x[0], reverse=True)

    async def get(self, key: str, default: Any = None) -> Any:
        for _, source in self._sources:
            value = await source.get(key)
            if value is not None:
                return value
        return default
```

## Configuration Sources

| Source | Type | Priority | Scope | Example Keys |
|---|---|---|---|---|
| Code defaults | Static | 6 | Global | `MAX_WORKFLOW_TIMEOUT=3600` |
| `.env` file | File | 5 | Dev only | `OPENAI_API_KEY=sk-...` |
| Environment variable | OS | 4 | Per-deploy | `DATABASE_URL=postgres://...` |
| `workspace_settings` table | DB | 3 | Per-workspace | `preferred_llm_provider=openai` |
| `user_preferences` table | DB | 2 | Per-user | `theme=dark` |
| Runtime API | Request | 1 | Per-request | `model=gpt-4o` (query param) |

## Configuration Definitions

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from decimal import Decimal

class GlobalConfig(BaseModel):
    """Static configuration with environment variable override."""

    # --- Database ---
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:aara_dev@localhost:5432/aara",
        validation_alias="DATABASE_URL",
    )
    database_pool_size: int = Field(default=10, validation_alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, validation_alias="DATABASE_MAX_OVERFLOW")

    # --- Qdrant ---
    qdrant_url: str = Field(default="http://localhost:6333", validation_alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, validation_alias="QDRANT_API_KEY")
    qdrant_prefer_grpc: bool = Field(default=True, validation_alias="QDRANT_PREFER_GRPC")

    # --- Redis ---
    redis_url: str = Field(default="redis://localhost:6379", validation_alias="REDIS_URL")

    # --- Supabase ---
    supabase_url: str = Field(validation_alias="SUPABASE_URL")
    supabase_service_key: str = Field(validation_alias="SUPABASE_SERVICE_KEY")

    # --- LLM Providers ---
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    gemini_api_key: str | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    groq_api_key: str | None = Field(default=None, validation_alias="GROQ_API_KEY")
    openrouter_api_key: str | None = Field(default=None, validation_alias="OPENROUTER_API_KEY")

    # --- Security ---
    encryption_key: str = Field(default="", validation_alias="ENCRYPTION_KEY")
    cors_origins: list[str] = Field(default=["http://localhost:3000"], validation_alias="CORS_ORIGINS")
    jwt_algorithm: str = "RS256"

    # --- Job Queue ---
    job_queue_backend: Literal["local", "fastapi", "arq"] = Field(
        default="local", validation_alias="JOB_QUEUE_BACKEND"
    )

    # --- Budget ---
    monthly_budget_default: Decimal = Field(default=Decimal("5.00"), validation_alias="MONTHLY_BUDGET_DEFAULT")

    # --- Logging ---
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    environment: Literal["development", "staging", "production"] = Field(
        default="development", validation_alias="ENV"
    )

    @field_validator("supabase_url", "supabase_service_key")
    def validate_required_in_production(cls, v, info):
        if cls.environment == "production" and not v:
            raise ValueError(f"{info.field_name} is required in production")
        return v
```

## Feature Flags

```python
class FeatureFlag(BaseModel):
    """Definition of a single feature flag."""

    name: str
    description: str
    default: bool = False
    requires_restart: bool = False  # True if flag requires server restart
    owner: str = "engineering"
    lifespan: str | None = None  # Expected removal date

class FeatureFlagSystem:
    """Central feature flag system with kill switches."""

    def __init__(self, db: AsyncSession):
        self._db = db
        self._cache: dict[str, bool] = {}
        self._cache_ttl = 60  # seconds

        # Built-in feature flags
        self._flags: dict[str, FeatureFlag] = {
            "agent.idea_generation": FeatureFlag(
                name="agent.idea_generation",
                description="Enable Idea Generation Agent in workflows",
                default=True,
            ),
            "agent.writing": FeatureFlag(
                name="agent.writing",
                description="Enable Writing Agent in workflows",
                default=False,  # Gradual rollout
            ),
            "export.latex": FeatureFlag(
                name="export.latex",
                description="Enable LaTeX export format",
                default=False,
            ),
            "workflow.full_research": FeatureFlag(
                name="workflow.full_research",
                description="Enable full research workflow (all 7 agents)",
                default=False,  # Gradual rollout
            ),
            "security.llm_output_guard": FeatureFlag(
                name="security.llm_output_guard",
                description="Enable secondary LLM safety check on agent output",
                default=False,  # Performance impact; enable if needed
                owner="security",
            ),
            "experimental.pdf_equation_detection": FeatureFlag(
                name="experimental.pdf_equation_detection",
                description="Enable experimental equation detection in PDF pipeline",
                default=False,
                owner="research",
            ),
        }

    async def is_enabled(self, flag_name: str, user_id: UUID = None,
                          workspace_id: UUID = None) -> bool:
        """Check if a feature flag is enabled, with optional per-user/per-workspace override."""

        # 1. Kill switch: if globally disabled in DB, return False
        kill = await self._get_kill_switch(flag_name)
        if kill is not None:
            return False

        # 2. Per-workspace override (highest priority)
        if workspace_id:
            ws_override = await self._get_workspace_override(flag_name, workspace_id)
            if ws_override is not None:
                return ws_override

        # 3. Per-user override
        if user_id:
            user_override = await self._get_user_override(flag_name, user_id)
            if user_override is not None:
                return user_override

        # 4. Global default
        flag = self._flags.get(flag_name)
        return flag.default if flag else False

    async def set_kill_switch(self, flag_name: str, active: bool):
        """Emergency kill switch — immediately disables a feature for all users."""
        # Store in DB with immediate effect
        await self._db.execute(
            upsert(FeatureFlagOverride).values(
                flag_name=flag_name, kill_switch=active, updated_at=func.now()
            )
        )
        await self._db.commit()
        self._cache.pop(flag_name, None)
```

## Kill Switches

```python
class KillSwitchRegistry:
    """Emergency kill switches for critical system functions."""

    KILL_SWITCHES = {
        "llm_providers": "Disable all LLM inference (emergency cost control)",
        "research_apis": "Disable all external research API calls",
        "pdf_uploads": "Disable PDF upload functionality",
        "workflow_execution": "Disable all workflow creation",
        "user_registration": "Disable new user registration",
        "embedding_generation": "Disable all embedding operations",
    }

    def __init__(self, db: AsyncSession):
        self._db = db
        self._local: dict[str, bool] = {}  # In-memory override (fastest)

    async def activate(self, switch: str):
        """Activate a kill switch immediately."""
        self._local[switch] = True
        await self._db.execute(
            update(KillSwitchState).where(KillSwitchState.name == switch)
            .values(active=True, activated_at=func.now())
        )
        await self._db.commit()

    async def deactivate(self, switch: str):
        self._local[switch] = False
        await self._db.execute(
            update(KillSwitchState).where(KillSwitchState.name == switch)
            .values(active=False)
        )
        await self._db.commit()

    async def is_active(self, switch: str) -> bool:
        # Check local first (fast path)
        if switch in self._local:
            return self._local[switch]
        # Fall back to DB
        result = await self._db.execute(
            select(KillSwitchState.active).where(KillSwitchState.name == switch)
        )
        state = result.scalar_one_or_none()
        return state or False
```

## Rollout Strategy

```python
class GradualRollout:
    """Controls gradual feature rollout by user percentage."""

    async def is_enabled_for_user(self, flag_name: str, user_id: UUID,
                                   rollout_percentage: int) -> bool:
        """Deterministic: same user always gets the same result."""
        # Hash user_id to a bucket 0-99
        bucket = int(hashlib.md5(str(user_id).encode()).hexdigest(), 16) % 100
        return bucket < rollout_percentage

    async def rollout_schedule(self, flag_name: str, days: int = 14):
        """Generate a rollout schedule: 5% → 25% → 50% → 100% over N days."""
        schedule = {
            1: 5,    # Day 1:  5% of users
            3: 25,   # Day 3:  25%
            7: 50,   # Day 7:  50%
            10: 75,  # Day 10: 75%
            14: 100, # Day 14: 100%
        }
        return schedule
```

## Configuration Loading Order

```
1. parse .env file (if exists, dev only)
2. read environment variables → populate GlobalConfig
3. validate GlobalConfig (Pydantic validation)
4. initialize DB connections
5. load workspace defaults (workspace_settings table)
6. load user preferences (user_preferences table)
7. initialize FeatureFlagSystem
8. initialize KillSwitchRegistry
9. register all extensions (AgentRegistry, ToolRegistry, etc.)
10. start Event Bus
11. warm JWKS cache
12. recover active workflows
13. expose /health endpoint
```

```python
class ApplicationInitializer:
    """Orchestrates application startup with correct configuration loading order."""

    async def initialize(self) -> AppContext:
        # Step 1-2: Load config
        from dotenv import load_dotenv
        if os.path.exists(".env"):
            load_dotenv()

        config = GlobalConfig()

        # Step 3: Validate
        config.model_validate(config)

        # Step 4: Initialize DB
        engine = create_async_engine(config.database_url)

        # Step 7-8: Feature flags and kill switches
        async with AsyncSession(engine) as session:
            feature_flags = FeatureFlagSystem(session)
            kill_switches = KillSwitchRegistry(session)

        # Step 12: Recover active workflows
        state_manager = SupervisorStateManager()
        active_workflows = await state_manager.recover_all_active_workflows()

        return AppContext(
            config=config,
            engine=engine,
            feature_flags=feature_flags,
            kill_switches=kill_switches,
            active_workflows=active_workflows,
        )
```

## Secrets Management

```python
class SecretsResolver:
    """Resolves secrets from multiple backends."""

    def __init__(self):
        self._backends: list[SecretsBackend] = [
            EnvironmentSecretsBackend(),    # Environment variables
            VaultSecretsBackend(),          # HashiCorp Vault (future)
            AwsSecretsBackend(),            # AWS Secrets Manager (future)
        ]

    async def get(self, key: str) -> str | None:
        for backend in self._backends:
            value = await backend.get(key)
            if value is not None:
                return value
        return None

class EnvironmentSecretsBackend(SecretsBackend):
    """Reads secrets from environment variables."""

    PREFIX = "AARA_SECRET_"

    async def get(self, key: str) -> str | None:
        return os.environ.get(f"{self.PREFIX}{key}")
```

## Fail-Safe Defaults

Every configurable value has a fail-safe default that ensures the system runs (possibly in degraded mode) even without configuration.

| Key | Fail-Safe Default | Degraded Behavior |
|---|---|---|
| `database_url` | In-memory SQLite | Data lost on restart; works for dev |
| `qdrant_url` | `None` | Vector search unavailable; keyword search only |
| `supabase_url` | `None` | Auth unavailable; all endpoints return 503 |
| `openai_api_key` | `None` | LLM unavailable; agents return "provider not configured" |
| `redis_url` | `None` | Job queue falls back to local SQLite |
| `encryption_key` | `insecure-dev-key` | Logs warning on startup; must be set in production |
| `log_level` | `INFO` | Normal operation |
| `job_queue_backend` | `local` | Works for dev and single-instance prod |

## Database Schema

```sql
CREATE TABLE feature_flag_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flag_name VARCHAR(100) NOT NULL,
    user_id UUID REFERENCES users(id),
    workspace_id UUID REFERENCES workspaces(id),
    enabled BOOLEAN NOT NULL,
    kill_switch BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(flag_name, user_id),
    UNIQUE(flag_name, workspace_id)
);

CREATE TABLE kill_switch_states (
    name VARCHAR(100) PRIMARY KEY,
    description TEXT,
    active BOOLEAN DEFAULT FALSE,
    activated_at TIMESTAMPTZ,
    deactivated_at TIMESTAMPTZ
);
```
