from __future__ import annotations

import hashlib
from dataclasses import dataclass
from uuid import UUID

from app.core.exceptions import FeatureDisabledError, KillSwitchActiveError


@dataclass
class FeatureFlag:
    name: str
    description: str
    default: bool = False
    requires_restart: bool = False
    owner: str = "engineering"
    lifespan: str | None = None


@dataclass
class KillSwitch:
    name: str
    description: str
    active: bool = False


class FeatureFlagSystem:
    def __init__(self) -> None:
        self._flags: dict[str, FeatureFlag] = {}
        self._overrides: dict[str, bool] = {}
        self._cache: dict[str, bool] = {}
        self._cache_ttl: int = 60

    def register(self, flag: FeatureFlag) -> None:
        self._flags[flag.name] = flag

    def register_builtins(self) -> None:
        builtins = [
            FeatureFlag(
                name="agent.idea_generation",
                description="Enable Idea Generation Agent in workflows",
                default=True,
            ),
            FeatureFlag(
                name="agent.writing",
                description="Enable Writing Agent in workflows",
                default=False,
            ),
            FeatureFlag(
                name="export.latex",
                description="Enable LaTeX export format",
                default=False,
            ),
            FeatureFlag(
                name="workflow.full_research",
                description="Enable full research workflow (all 7 agents)",
                default=False,
            ),
            FeatureFlag(
                name="security.llm_output_guard",
                description="Enable secondary LLM safety check on agent output",
                default=False,
                owner="security",
            ),
            FeatureFlag(
                name="experimental.pdf_equation_detection",
                description="Enable experimental equation detection in PDF pipeline",
                default=False,
                owner="research",
            ),
        ]
        for flag in builtins:
            self.register(flag)

    async def is_enabled(
        self,
        flag_name: str,
        user_id: UUID | None = None,
        workspace_id: UUID | None = None,
        use_cache: bool = True,
    ) -> bool:
        cache_key = f"{flag_name}:{user_id}:{workspace_id}"
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        if flag_name in self._overrides:
            result = self._overrides[flag_name]
            self._cache[cache_key] = result
            return result

        flag = self._flags.get(flag_name)
        result = flag.default if flag else False
        self._cache[cache_key] = result
        return result

    async def require_enabled(
        self,
        flag_name: str,
        user_id: UUID | None = None,
        workspace_id: UUID | None = None,
    ) -> None:
        if not await self.is_enabled(flag_name, user_id, workspace_id):
            raise FeatureDisabledError(flag_name)

    def set_override(self, flag_name: str, enabled: bool) -> None:
        self._overrides[flag_name] = enabled
        self._cache.pop(f"{flag_name}:None:None", None)

    def clear_cache(self) -> None:
        self._cache.clear()

    def list_flags(self) -> list[FeatureFlag]:
        return list(self._flags.values())

    def get_flag(self, name: str) -> FeatureFlag | None:
        return self._flags.get(name)


class KillSwitchRegistry:
    def __init__(self) -> None:
        self._switches: dict[str, KillSwitch] = {}
        self._local: dict[str, bool] = {}

    def register_builtins(self) -> None:
        builtins = [
            KillSwitch("llm_providers", "Disable all LLM inference"),
            KillSwitch("research_apis", "Disable all external research API calls"),
            KillSwitch("pdf_uploads", "Disable PDF upload functionality"),
            KillSwitch("workflow_execution", "Disable all workflow creation"),
            KillSwitch("user_registration", "Disable new user registration"),
            KillSwitch("embedding_generation", "Disable all embedding operations"),
        ]
        for switch in builtins:
            self._switches[switch.name] = switch

    def register(self, switch: KillSwitch) -> None:
        self._switches[switch.name] = switch

    async def activate(self, switch: str) -> None:
        self._local[switch] = True
        if switch in self._switches:
            self._switches[switch].active = True

    async def deactivate(self, switch: str) -> None:
        self._local[switch] = False
        if switch in self._switches:
            self._switches[switch].active = False

    async def is_active(self, switch: str) -> bool:
        if switch in self._local:
            return self._local[switch]
        entry = self._switches.get(switch)
        return entry.active if entry else False

    async def require_inactive(self, switch: str) -> None:
        if await self.is_active(switch):
            raise KillSwitchActiveError(switch)

    def list_switches(self) -> list[KillSwitch]:
        return list(self._switches.values())

    def register_from_overrides(self, overrides: dict[str, bool]) -> None:
        for name, active in overrides.items():
            if name in self._switches:
                self._local[name] = active


class GradualRollout:
    async def is_enabled_for_user(
        self, flag_name: str, user_id: UUID, rollout_percentage: int
    ) -> bool:
        bucket = int(hashlib.md5(str(user_id).encode()).hexdigest(), 16) % 100
        return bucket < rollout_percentage

    async def rollout_schedule(self, flag_name: str, days: int = 14) -> dict[int, int]:
        return {
            1: 5,
            3: 25,
            7: 50,
            10: 75,
            14: 100,
        }
