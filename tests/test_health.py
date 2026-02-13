"""Tests for health check functionality."""

import pytest
from datetime import datetime, timezone

from app.health import (
    HealthStatus,
    ComponentHealth,
    HealthCheckResult,
    HealthChecker,
    check_memory,
)


class TestHealthStatus:
    """Tests for HealthStatus enum."""
    
    def test_healthy_status(self):
        """Healthy status has correct value."""
        assert HealthStatus.HEALTHY.value == "healthy"
    
    def test_degraded_status(self):
        """Degraded status has correct value."""
        assert HealthStatus.DEGRADED.value == "degraded"
    
    def test_unhealthy_status(self):
        """Unhealthy status has correct value."""
        assert HealthStatus.UNHEALTHY.value == "unhealthy"


class TestComponentHealth:
    """Tests for ComponentHealth dataclass."""
    
    def test_create_healthy_component(self):
        """Can create healthy component."""
        comp = ComponentHealth(
            name="test",
            status=HealthStatus.HEALTHY,
        )
        assert comp.name == "test"
        assert comp.status == HealthStatus.HEALTHY
    
    def test_component_with_details(self):
        """Can create component with details."""
        comp = ComponentHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            message="Connected",
            latency_ms=5.2,
            details={"pool_size": 10},
        )
        assert comp.message == "Connected"
        assert comp.latency_ms == 5.2
        assert comp.details["pool_size"] == 10


class TestHealthCheckResult:
    """Tests for HealthCheckResult dataclass."""
    
    def test_create_result(self):
        """Can create health check result."""
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            version="1.0.0",
            environment="test",
            timestamp=datetime.now(timezone.utc),
        )
        assert result.status == HealthStatus.HEALTHY
        assert result.version == "1.0.0"
    
    def test_to_dict(self):
        """to_dict produces valid dictionary."""
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            version="1.0.0",
            environment="test",
            timestamp=datetime.now(timezone.utc),
            components={
                "db": ComponentHealth(
                    name="db",
                    status=HealthStatus.HEALTHY,
                    latency_ms=5.0,
                ),
            },
        )
        
        d = result.to_dict()
        assert d["status"] == "healthy"
        assert d["version"] == "1.0.0"
        assert "db" in d["components"]
        assert d["components"]["db"]["status"] == "healthy"


class TestHealthChecker:
    """Tests for HealthChecker service."""
    
    @pytest.mark.asyncio
    async def test_check_health_no_checks(self):
        """Health check with no registered checks returns healthy."""
        checker = HealthChecker(version="1.0.0", environment="test")
        result = await checker.check_health()
        
        assert result.status == HealthStatus.HEALTHY
        assert result.version == "1.0.0"
        assert len(result.components) == 0
    
    @pytest.mark.asyncio
    async def test_register_and_run_check(self):
        """Can register and run a health check."""
        checker = HealthChecker(version="1.0.0", environment="test")
        
        async def always_healthy():
            return True
        
        checker.register_check("test", always_healthy)
        result = await checker.check_health()
        
        assert "test" in result.components
        assert result.components["test"].status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_unhealthy_check_affects_overall(self):
        """Unhealthy component makes overall status unhealthy."""
        checker = HealthChecker(version="1.0.0", environment="test")
        
        async def failing_check():
            return False
        
        checker.register_check("failing", failing_check)
        result = await checker.check_health()
        
        assert result.status == HealthStatus.UNHEALTHY
        assert result.components["failing"].status == HealthStatus.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_degraded_check_affects_overall(self):
        """Degraded component makes overall status degraded."""
        checker = HealthChecker(version="1.0.0", environment="test")
        
        async def degraded_check():
            return ComponentHealth(
                name="slow",
                status=HealthStatus.DEGRADED,
                message="High latency",
            )
        
        checker.register_check("slow", degraded_check)
        result = await checker.check_health()
        
        assert result.status == HealthStatus.DEGRADED
    
    @pytest.mark.asyncio
    async def test_exception_in_check(self):
        """Exception in check results in unhealthy component."""
        checker = HealthChecker(version="1.0.0", environment="test")
        
        async def failing_check():
            raise RuntimeError("Connection failed")
        
        checker.register_check("broken", failing_check)
        result = await checker.check_health()
        
        assert result.components["broken"].status == HealthStatus.UNHEALTHY
        assert "Connection failed" in result.components["broken"].message
    
    @pytest.mark.asyncio
    async def test_check_ready(self):
        """check_ready returns boolean based on health."""
        checker = HealthChecker(version="1.0.0", environment="test")
        
        # No checks = healthy = ready
        assert await checker.check_ready() is True
        
        # Add failing check
        async def failing():
            return False
        
        checker.register_check("fail", failing)
        assert await checker.check_ready() is False
    
    @pytest.mark.asyncio
    async def test_check_live(self):
        """check_live always returns True (app is running)."""
        checker = HealthChecker(version="1.0.0", environment="test")
        assert await checker.check_live() is True


class TestBuiltInChecks:
    """Tests for built-in health check functions."""
    
    @pytest.mark.asyncio
    async def test_check_memory(self):
        """Memory check returns healthy status."""
        result = await check_memory()
        
        assert result.status == HealthStatus.HEALTHY
        assert "python_version" in result.details
