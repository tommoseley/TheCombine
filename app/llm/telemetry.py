"""LLM telemetry service for cost tracking and metrics."""

from dataclasses import dataclass, field
from datetime import datetime, date, UTC
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID


# Model pricing per 1M tokens (as of Jan 2026)
MODEL_PRICING: Dict[str, Dict[str, Decimal]] = {
    "claude-sonnet-4-20250514": {
        "input": Decimal("3.00"),
        "output": Decimal("15.00"),
        "cached_input": Decimal("0.30"),  # 90% discount for cached
    },
    "claude-haiku-4-20250514": {
        "input": Decimal("0.25"),
        "output": Decimal("1.25"),
        "cached_input": Decimal("0.025"),
    },
    "claude-opus-4-20250514": {
        "input": Decimal("15.00"),
        "output": Decimal("75.00"),
        "cached_input": Decimal("1.50"),
    },
    # Aliases
    "sonnet": {
        "input": Decimal("3.00"),
        "output": Decimal("15.00"),
        "cached_input": Decimal("0.30"),
    },
    "haiku": {
        "input": Decimal("0.25"),
        "output": Decimal("1.25"),
        "cached_input": Decimal("0.025"),
    },
}


@dataclass
class LLMCallRecord:
    """Record of a single LLM call for telemetry."""
    call_id: UUID
    execution_id: UUID
    step_id: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cached: bool = False
    cost_usd: Decimal = Decimal("0")
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0


@dataclass
class CostSummary:
    """Summary of costs for a period or execution."""
    total_cost_usd: Decimal
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    call_count: int
    error_count: int
    avg_latency_ms: float
    cache_hit_rate: float
    
    @classmethod
    def empty(cls) -> "CostSummary":
        """Create an empty summary."""
        return cls(
            total_cost_usd=Decimal("0"),
            input_tokens=0,
            output_tokens=0,
            cached_tokens=0,
            call_count=0,
            error_count=0,
            avg_latency_ms=0.0,
            cache_hit_rate=0.0,
        )


@dataclass
class ModelUsage:
    """Usage statistics for a specific model."""
    model: str
    call_count: int
    input_tokens: int
    output_tokens: int
    total_cost_usd: Decimal
    avg_latency_ms: float


class CostCalculator:
    """Calculates costs for LLM usage."""
    
    def __init__(self, pricing: Optional[Dict[str, Dict[str, Decimal]]] = None):
        """
        Initialize calculator.
        
        Args:
            pricing: Optional custom pricing. Uses MODEL_PRICING if not provided.
        """
        self._pricing = pricing or MODEL_PRICING
    
    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_input_tokens: int = 0,
    ) -> Decimal:
        """
        Calculate cost for an LLM call.
        
        Args:
            model: Model name
            input_tokens: Non-cached input tokens
            output_tokens: Output tokens
            cached_input_tokens: Cached input tokens (discounted)
            
        Returns:
            Cost in USD
        """
        pricing = self._pricing.get(model)
        if not pricing:
            # Try to find by partial match
            for name, p in self._pricing.items():
                if name in model or model in name:
                    pricing = p
                    break
        
        if not pricing:
            # Default to sonnet pricing if unknown
            pricing = self._pricing.get("sonnet", {
                "input": Decimal("3.00"),
                "output": Decimal("15.00"),
                "cached_input": Decimal("0.30"),
            })
        
        # Calculate cost (per 1M tokens)
        input_cost = (Decimal(input_tokens) / Decimal(1_000_000)) * pricing["input"]
        output_cost = (Decimal(output_tokens) / Decimal(1_000_000)) * pricing["output"]
        cached_cost = (Decimal(cached_input_tokens) / Decimal(1_000_000)) * pricing.get("cached_input", pricing["input"])
        
        return input_cost + output_cost + cached_cost
    
    def get_model_pricing(self, model: str) -> Optional[Dict[str, Decimal]]:
        """Get pricing for a model."""
        return self._pricing.get(model)


