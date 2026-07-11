from __future__ import annotations

import pytest

from app.health.dependency import DependencyConfig, DependencyHealthCheck, DependencyHealthRegistry
from app.health.framework import HealthChecker, HealthCheckResult
from app.health.liveness import LivenessProbe
from app.health.readiness import ReadinessProbe
from app.health.startup import StartupValidationResult, StartupValidator


class TestHealthChecker:
    @pytest.mark.asyncio
    async def test_run_all_passing(self):
        checker = HealthChecker()

        async def ok_check():
            return HealthCheckResult(name="test", healthy=True)

        checker.register("test", ok_check)
        results = await checker.run_all()
        assert len(results) == 1
        assert results[0].healthy is True

    @pytest.mark.asyncio
    async def test_run_all_failing(self):
        checker = HealthChecker()

        async def fail_check():
            return HealthCheckResult(name="test", healthy=False, message="fail")

        checker.register("test", fail_check)
        results = await checker.run_all()
        assert results[0].healthy is False

    @pytest.mark.asyncio
    async def test_run_all_exception(self):
        checker = HealthChecker()

        async def broken_check():
            raise RuntimeError("broken")

        checker.register("test", broken_check)
        results = await checker.run_all()
        assert results[0].healthy is False

    @pytest.mark.asyncio
    async def test_is_healthy(self):
        checker = HealthChecker()

        async def ok_check():
            return HealthCheckResult(name="test", healthy=True)

        checker.register("test", ok_check)
        assert await checker.is_healthy() is True

    @pytest.mark.asyncio
    async def test_summary(self):
        checker = HealthChecker()

        async def ok_check():
            return HealthCheckResult(name="test", healthy=True)

        checker.register("test", ok_check)
        summary = await checker.summary()
        assert summary["healthy"] is True

    def test_list_checks(self):
        checker = HealthChecker()

        async def ok_check():
            return HealthCheckResult(name="test", healthy=True)

        checker.register("test", ok_check)
        assert "test" in checker.list_checks()

    def test_register_bool_result(self):
        checker = HealthChecker()

        async def ok_check():
            return True

        checker.register("t", ok_check)

    def test_unregister(self):
        checker = HealthChecker()

        async def ok_check():
            return HealthCheckResult(name="test", healthy=True)

        checker.register("test", ok_check)
        checker.unregister("test")
        assert "test" not in checker.list_checks()


class FakeDependencyCheck(DependencyHealthCheck):
    async def check(self) -> HealthCheckResult:
        return HealthCheckResult(name=self.config.name, healthy=True)


class TestDependencyHealthRegistry:
    @pytest.mark.asyncio
    async def test_check_all(self):
        registry = DependencyHealthRegistry()
        registry.register(FakeDependencyCheck(DependencyConfig(name="db")))
        results = await registry.check_all()
        assert "db" in results

    @pytest.mark.asyncio
    async def test_is_all_healthy(self):
        registry = DependencyHealthRegistry()
        registry.register(FakeDependencyCheck(DependencyConfig(name="db")))
        assert await registry.is_all_healthy() is True

    def test_list_dependencies(self):
        registry = DependencyHealthRegistry()
        registry.register(FakeDependencyCheck(DependencyConfig(name="db")))
        assert "db" in registry.list_dependencies()


class TestReadinessProbe:
    @pytest.mark.asyncio
    async def test_check(self):
        checker = HealthChecker()

        async def ok():
            return HealthCheckResult(name="r", healthy=True)

        checker.register("r", ok)
        probe = ReadinessProbe(checker)
        result = await probe.check()
        assert result.healthy is True

    def test_mark_ready(self):
        checker = HealthChecker()
        probe = ReadinessProbe(checker)
        probe.mark_ready("db_ready")
        assert probe.get_state().db_ready is True

    def test_mark_not_ready(self):
        checker = HealthChecker()
        probe = ReadinessProbe(checker)
        probe.mark_ready("db_ready")
        probe.mark_not_ready("db_ready")
        assert probe.get_state().db_ready is False


class TestLivenessProbe:
    @pytest.mark.asyncio
    async def test_is_alive(self):
        probe = LivenessProbe(timeout=30.0)
        assert await probe.is_alive() is True

    @pytest.mark.asyncio
    async def test_check(self):
        probe = LivenessProbe(timeout=30.0)
        result = await probe.check()
        assert result.healthy is True

    def test_mark_activity(self):
        probe = LivenessProbe()
        probe.mark_activity()


class TestStartupValidator:
    @pytest.mark.asyncio
    async def test_validate_all_passing(self):
        validator = StartupValidator()

        async def ok():
            return StartupValidationResult(name="cfg", passed=True)

        validator.register("cfg", ok)
        results = await validator.validate_all()
        assert len(results) == 1
        assert results[0].passed is True

    @pytest.mark.asyncio
    async def test_all_passed(self):
        validator = StartupValidator()

        async def ok():
            return True

        validator.register("cfg", ok)
        await validator.validate_all()
        assert validator.all_passed() is True

    @pytest.mark.asyncio
    async def test_validation_failure(self):
        validator = StartupValidator()

        async def fail():
            raise ValueError("fail")

        validator.register("cfg", fail)
        await validator.validate_all()
        assert validator.all_passed() is False
        assert len(validator.get_failures()) == 1
