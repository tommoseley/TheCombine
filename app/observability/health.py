"""Health check service for The Combine."""

import time
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Awaitable


class HealthStatus(str, Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status of a single component."""
    name: str
    status: HealthStatus
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class SystemHealth:
    """Overall system health."""
    status: HealthStatus
    components: List[ComponentHealth]
    version: str = "unknown"
    uptime_seconds: float = 0.0
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "status": self.status.value,
            "version": self.version,
            "uptime_seconds": self.uptime_seconds,
            "checked_at": self.checked_at.isoformat(),
            "components": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "latency_ms": c.latency_ms,
                    "message": c.message,
                    "details": c.details,
                }
                for c in self.components
            ],
        }


# Type for health check functions
HealthCheckFn = Callable[[], Awaitable[ComponentHealth]]


class HealthChecker:
    """
    Health check service.
    
    Manages component health checks and aggregates results.
    """
    
    def __init__(
        self,
        version: str = "unknown",
        start_time: Optional[datetime] = None,
    ):
        self._version = version
        self._start_time = start_time or datetime.now(UTC)
        self._checks: Dict[str, HealthCheckFn] = {}
    
    def register(self, name: str, check_fn: HealthCheckFn) -> None:
        """Register a health check function."""
        self._checks[name] = check_fn
    
    def unregister(self, name: str) -> None:
        """Unregister a health check."""
        self._checks.pop(name, None)
    
    async def check_component(self, name: str) -> ComponentHealth:
        """Run a single component health check."""
        if name not in self._checks:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Unknown component: {name}",
            )
        
        start = time.perf_counter()
        try:
            result = await self._checks[name]()
            result.latency_ms = (time.perf_counter() - start) * 1000
            return result
        except Exception as e:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.perf_counter() - start) * 1000,
                message=str(e),
            )
    
    async def check_all(self) -> SystemHealth:
        """Run all health checks and aggregate results."""
        components = []
        
        for name in self._checks:
            result = await self.check_component(name)
            components.append(result)
        
        # Determine overall status
        statuses = [c.status for c in components]
        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        elif not components:
            overall = HealthStatus.HEALTHY  # No checks = healthy
        else:
            overall = HealthStatus.HEALTHY
        
        uptime = (datetime.now(UTC) - self._start_time).total_seconds()
        
        return SystemHealth(
            status=overall,
            components=components,
            version=self._version,
            uptime_seconds=uptime,
        )
    
    async def check_ready(self) -> bool:
        """Quick readiness check - all components healthy."""
        health = await self.check_all()
        return health.status == HealthStatus.HEALTHY
    
    async def check_live(self) -> bool:
        """Quick liveness check - application is running."""
        return True  # If we can execute this, we're alive


# Factory functions for common health checks

async def create_database_check(db_session_factory) -> ComponentHealth:
    """Create a database health check."""
    try:
        async with db_session_factory() as session:
            start = time.perf_counter()
            await session.execute("SELECT 1")
            latency = (time.perf_counter() - start) * 1000
            
            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
            )
    except Exception as e:
        return ComponentHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=str(e),
        )


def make_database_check(db_session_factory) -> HealthCheckFn:
    """Make a database health check function."""
    async def check() -> ComponentHealth:
        return await create_database_check(db_session_factory)
    return check


async def create_http_check(
    url: str,
    name: str = "http",
    timeout: float = 5.0,
) -> ComponentHealth:
    """Create an HTTP endpoint health check."""
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            start = time.perf_counter()
            response = await client.get(url)
            latency = (time.perf_counter() - start) * 1000
            
            if response.status_code < 400:
                return ComponentHealth(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    details={"status_code": response.status_code},
                )
            else:
                return ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    latency_ms=latency,
                    message=f"HTTP {response.status_code}",
                )
    except Exception as e:
        return ComponentHealth(
            name=name,
            status=HealthStatus.UNHEALTHY,
            message=str(e),
        )


def make_http_check(url: str, name: str = "http", timeout: float = 5.0) -> HealthCheckFn:
    """Make an HTTP health check function."""
    async def check() -> ComponentHealth:
        return await create_http_check(url, name, timeout)
    return check