class InMemoryTelemetryStore:
    """In-memory storage for telemetry records (for testing)."""
    
    def __init__(self):
        self._calls: Dict[UUID, LLMCallRecord] = {}
        self._by_execution: Dict[UUID, List[UUID]] = {}
        self._by_date: Dict[date, List[UUID]] = {}
    
    async def record_call(self, record: LLMCallRecord) -> None:
        """Record an LLM call."""
        self._calls[record.call_id] = record
        
        # Index by execution
        if record.execution_id not in self._by_execution:
            self._by_execution[record.execution_id] = []
        self._by_execution[record.execution_id].append(record.call_id)
        
        # Index by date
        call_date = record.started_at.date()
        if call_date not in self._by_date:
            self._by_date[call_date] = []
        self._by_date[call_date].append(record.call_id)
    
    async def get_execution_calls(self, execution_id: UUID) -> List[LLMCallRecord]:
        """Get all calls for an execution."""
        call_ids = self._by_execution.get(execution_id, [])
        return [self._calls[cid] for cid in call_ids if cid in self._calls]
    
    async def get_calls_by_date(self, target_date: date) -> List[LLMCallRecord]:
        """Get all calls for a date."""
        call_ids = self._by_date.get(target_date, [])
        return [self._calls[cid] for cid in call_ids if cid in self._calls]
    
    def clear(self) -> None:
        """Clear all records."""
        self._calls.clear()
        self._by_execution.clear()
        self._by_date.clear()


class TelemetryService:
    """Service for LLM telemetry and cost tracking."""
    
    def __init__(
        self,
        store: InMemoryTelemetryStore,
        calculator: Optional[CostCalculator] = None,
    ):
        """
        Initialize telemetry service.
        
        Args:
            store: Telemetry storage
            calculator: Cost calculator
        """
        self._store = store
        self._calculator = calculator or CostCalculator()
    
    async def log_call(
        self,
        call_id: UUID,
        execution_id: UUID,
        step_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        cached: bool = False,
        cached_tokens: int = 0,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0,
    ) -> LLMCallRecord:
        """
        Log an LLM call with cost calculation.
        
        Args:
            call_id: Unique call identifier
            execution_id: Parent execution ID
            step_id: Workflow step ID
            model: Model used
            input_tokens: Input tokens (non-cached)
            output_tokens: Output tokens
            latency_ms: Call latency
            cached: Whether response was cached
            cached_tokens: Number of cached input tokens
            error_type: Error type if failed
            error_message: Error message if failed
            retry_count: Number of retries
            
        Returns:
            Created call record
        """
        cost = self._calculator.calculate_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_tokens,
        )
        
        record = LLMCallRecord(
            call_id=call_id,
            execution_id=execution_id,
            step_id=step_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cached=cached,
            cost_usd=cost,
            completed_at=datetime.now(UTC),
            error_type=error_type,
            error_message=error_message,
            retry_count=retry_count,
        )
        
        await self._store.record_call(record)
        return record
    
    async def get_execution_summary(self, execution_id: UUID) -> CostSummary:
        """Get cost summary for an execution."""
        calls = await self._store.get_execution_calls(execution_id)
        return self._summarize_calls(calls)
    
    async def get_daily_summary(self, target_date: date) -> CostSummary:
        """Get cost summary for a specific date."""
        calls = await self._store.get_calls_by_date(target_date)
        return self._summarize_calls(calls)
    
    async def get_model_usage(self, execution_id: UUID) -> List[ModelUsage]:
        """Get usage breakdown by model for an execution."""
        calls = await self._store.get_execution_calls(execution_id)
        
        by_model: Dict[str, List[LLMCallRecord]] = {}
        for call in calls:
            if call.model not in by_model:
                by_model[call.model] = []
            by_model[call.model].append(call)
        
        results = []
        for model, model_calls in by_model.items():
            total_latency = sum(c.latency_ms for c in model_calls)
            results.append(ModelUsage(
                model=model,
                call_count=len(model_calls),
                input_tokens=sum(c.input_tokens for c in model_calls),
                output_tokens=sum(c.output_tokens for c in model_calls),
                total_cost_usd=sum(c.cost_usd for c in model_calls),
                avg_latency_ms=total_latency / len(model_calls) if model_calls else 0,
            ))
        
        return results
    
    def _summarize_calls(self, calls: List[LLMCallRecord]) -> CostSummary:
        """Summarize a list of calls."""
        if not calls:
            return CostSummary.empty()
        
        total_cost = sum(c.cost_usd for c in calls)
        input_tokens = sum(c.input_tokens for c in calls)
        output_tokens = sum(c.output_tokens for c in calls)
        cached_count = sum(1 for c in calls if c.cached)
        error_count = sum(1 for c in calls if c.error_type)
        total_latency = sum(c.latency_ms for c in calls)
        
        return CostSummary(
            total_cost_usd=total_cost,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=0,  # Would need to track separately
            call_count=len(calls),
            error_count=error_count,
            avg_latency_ms=total_latency / len(calls),
            cache_hit_rate=cached_count / len(calls) if calls else 0.0,
        )


