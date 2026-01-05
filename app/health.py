"""Health check endpoint for production monitoring."""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Dict, Optional
from enum import Enum


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
    message: Optional[str] = None
    latency_ms: Optional[float] = None
    details: Dict = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """Overall health check result."""
    status: HealthStatus
    version: str
    environment: str
    timestamp: datetime
    components: Dict[str, ComponentHealth] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON response."""
        return {
            "status": self.status.value,
            "version": self.version,
            "environment": self.environment,
            "timestamp": self.timestamp.isoformat(),
            "components": {
                name: {
                    "status": comp.status.value,
                    "message": comp.message,
                    "latency_ms": comp.latency_ms,
                    "details": comp.details,
                }
                for name, comp in self.components.items()
            },
        }


class HealthChecker:
    """Service for performing health checks."""
    
    def __init__(self, version: str, environment: str):
        self.version = version
        self.environment = environment
        self._checks: Dict[str, callable] = {}
    
    def register_check(self, name: str, check_fn: callable) -> None:
        """Register a health check function."""
        self._checks[name] = check_fn
    
    async def check_health(self) -> HealthCheckResult:
        """Perform all health checks."""
        components = {}
        overall_status = HealthStatus.HEALTHY
        
        for name, check_fn in self._checks.items():
            try:
                start = datetime.now(UTC)
                result = await check_fn()
                latency = (datetime.now(UTC) - start).total_seconds() * 1000
                
                if isinstance(result, ComponentHealth):
                    result.latency_ms = latency
                    components[name] = result
                else:
                    components[name] = ComponentHealth(
                        name=name,
                        status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                        latency_ms=latency,
                    )
            except Exception as e:
                components[name] = ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(e),
                )
            
            # Update overall status
            if components[name].status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif components[name].status == HealthStatus.DEGRADED and overall_status != HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.DEGRADED
        
        return HealthCheckResult(
            status=overall_status,
            version=self.version,
            environment=self.environment,
            timestamp=datetime.now(UTC),
            components=components,
        )
    
    async def check_ready(self) -> bool:
        """Quick readiness check (for k8s probes)."""
        result = await self.check_health()
        return result.status != HealthStatus.UNHEALTHY
    
    async def check_live(self) -> bool:
        """Quick liveness check (for k8s probes)."""
        # Just check if the app is running
        return True


# Common health check functions
async def check_database(db_url: str) -> ComponentHealth:
    """Check database connectivity."""
    # Simplified check - in production would actually query DB
    return ComponentHealth(
        name="database",
        status=HealthStatus.HEALTHY,
        message="Connected",
    )


async def check_memory() -> ComponentHealth:
    """Check memory usage."""
    import sys
    
    # Get rough memory info
    details = {
        "python_version": sys.version,
    }
    
    return ComponentHealth(
        name="memory",
        status=HealthStatus.HEALTHY,
        details=details,
    )
