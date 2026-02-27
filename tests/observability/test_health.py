"""Tests for health checks."""

import pytest

from app.observability.health import (
    HealthStatus,
    ComponentHealth,
    SystemHealth,
    HealthChecker,
)


class TestComponentHealth:
    """Tests for ComponentHealth."""
    
    def test_create_healthy(self):
        """Can create healthy component."""
        health = ComponentHealth(
            name="test",
            status=HealthStatus.HEALTHY,
        )
        
        assert health.status == HealthStatus.HEALTHY
        assert health.checked_at is not None


class TestSystemHealth:
    """Tests for SystemHealth."""
    
    def test_to_dict(self):
        """Converts to dictionary correctly."""
        health = SystemHealth(
            status=HealthStatus.HEALTHY,
            components=[
                ComponentHealth(name="db", status=HealthStatus.HEALTHY),
            ],
            version="1.0.0",
            uptime_seconds=100.0,
        )
        
        result = health.to_dict()
        
        assert result["status"] == "healthy"
        assert result["version"] == "1.0.0"
        assert len(result["components"]) == 1


class TestHealthChecker:
    """Tests for HealthChecker."""
    
    @pytest.fixture
    def checker(self):
        return HealthChecker(version="1.0.0")
    
    @pytest.mark.asyncio
    async def test_no_checks_healthy(self, checker):
        """No checks means healthy."""
        health = await checker.check_all()
        
        assert health.status == HealthStatus.HEALTHY
        assert len(health.components) == 0
    
    @pytest.mark.asyncio
    async def test_register_and_check(self, checker):
        """Can register and run check."""
        async def healthy_check():
            return ComponentHealth(
                name="test",
                status=HealthStatus.HEALTHY,
            )
        
        checker.register("test", healthy_check)
        health = await checker.check_all()
        
        assert len(health.components) == 1
        assert health.components[0].status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_unhealthy_component(self, checker):
        """Unhealthy component makes system unhealthy."""
        async def unhealthy_check():
            return ComponentHealth(
                name="test",
                status=HealthStatus.UNHEALTHY,
                message="Connection failed",
            )
        
        checker.register("test", unhealthy_check)
        health = await checker.check_all()
        
        assert health.status == HealthStatus.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_degraded_component(self, checker):
        """Degraded component makes system degraded."""
        async def degraded_check():
            return ComponentHealth(
                name="test",
                status=HealthStatus.DEGRADED,
            )
        
        checker.register("test", degraded_check)
        health = await checker.check_all()
        
        assert health.status == HealthStatus.DEGRADED
    
    @pytest.mark.asyncio
    async def test_mixed_status(self, checker):
        """Unhealthy takes precedence over degraded."""
        async def healthy():
            return ComponentHealth(name="a", status=HealthStatus.HEALTHY)
        
        async def degraded():
            return ComponentHealth(name="b", status=HealthStatus.DEGRADED)
        
        async def unhealthy():
            return ComponentHealth(name="c", status=HealthStatus.UNHEALTHY)
        
        checker.register("a", healthy)
        checker.register("b", degraded)
        checker.register("c", unhealthy)
        
        health = await checker.check_all()
        
        assert health.status == HealthStatus.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_check_handles_exception(self, checker):
        """Handles exception in health check."""
        async def failing_check():
            raise RuntimeError("Check failed")
        
        checker.register("failing", failing_check)
        health = await checker.check_all()
        
        assert health.status == HealthStatus.UNHEALTHY
        assert "Check failed" in health.components[0].message
    
    @pytest.mark.asyncio
    async def test_check_component(self, checker):
        """Can check single component."""
        async def healthy():
            return ComponentHealth(name="test", status=HealthStatus.HEALTHY)
        
        checker.register("test", healthy)
        result = await checker.check_component("test")
        
        assert result.status == HealthStatus.HEALTHY
        assert result.latency_ms is not None
    
    @pytest.mark.asyncio
    async def test_check_unknown_component(self, checker):
        """Returns unhealthy for unknown component."""
        result = await checker.check_component("unknown")
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "Unknown" in result.message
    
    @pytest.mark.asyncio
    async def test_unregister(self, checker):
        """Can unregister check."""
        async def check():
            return ComponentHealth(name="test", status=HealthStatus.HEALTHY)
        
        checker.register("test", check)
        checker.unregister("test")
        
        health = await checker.check_all()
        assert len(health.components) == 0
    
    @pytest.mark.asyncio
    async def test_check_ready(self, checker):
        """Ready check returns boolean."""
        async def healthy():
            return ComponentHealth(name="test", status=HealthStatus.HEALTHY)
        
        checker.register("test", healthy)
        
        assert await checker.check_ready() is True
    
    @pytest.mark.asyncio
    async def test_check_live(self, checker):
        """Live check returns True."""
        assert await checker.check_live() is True
    
    @pytest.mark.asyncio
    async def test_uptime(self, checker):
        """Reports uptime."""
        health = await checker.check_all()
        
        assert health.uptime_seconds >= 0
    
    @pytest.mark.asyncio
    async def test_version(self, checker):
        """Reports version."""
        health = await checker.check_all()
        
        assert health.version == "1.0.0"
