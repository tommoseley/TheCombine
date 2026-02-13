"""Tests for metrics collection."""

import pytest
from decimal import Decimal

from app.observability.metrics import (
    ExecutionMetrics,
    WorkflowMetrics,
    MetricsCollector,
    get_metrics_collector,
    reset_metrics_collector,
)


class TestExecutionMetrics:
    """Tests for ExecutionMetrics."""
    
    def test_success_rate_no_executions(self):
        """Success rate is 0 with no executions."""
        metrics = ExecutionMetrics()
        assert metrics.success_rate == 0.0
    
    def test_success_rate_all_success(self):
        """Success rate is 1.0 with all successes."""
        metrics = ExecutionMetrics(
            executions_completed=10,
            executions_failed=0,
        )
        assert metrics.success_rate == 1.0
    
    def test_success_rate_mixed(self):
        """Success rate calculates correctly."""
        metrics = ExecutionMetrics(
            executions_completed=8,
            executions_failed=2,
        )
        assert metrics.success_rate == 0.8
    
    def test_avg_latency_no_calls(self):
        """Average latency is 0 with no calls."""
        metrics = ExecutionMetrics()
        assert metrics.avg_latency_ms == 0.0
    
    def test_avg_latency_calculates(self):
        """Average latency calculates correctly."""
        metrics = ExecutionMetrics(
            llm_calls_total=10,
            total_latency_ms=5000.0,
        )
        assert metrics.avg_latency_ms == 500.0


class TestWorkflowMetrics:
    """Tests for WorkflowMetrics."""
    
    def test_avg_duration(self):
        """Average duration calculates correctly."""
        metrics = WorkflowMetrics(
            workflow_id="test",
            completions=5,
            total_duration_ms=10000.0,
        )
        assert metrics.avg_duration_ms == 2000.0
    
    def test_avg_cost(self):
        """Average cost calculates correctly."""
        metrics = WorkflowMetrics(
            workflow_id="test",
            completions=4,
            total_cost_usd=Decimal("2.00"),
        )
        assert metrics.avg_cost_usd == Decimal("0.50")


class TestMetricsCollector:
    """Tests for MetricsCollector."""
    
    @pytest.fixture
    def collector(self):
        return MetricsCollector()
    
    def test_record_execution_start(self, collector):
        """Records execution start."""
        collector.record_execution_start("wf-1")
        
        metrics = collector.get_metrics()
        assert metrics.executions_started == 1
    
    def test_record_execution_complete(self, collector):
        """Records execution completion."""
        collector.record_execution_start("wf-1")
        collector.record_execution_complete("wf-1", 1000.0, Decimal("0.10"))
        
        metrics = collector.get_metrics()
        assert metrics.executions_completed == 1
        assert metrics.total_cost_usd == Decimal("0.10")
    
    def test_record_execution_failed(self, collector):
        """Records execution failure."""
        collector.record_execution_start("wf-1")
        collector.record_execution_failed("wf-1")
        
        metrics = collector.get_metrics()
        assert metrics.executions_failed == 1
    
    def test_record_llm_call(self, collector):
        """Records LLM call."""
        collector.record_llm_call(
            input_tokens=1000,
            output_tokens=500,
            latency_ms=1500.0,
            cost_usd=Decimal("0.05"),
        )
        
        metrics = collector.get_metrics()
        assert metrics.llm_calls_total == 1
        assert metrics.total_input_tokens == 1000
        assert metrics.total_output_tokens == 500
    
    def test_record_llm_call_with_error(self, collector):
        """Records LLM call with error."""
        collector.record_llm_call(
            input_tokens=100,
            output_tokens=0,
            latency_ms=100.0,
            cost_usd=Decimal("0"),
            error=True,
        )
        
        metrics = collector.get_metrics()
        assert metrics.llm_calls_failed == 1
    
    def test_workflow_metrics(self, collector):
        """Tracks per-workflow metrics."""
        collector.record_execution_start("wf-1")
        collector.record_execution_complete("wf-1", 1000.0, Decimal("0.10"))
        collector.record_execution_start("wf-1")
        collector.record_execution_complete("wf-1", 2000.0, Decimal("0.20"))
        
        wm = collector.get_workflow_metrics("wf-1")
        
        assert wm is not None
        assert wm.executions == 2
        assert wm.completions == 2
        assert wm.total_cost_usd == Decimal("0.30")
    
    def test_get_all_workflow_metrics(self, collector):
        """Gets all workflow metrics."""
        collector.record_execution_start("wf-1")
        collector.record_execution_start("wf-2")
        
        all_metrics = collector.get_all_workflow_metrics()
        
        assert len(all_metrics) == 2
        workflow_ids = {m.workflow_id for m in all_metrics}
        assert workflow_ids == {"wf-1", "wf-2"}
    
    def test_reset(self, collector):
        """Reset clears all metrics."""
        collector.record_execution_start("wf-1")
        collector.record_llm_call(100, 50, 100.0, Decimal("0.01"))
        
        collector.reset()
        
        metrics = collector.get_metrics()
        assert metrics.executions_started == 0
        assert metrics.llm_calls_total == 0


class TestGlobalCollector:
    """Tests for global metrics collector."""
    
    def setup_method(self):
        reset_metrics_collector()
    
    def test_get_metrics_collector_singleton(self):
        """Returns same instance."""
        c1 = get_metrics_collector()
        c2 = get_metrics_collector()
        
        assert c1 is c2
    
    def test_reset_creates_new(self):
        """Reset creates new collector."""
        c1 = get_metrics_collector()
        reset_metrics_collector()
        c2 = get_metrics_collector()
        
        assert c1 is not c2
