"""Observability module for The Combine."""

from app.observability.logging import (
    JSONFormatter,
    ContextLogger,
    configure_logging,
    get_logger,
)
from app.observability.metrics import (
    ExecutionMetrics,
    WorkflowMetrics,
    MetricsCollector,
    get_metrics_collector,
    reset_metrics_collector,
)
from app.observability.health import (
    HealthStatus,
    ComponentHealth,
    SystemHealth,
    HealthChecker,
    make_database_check,
    make_http_check,
)

__all__ = [
    # Logging
    "JSONFormatter",
    "ContextLogger",
    "configure_logging",
    "get_logger",
    # Metrics
    "ExecutionMetrics",
    "WorkflowMetrics",
    "MetricsCollector",
    "get_metrics_collector",
    "reset_metrics_collector",
    # Health
    "HealthStatus",
    "ComponentHealth",
    "SystemHealth",
    "HealthChecker",
    "make_database_check",
    "make_http_check",
]
