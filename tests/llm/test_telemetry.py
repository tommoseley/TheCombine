"""Tests for LLM telemetry service."""

import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.llm.telemetry import (
    CostCalculator,
    MODEL_PRICING,
    LLMCallRecord,
    CostSummary,
    InMemoryTelemetryStore,
    TelemetryService,
)


class TestCostCalculator:
    """Tests for CostCalculator."""
    
    def test_calculate_sonnet_cost(self):
        """Calculates Sonnet costs correctly."""
        calc = CostCalculator()
        
        # 1000 input, 500 output
        cost = calc.calculate_cost(
            model="claude-sonnet-4-20250514",
            input_tokens=1000,
            output_tokens=500,
        )
        
        # Input: 1000/1M * $3 = $0.003
        # Output: 500/1M * $15 = $0.0075
        expected = Decimal("0.003") + Decimal("0.0075")
        assert cost == expected
    
    def test_calculate_haiku_cost(self):
        """Calculates Haiku costs correctly."""
        calc = CostCalculator()
        
        cost = calc.calculate_cost(
            model="claude-haiku-4-20250514",
            input_tokens=1000,
            output_tokens=500,
        )
        
        # Input: 1000/1M * $0.25 = $0.00025
        # Output: 500/1M * $1.25 = $0.000625
        expected = Decimal("0.00025") + Decimal("0.000625")
        assert cost == expected
    
    def test_calculate_with_cached_tokens(self):
        """Cached tokens use discounted rate."""
        calc = CostCalculator()
        
        cost = calc.calculate_cost(
            model="sonnet",
            input_tokens=500,
            output_tokens=500,
            cached_input_tokens=500,
        )
        
        # Input: 500/1M * $3 = $0.0015
        # Output: 500/1M * $15 = $0.0075
        # Cached: 500/1M * $0.30 = $0.00015
        expected = Decimal("0.0015") + Decimal("0.0075") + Decimal("0.00015")
        assert cost == expected
    
    def test_calculate_unknown_model_defaults(self):
        """Unknown model defaults to sonnet pricing."""
        calc = CostCalculator()
        
        cost = calc.calculate_cost(
            model="unknown-model",
            input_tokens=1000,
            output_tokens=500,
        )
        
        # Should use default pricing
        assert cost > Decimal("0")
    
    def test_get_model_pricing(self):
        """Can get pricing for a model."""
        calc = CostCalculator()
        
        pricing = calc.get_model_pricing("sonnet")
        
        assert pricing is not None
        assert "input" in pricing
        assert "output" in pricing


class TestLLMCallRecord:
    """Tests for LLMCallRecord."""
    
    def test_create_record(self):
        """Can create call record."""
        record = LLMCallRecord(
            call_id=uuid4(),
            execution_id=uuid4(),
            step_id="step-1",
            model="sonnet",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=1500.0,
        )
        
        assert record.cached is False
        assert record.retry_count == 0


class TestCostSummary:
    """Tests for CostSummary."""
    
    def test_empty_summary(self):
        """Empty summary has zeroes."""
        summary = CostSummary.empty()
        
        assert summary.total_cost_usd == Decimal("0")
        assert summary.call_count == 0
        assert summary.cache_hit_rate == 0.0


class TestInMemoryTelemetryStore:
    """Tests for InMemoryTelemetryStore."""
    
    @pytest.fixture
    def store(self):
        return InMemoryTelemetryStore()
    
    @pytest.mark.asyncio
    async def test_record_and_get_by_execution(self, store):
        """Can record and retrieve by execution."""
        execution_id = uuid4()
        record = LLMCallRecord(
            call_id=uuid4(),
            execution_id=execution_id,
            step_id="step-1",
            model="sonnet",
            input_tokens=100,
            output_tokens=50,
            latency_ms=500.0,
        )
        
        await store.record_call(record)
        calls = await store.get_execution_calls(execution_id)
        
        assert len(calls) == 1
        assert calls[0].step_id == "step-1"
    
    @pytest.mark.asyncio
    async def test_get_by_date(self, store):
        """Can retrieve by date."""
        record = LLMCallRecord(
            call_id=uuid4(),
            execution_id=uuid4(),
            step_id="step-1",
            model="sonnet",
            input_tokens=100,
            output_tokens=50,
            latency_ms=500.0,
        )
        
        await store.record_call(record)
        calls = await store.get_calls_by_date(datetime.now(timezone.utc).date())
        
        assert len(calls) == 1


