from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.exceptions import FeatureDisabledError, KillSwitchActiveError
from app.feature_flags.feature_flags import (
    FeatureFlag,
    FeatureFlagSystem,
    GradualRollout,
    KillSwitch,
    KillSwitchRegistry,
)


class TestFeatureFlagSystem:
    def test_register_and_check_default(self):
        ffs = FeatureFlagSystem()
        ffs.register(FeatureFlag(name="test.feature", description="Test", default=True))
        assert ffs.get_flag("test.feature") is not None
        assert ffs.list_flags()[0].name == "test.feature"

    def test_builtins_are_registered(self):
        ffs = FeatureFlagSystem()
        ffs.register_builtins()
        assert ffs.get_flag("agent.idea_generation") is not None
        assert ffs.get_flag("agent.writing") is not None
        assert ffs.get_flag("export.latex") is not None

    @pytest.mark.asyncio
    async def test_is_enabled_default_true(self):
        ffs = FeatureFlagSystem()
        ffs.register(FeatureFlag(name="test.feature", description="Test", default=True))
        assert await ffs.is_enabled("test.feature") is True

    @pytest.mark.asyncio
    async def test_is_enabled_default_false(self):
        ffs = FeatureFlagSystem()
        ffs.register(FeatureFlag(name="test.feature", description="Test", default=False))
        assert await ffs.is_enabled("test.feature") is False

    @pytest.mark.asyncio
    async def test_is_enabled_unknown_flag(self):
        ffs = FeatureFlagSystem()
        assert await ffs.is_enabled("nonexistent") is False

    @pytest.mark.asyncio
    async def test_override(self):
        ffs = FeatureFlagSystem()
        ffs.register(FeatureFlag(name="test.feature", description="Test", default=False))
        ffs.set_override("test.feature", True)
        assert await ffs.is_enabled("test.feature", use_cache=False) is True

    @pytest.mark.asyncio
    async def test_require_enabled_raises(self):
        ffs = FeatureFlagSystem()
        ffs.register(FeatureFlag(name="test.feature", description="Test", default=False))
        with pytest.raises(FeatureDisabledError):
            await ffs.require_enabled("test.feature")

    @pytest.mark.asyncio
    async def test_require_enabled_passes(self):
        ffs = FeatureFlagSystem()
        ffs.register(FeatureFlag(name="test.feature", description="Test", default=True))
        await ffs.require_enabled("test.feature")

    def test_clear_cache(self):
        ffs = FeatureFlagSystem()
        ffs.register(FeatureFlag(name="test.feature", description="Test", default=True))
        ffs.clear_cache()


class TestKillSwitchRegistry:
    def test_register_builtins(self):
        ksr = KillSwitchRegistry()
        ksr.register_builtins()
        switches = ksr.list_switches()
        names = {s.name for s in switches}
        assert "llm_providers" in names
        assert "workflow_execution" in names

    @pytest.mark.asyncio
    async def test_activate_and_check(self):
        ksr = KillSwitchRegistry()
        ksr.register(KillSwitch(name="test.switch", description="Test"))
        assert await ksr.is_active("test.switch") is False
        await ksr.activate("test.switch")
        assert await ksr.is_active("test.switch") is True

    @pytest.mark.asyncio
    async def test_deactivate(self):
        ksr = KillSwitchRegistry()
        ksr.register(KillSwitch(name="test.switch", description="Test"))
        await ksr.activate("test.switch")
        await ksr.deactivate("test.switch")
        assert await ksr.is_active("test.switch") is False

    @pytest.mark.asyncio
    async def test_unknown_switch_is_inactive(self):
        ksr = KillSwitchRegistry()
        assert await ksr.is_active("nonexistent") is False

    @pytest.mark.asyncio
    async def test_require_inactive_raises(self):
        ksr = KillSwitchRegistry()
        ksr.register(KillSwitch(name="test.switch", description="Test"))
        await ksr.activate("test.switch")
        with pytest.raises(KillSwitchActiveError):
            await ksr.require_inactive("test.switch")

    @pytest.mark.asyncio
    async def test_require_inactive_passes(self):
        ksr = KillSwitchRegistry()
        ksr.register(KillSwitch(name="test.switch", description="Test"))
        await ksr.require_inactive("test.switch")

    def test_register_from_overrides(self):
        ksr = KillSwitchRegistry()
        ksr.register_builtins()
        ksr.register_from_overrides({"llm_providers": True})


class TestGradualRollout:
    @pytest.mark.asyncio
    async def test_deterministic_bucketing(self):
        rollout = GradualRollout()
        user_id = uuid4()
        result1 = await rollout.is_enabled_for_user("test", user_id, 50)
        result2 = await rollout.is_enabled_for_user("test", user_id, 50)
        assert result1 == result2

    @pytest.mark.asyncio
    async def test_zero_percent(self):
        rollout = GradualRollout()
        assert await rollout.is_enabled_for_user("test", uuid4(), 0) is False

    @pytest.mark.asyncio
    async def test_hundred_percent(self):
        rollout = GradualRollout()
        assert await rollout.is_enabled_for_user("test", uuid4(), 100) is True

    @pytest.mark.asyncio
    async def test_rollout_schedule(self):
        rollout = GradualRollout()
        schedule = await rollout.rollout_schedule("test")
        assert schedule[1] == 5
        assert schedule[14] == 100
