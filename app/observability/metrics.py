"""Metrics collection for The Combine."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from threading import Lock
from typing import Dict, List, Optional


@dataclass
class ExecutionMetrics:
    """Aggregated execution metrics."""
    executions_started: int = 0
    executions_completed: int = 0
    executions_failed: int = 0
    executions_cancelled: int = 0
    llm_calls_total: int = 0
    llm_calls_failed: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: Decimal = Decimal("0")
    total_latency_ms: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate execution success rate."""
        total = self.executions_completed + self.executions_failed
        if total == 0:
            return 0.0
        return self.executions_completed / total
    
    @property
    def avg_latency_ms(self) -> float:
        """Calculate average LLM call latency."""
        if self.llm_calls_total == 0:
            return 0.0
        return self.total_latency_ms / self.llm_calls_total
    
    @property
    def llm_error_rate(self) -> float:
        """Calculate LLM error rate."""
        if self.llm_calls_total == 0:
            return 0.0
        return self.llm_calls_failed / self.llm_calls_total


@dataclass
class WorkflowMetrics:
    """Metrics for a specific workflow."""
    workflow_id: str
    executions: int = 0
    completions: int = 0
    failures: int = 0
    total_duration_ms: float = 0.0
    total_cost_usd: Decimal = Decimal("0")
    
    @property
    def avg_duration_ms(self) -> float:
        """Average execution duration."""
        if self.completions == 0:
            return 0.0
        return self.total_duration_ms / self.completions
    
    @property
    def avg_cost_usd(self) -> Decimal:
        """Average execution cost."""
        if self.completions == 0:
            return Decimal("0")
        return self.total_cost_usd / self.completions


@dataclass
class HealthStatus:
    """Health check status for a component."""
    name: str
    healthy: bool
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MetricsCollector:
    """
    Thread-safe metrics collector.
    
    Collects and aggregates metrics for executions and LLM calls.
    """
    
    def __init__(self):
        self._lock = Lock()
        self._metrics = ExecutionMetrics()
        self._workflow_metrics: Dict[str, WorkflowMetrics] = {}
        self._started_at = datetime.now(timezone.utc)
    
    def record_execution_start(self, workflow_id: str) -> None:
        """Record an execution starting."""
        with self._lock:
            self._metrics.executions_started += 1
            
            if workflow_id not in self._workflow_metrics:
                self._workflow_metrics[workflow_id] = WorkflowMetrics(workflow_id)
            self._workflow_metrics[workflow_id].executions += 1
    
    def record_execution_complete(
        self,
        workflow_id: str,
        duration_ms: float,
        cost_usd: Decimal,
    ) -> None:
        """Record an execution completing successfully."""
        with self._lock:
            self._metrics.executions_completed += 1
            self._metrics.total_cost_usd += cost_usd
            
            if workflow_id in self._workflow_metrics:
                wm = self._workflow_metrics[workflow_id]
                wm.completions += 1
                wm.total_duration_ms += duration_ms
                wm.total_cost_usd += cost_usd
    
    def record_execution_failed(self, workflow_id: str) -> None:
        """Record an execution failing."""
        with self._lock:
            self._metrics.executions_failed += 1
            
            if workflow_id in self._workflow_metrics:
                self._workflow_metrics[workflow_id].failures += 1
    
    def record_execution_cancelled(self, workflow_id: str) -> None:
        """Record an execution being cancelled."""
        with self._lock:
            self._metrics.executions_cancelled += 1
    
    def record_llm_call(
        self,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        cost_usd: Decimal,
        error: bool = False,
    ) -> None:
        """Record an LLM call."""
        with self._lock:
            self._metrics.llm_calls_total += 1
            self._metrics.total_input_tokens += input_tokens
            self._metrics.total_output_tokens += output_tokens
            self._metrics.total_latency_ms += latency_ms
            self._metrics.total_cost_usd += cost_usd
            
            if error:
                self._metrics.llm_calls_failed += 1
    
    def get_metrics(self) -> ExecutionMetrics:
        """Get current metrics snapshot."""
        with self._lock:
            return ExecutionMetrics(
                executions_started=self._metrics.executions_started,
                executions_completed=self._metrics.executions_completed,
                executions_failed=self._metrics.executions_failed,
                executions_cancelled=self._metrics.executions_cancelled,
                llm_calls_total=self._metrics.llm_calls_total,
                llm_calls_failed=self._metrics.llm_calls_failed,
                total_input_tokens=self._metrics.total_input_tokens,
                total_output_tokens=self._metrics.total_output_tokens,
                total_cost_usd=self._metrics.total_cost_usd,
                total_latency_ms=self._metrics.total_latency_ms,
            )
    
    def get_workflow_metrics(self, workflow_id: str) -> Optional[WorkflowMetrics]:
        """Get metrics for a specific workflow."""
        with self._lock:
            wm = self._workflow_metrics.get(workflow_id)
            if wm:
                return WorkflowMetrics(
                    workflow_id=wm.workflow_id,
                    executions=wm.executions,
                    completions=wm.completions,
                    failures=wm.failures,
                    total_duration_ms=wm.total_duration_ms,
                    total_cost_usd=wm.total_cost_usd,
                )
            return None
    
    def get_all_workflow_metrics(self) -> List[WorkflowMetrics]:
        """Get metrics for all workflows."""
        with self._lock:
            return [
                WorkflowMetrics(
                    workflow_id=wm.workflow_id,
                    executions=wm.executions,
                    completions=wm.completions,
                    failures=wm.failures,
                    total_duration_ms=wm.total_duration_ms,
                    total_cost_usd=wm.total_cost_usd,
                )
                for wm in self._workflow_metrics.values()
            ]
    
    def uptime_seconds(self) -> float:
        """Get collector uptime in seconds."""
        return (datetime.now(timezone.utc) - self._started_at).total_seconds()
    
    def reset(self) -> None:
        """Reset all metrics (for testing)."""
        with self._lock:
            self._metrics = ExecutionMetrics()
            self._workflow_metrics.clear()
            self._started_at = datetime.now(timezone.utc)


# Global metrics collector instance
_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector


def reset_metrics_collector() -> None:
    """Reset the global metrics collector (for testing)."""
    global _collector
    _collector = None