class TestTelemetryService:
    """Tests for TelemetryService."""
    
    @pytest.fixture
    def service(self):
        store = InMemoryTelemetryStore()
        return TelemetryService(store)
    
    @pytest.mark.asyncio
    async def test_log_call_calculates_cost(self, service):
        """Logging a call calculates cost."""
        record = await service.log_call(
            call_id=uuid4(),
            execution_id=uuid4(),
            step_id="step-1",
            model="sonnet",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=1500.0,
        )
        
        assert record.cost_usd > Decimal("0")
    
    @pytest.mark.asyncio
    async def test_get_execution_summary(self, service):
        """Can get execution summary."""
        execution_id = uuid4()
        
        # Log multiple calls
        for i in range(3):
            await service.log_call(
                call_id=uuid4(),
                execution_id=execution_id,
                step_id=f"step-{i}",
                model="sonnet",
                input_tokens=1000,
                output_tokens=500,
                latency_ms=1000.0,
            )
        
        summary = await service.get_execution_summary(execution_id)
        
        assert summary.call_count == 3
        assert summary.input_tokens == 3000
        assert summary.output_tokens == 1500
    
    @pytest.mark.asyncio
    async def test_get_execution_summary_with_errors(self, service):
        """Summary includes error count."""
        execution_id = uuid4()
        
        # Log success
        await service.log_call(
            call_id=uuid4(),
            execution_id=execution_id,
            step_id="step-1",
            model="sonnet",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=1000.0,
        )
        
        # Log error
        await service.log_call(
            call_id=uuid4(),
            execution_id=execution_id,
            step_id="step-2",
            model="sonnet",
            input_tokens=1000,
            output_tokens=0,
            latency_ms=500.0,
            error_type="rate_limit",
            error_message="Too many requests",
        )
        
        summary = await service.get_execution_summary(execution_id)
        
        assert summary.call_count == 2
        assert summary.error_count == 1
    
    @pytest.mark.asyncio
    async def test_get_daily_summary(self, service):
        """Can get daily summary."""
        await service.log_call(
            call_id=uuid4(),
            execution_id=uuid4(),
            step_id="step-1",
            model="sonnet",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=1000.0,
        )
        
        summary = await service.get_daily_summary(datetime.now(timezone.utc).date())
        
        assert summary.call_count == 1
    
    @pytest.mark.asyncio
    async def test_get_model_usage(self, service):
        """Can get usage breakdown by model."""
        execution_id = uuid4()
        
        # Sonnet calls
        await service.log_call(
            call_id=uuid4(),
            execution_id=execution_id,
            step_id="step-1",
            model="sonnet",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=1000.0,
        )
        
        # Haiku call
        await service.log_call(
            call_id=uuid4(),
            execution_id=execution_id,
            step_id="step-2",
            model="haiku",
            input_tokens=500,
            output_tokens=200,
            latency_ms=200.0,
        )
        
        usage = await service.get_model_usage(execution_id)
        
        assert len(usage) == 2
        models = {u.model for u in usage}
        assert "sonnet" in models
        assert "haiku" in models
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate(self, service):
        """Summary calculates cache hit rate."""
        execution_id = uuid4()
        
        # 2 cached, 1 not
        await service.log_call(
            call_id=uuid4(),
            execution_id=execution_id,
            step_id="step-1",
            model="sonnet",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=1000.0,
            cached=True,
        )
        await service.log_call(
            call_id=uuid4(),
            execution_id=execution_id,
            step_id="step-2",
            model="sonnet",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=1000.0,
            cached=True,
        )
        await service.log_call(
            call_id=uuid4(),
            execution_id=execution_id,
            step_id="step-3",
            model="sonnet",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=1000.0,
            cached=False,
        )
        
        summary = await service.get_execution_summary(execution_id)
        
        assert summary.cache_hit_rate == pytest.approx(2/3)

