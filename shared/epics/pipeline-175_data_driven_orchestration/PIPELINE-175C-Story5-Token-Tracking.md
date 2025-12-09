# Token Usage Tracking & Cost Reporting System

**Story:** PIPELINE-175C Story 5  
**Priority:** CRITICAL for optimization  
**Effort:** 4 hours  
**Dependencies:** PIPELINE-175A (database), PIPELINE-175B (LLMCaller)

---

## Goal

Enable real-time monitoring and optimization of LLM token usage and costs across all pipeline executions.

**Success Criteria:**
- Every LLM call tracked with input/output token counts
- Cost calculated per call, phase, pipeline, role
- Dashboard shows token metrics in real-time
- CLI tools for historical analysis
- Alerts when budgets exceeded

---

## Database Schema Changes

### Migration: 002_add_token_tracking.py

```python
"""
Add token usage tracking to pipeline_prompt_usage table.

Adds columns for token counts and cost calculation.
"""

from sqlalchemy import text

def upgrade():
    """Add token tracking columns."""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Add token count columns
        conn.execute(text("""
            ALTER TABLE pipeline_prompt_usage
            ADD COLUMN input_tokens INTEGER DEFAULT 0;
        """))
        
        conn.execute(text("""
            ALTER TABLE pipeline_prompt_usage
            ADD COLUMN output_tokens INTEGER DEFAULT 0;
        """))
        
        conn.execute(text("""
            ALTER TABLE pipeline_prompt_usage
            ADD COLUMN total_tokens INTEGER GENERATED ALWAYS AS 
                (input_tokens + output_tokens) STORED;
        """))
        
        conn.execute(text("""
            ALTER TABLE pipeline_prompt_usage
            ADD COLUMN cost_usd DECIMAL(10, 6) DEFAULT 0.00;
        """))
        
        conn.execute(text("""
            ALTER TABLE pipeline_prompt_usage
            ADD COLUMN model VARCHAR(64) DEFAULT 'claude-sonnet-4-20250514';
        """))
        
        conn.execute(text("""
            ALTER TABLE pipeline_prompt_usage
            ADD COLUMN execution_time_ms INTEGER DEFAULT 0;
        """))
        
        # Create index for reporting queries
        conn.execute(text("""
            CREATE INDEX idx_usage_pipeline_phase 
            ON pipeline_prompt_usage(pipeline_id, phase_name);
        """))
        
        conn.commit()
    
    print("✅ Added token tracking columns")
    print("✅ Created reporting indexes")

def downgrade():
    """Remove token tracking columns."""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        conn.execute(text("DROP INDEX idx_usage_pipeline_phase"))
        conn.execute(text("ALTER TABLE pipeline_prompt_usage DROP COLUMN execution_time_ms"))
        conn.execute(text("ALTER TABLE pipeline_prompt_usage DROP COLUMN model"))
        conn.execute(text("ALTER TABLE pipeline_prompt_usage DROP COLUMN cost_usd"))
        conn.execute(text("ALTER TABLE pipeline_prompt_usage DROP COLUMN total_tokens"))
        conn.execute(text("ALTER TABLE pipeline_prompt_usage DROP COLUMN output_tokens"))
        conn.execute(text("ALTER TABLE pipeline_prompt_usage DROP COLUMN input_tokens"))
        conn.commit()
    
    print("✅ Removed token tracking columns")
```

### Updated Schema

```sql
CREATE TABLE pipeline_prompt_usage (
    id VARCHAR(64) PRIMARY KEY,
    pipeline_id VARCHAR(64) NOT NULL,
    prompt_id VARCHAR(64) NOT NULL,
    role_name VARCHAR(64) NOT NULL,
    phase_name VARCHAR(64) NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- NEW: Token tracking
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER GENERATED ALWAYS AS (input_tokens + output_tokens) STORED,
    cost_usd DECIMAL(10, 6) DEFAULT 0.00,
    model VARCHAR(64) DEFAULT 'claude-sonnet-4-20250514',
    execution_time_ms INTEGER DEFAULT 0,
    
    FOREIGN KEY (pipeline_id) REFERENCES pipelines(pipeline_id),
    FOREIGN KEY (prompt_id) REFERENCES role_prompts(id)
);

CREATE INDEX idx_usage_pipeline_phase ON pipeline_prompt_usage(pipeline_id, phase_name);
CREATE INDEX idx_usage_role ON pipeline_prompt_usage(role_name);
CREATE INDEX idx_usage_date ON pipeline_prompt_usage(used_at);
```

---

## Pricing Model

### Anthropic Pricing (as of Dec 2025)

```python
# config.py
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Anthropic API Pricing (USD per million tokens)
    ANTHROPIC_INPUT_PRICE_PER_MTK: float = Field(
        default=3.00,  # $3 per million input tokens
        description="Anthropic input token price per million tokens"
    )
    
    ANTHROPIC_OUTPUT_PRICE_PER_MTK: float = Field(
        default=15.00,  # $15 per million output tokens
        description="Anthropic output token price per million tokens"
    )
```

### Cost Calculation

```python
def calculate_cost(input_tokens: int, output_tokens: int, model: str = "claude-sonnet-4") -> float:
    """
    Calculate cost in USD for token usage.
    
    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model name (for future multi-model support)
    
    Returns:
        Cost in USD (6 decimal places)
    """
    # Price per million tokens
    input_price = settings.ANTHROPIC_INPUT_PRICE_PER_MTK
    output_price = settings.ANTHROPIC_OUTPUT_PRICE_PER_MTK
    
    # Calculate cost
    input_cost = (input_tokens / 1_000_000) * input_price
    output_cost = (output_tokens / 1_000_000) * output_price
    total_cost = input_cost + output_cost
    
    return round(total_cost, 6)  # Store to 6 decimal places


# Example:
# Input: 10,000 tokens, Output: 2,000 tokens
# Cost = (10,000 / 1M * $3) + (2,000 / 1M * $15)
#      = $0.03 + $0.03
#      = $0.06
```

---

## Updated UsageRecorder

### Enhanced UsageRecord Dataclass

```python
@dataclass
class UsageRecord:
    """Prompt usage data to record."""
    pipeline_id: str
    prompt_id: str
    role_name: str
    phase_name: str
    
    # NEW: Token tracking
    input_tokens: int = 0
    output_tokens: int = 0
    execution_time_ms: int = 0
    model: str = "claude-sonnet-4-20250514"
```

### Enhanced UsageRecorder

```python
class UsageRecorder:
    """Record prompt usage to audit trail with token tracking."""
    
    def __init__(self, repo: PipelinePromptUsageRepository):
        self._repo = repo
    
    def record_usage(self, usage: UsageRecord) -> bool:
        """
        Record prompt usage with token counts and cost.
        
        Args:
            usage: Usage record with token data
            
        Returns:
            True if recorded successfully, False otherwise
        """
        try:
            # Calculate cost
            cost_usd = calculate_cost(
                usage.input_tokens, 
                usage.output_tokens,
                usage.model
            )
            
            # Store in database
            usage_id = self._repo.create(
                pipeline_id=usage.pipeline_id,
                prompt_id=usage.prompt_id,
                role_name=usage.role_name,
                phase_name=usage.phase_name,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cost_usd=cost_usd,
                model=usage.model,
                execution_time_ms=usage.execution_time_ms
            )
            
            logger.debug(
                f"Recorded usage: {usage_id}, "
                f"tokens={usage.input_tokens + usage.output_tokens}, "
                f"cost=${cost_usd:.6f}"
            )
            
            return True
            
        except Exception as e:
            logger.warning(
                "Usage record failure",
                extra={
                    "event": "usage_record_failure",
                    "pipeline_id": usage.pipeline_id,
                    "phase_name": usage.phase_name,
                    "role_name": usage.role_name,
                    "prompt_id": usage.prompt_id,
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "error": str(e)
                }
            )
            return False
```

---

## Updated PhaseExecutionOrchestrator

### Pass Token Data to UsageRecorder

```python
# In execute_phase(), after LLM call:

# Step 5: Record usage (best-effort, non-blocking)
usage = UsageRecord(
    pipeline_id=pipeline_id,
    prompt_id=prompt_id,
    role_name=config.role_name,
    phase_name=phase_name,
    input_tokens=llm_result.token_usage.get("input_tokens", 0),
    output_tokens=llm_result.token_usage.get("output_tokens", 0),
    execution_time_ms=llm_result.execution_time_ms,
    model="claude-sonnet-4-20250514"  # or from config
)
recorded = self._usage_recorder.record_usage(usage)
```

---

## TokenMetricsService

### New Service for Aggregation

```python
"""
Token metrics service for aggregation and reporting.

Provides various views of token usage for optimization.
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class TokenMetrics:
    """Aggregated token metrics."""
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost_usd: float
    call_count: int
    avg_tokens_per_call: float
    avg_cost_per_call: float


@dataclass
class PhaseMetrics:
    """Token metrics for a specific phase."""
    phase_name: str
    metrics: TokenMetrics


@dataclass
class PipelineMetrics:
    """Complete metrics for a pipeline."""
    pipeline_id: str
    total_metrics: TokenMetrics
    phase_metrics: List[PhaseMetrics]
    created_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]


class TokenMetricsService:
    """Service for token usage analytics."""
    
    def __init__(self, repo: PipelinePromptUsageRepository):
        self._repo = repo
    
    def get_pipeline_metrics(self, pipeline_id: str) -> PipelineMetrics:
        """Get complete token metrics for a pipeline."""
        usage_records = self._repo.get_by_pipeline(pipeline_id)
        
        # Aggregate by phase
        phase_data = {}
        for record in usage_records:
            if record.phase_name not in phase_data:
                phase_data[record.phase_name] = []
            phase_data[record.phase_name].append(record)
        
        # Calculate phase metrics
        phase_metrics = []
        for phase_name, records in phase_data.items():
            metrics = self._calculate_metrics(records)
            phase_metrics.append(PhaseMetrics(phase_name, metrics))
        
        # Calculate total metrics
        total_metrics = self._calculate_metrics(usage_records)
        
        # Get timing
        created_at = min(r.used_at for r in usage_records)
        completed_at = max(r.used_at for r in usage_records) if usage_records else None
        duration = (completed_at - created_at).total_seconds() if completed_at else None
        
        return PipelineMetrics(
            pipeline_id=pipeline_id,
            total_metrics=total_metrics,
            phase_metrics=phase_metrics,
            created_at=created_at,
            completed_at=completed_at,
            duration_seconds=duration
        )
    
    def get_role_metrics(self, role_name: str, days: int = 30) -> TokenMetrics:
        """Get token metrics for a role over time period."""
        since = datetime.utcnow() - timedelta(days=days)
        records = self._repo.get_by_role_since(role_name, since)
        return self._calculate_metrics(records)
    
    def get_daily_metrics(self, days: int = 7) -> List[dict]:
        """Get daily token usage for trending."""
        since = datetime.utcnow() - timedelta(days=days)
        records = self._repo.get_since(since)
        
        # Group by date
        daily = {}
        for record in records:
            date_key = record.used_at.date()
            if date_key not in daily:
                daily[date_key] = []
            daily[date_key].append(record)
        
        # Calculate metrics per day
        result = []
        for date, records in sorted(daily.items()):
            metrics = self._calculate_metrics(records)
            result.append({
                "date": date.isoformat(),
                "metrics": metrics
            })
        
        return result
    
    def get_budget_status(
        self, 
        pipeline_id: str, 
        budget_usd: float
    ) -> dict:
        """Check if pipeline is within budget."""
        metrics = self.get_pipeline_metrics(pipeline_id)
        
        remaining = budget_usd - metrics.total_metrics.total_cost_usd
        percent_used = (metrics.total_metrics.total_cost_usd / budget_usd) * 100
        
        return {
            "budget_usd": budget_usd,
            "spent_usd": metrics.total_metrics.total_cost_usd,
            "remaining_usd": remaining,
            "percent_used": percent_used,
            "over_budget": remaining < 0
        }
    
    def _calculate_metrics(self, records: List) -> TokenMetrics:
        """Calculate aggregated metrics from usage records."""
        if not records:
            return TokenMetrics(0, 0, 0, 0.0, 0, 0.0, 0.0)
        
        total_input = sum(r.input_tokens for r in records)
        total_output = sum(r.output_tokens for r in records)
        total_tokens = total_input + total_output
        total_cost = sum(r.cost_usd for r in records)
        call_count = len(records)
        
        return TokenMetrics(
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_tokens=total_tokens,
            total_cost_usd=round(total_cost, 6),
            call_count=call_count,
            avg_tokens_per_call=round(total_tokens / call_count, 2),
            avg_cost_per_call=round(total_cost / call_count, 6)
        )
```

---

## API Endpoints

### GET /metrics/tokens

```python
"""Token metrics API endpoints."""

from fastapi import APIRouter, Depends, Query
from typing import Optional

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/tokens/pipeline/{pipeline_id}")
def get_pipeline_token_metrics(pipeline_id: str):
    """Get complete token metrics for a pipeline."""
    service = TokenMetricsService(PipelinePromptUsageRepository())
    metrics = service.get_pipeline_metrics(pipeline_id)
    
    return {
        "pipeline_id": metrics.pipeline_id,
        "total": {
            "input_tokens": metrics.total_metrics.total_input_tokens,
            "output_tokens": metrics.total_metrics.total_output_tokens,
            "total_tokens": metrics.total_metrics.total_tokens,
            "cost_usd": metrics.total_metrics.total_cost_usd,
            "call_count": metrics.total_metrics.call_count,
            "avg_tokens_per_call": metrics.total_metrics.avg_tokens_per_call,
            "avg_cost_per_call": metrics.total_metrics.avg_cost_per_call
        },
        "phases": [
            {
                "phase": pm.phase_name,
                "input_tokens": pm.metrics.total_input_tokens,
                "output_tokens": pm.metrics.total_output_tokens,
                "total_tokens": pm.metrics.total_tokens,
                "cost_usd": pm.metrics.total_cost_usd,
                "call_count": pm.metrics.call_count
            }
            for pm in metrics.phase_metrics
        ],
        "timing": {
            "created_at": metrics.created_at.isoformat(),
            "completed_at": metrics.completed_at.isoformat() if metrics.completed_at else None,
            "duration_seconds": metrics.duration_seconds
        }
    }


@router.get("/tokens/role/{role_name}")
def get_role_token_metrics(
    role_name: str,
    days: int = Query(default=30, ge=1, le=90)
):
    """Get token metrics for a role over time."""
    service = TokenMetricsService(PipelinePromptUsageRepository())
    metrics = service.get_role_metrics(role_name, days)
    
    return {
        "role_name": role_name,
        "period_days": days,
        "metrics": {
            "input_tokens": metrics.total_input_tokens,
            "output_tokens": metrics.total_output_tokens,
            "total_tokens": metrics.total_tokens,
            "cost_usd": metrics.total_cost_usd,
            "call_count": metrics.call_count,
            "avg_tokens_per_call": metrics.avg_tokens_per_call,
            "avg_cost_per_call": metrics.avg_cost_per_call
        }
    }


@router.get("/tokens/daily")
def get_daily_token_metrics(
    days: int = Query(default=7, ge=1, le=30)
):
    """Get daily token usage for trending."""
    service = TokenMetricsService(PipelinePromptUsageRepository())
    daily_metrics = service.get_daily_metrics(days)
    
    return {
        "period_days": days,
        "daily": daily_metrics
    }


@router.get("/tokens/budget/{pipeline_id}")
def check_budget_status(
    pipeline_id: str,
    budget_usd: float = Query(ge=0.01)
):
    """Check if pipeline is within budget."""
    service = TokenMetricsService(PipelinePromptUsageRepository())
    status = service.get_budget_status(pipeline_id, budget_usd)
    
    return status
```

---

## CLI Commands

### manage.py token-report

```python
"""
CLI command for token usage reports.

Usage:
    python manage.py token-report --pipeline pip_123
    python manage.py token-report --role pm
    python manage.py token-report --daily 7
    python manage.py token-report --export pipeline_report.csv
"""

import click
import csv
from tabulate import tabulate


@click.group()
def cli():
    """Token usage reporting commands."""
    pass


@cli.command()
@click.option('--pipeline', help='Pipeline ID')
@click.option('--role', help='Role name')
@click.option('--days', default=30, help='Number of days')
@click.option('--export', help='Export to CSV file')
def token_report(pipeline, role, days, export):
    """Generate token usage report."""
    service = TokenMetricsService(PipelinePromptUsageRepository())
    
    if pipeline:
        # Pipeline report
        metrics = service.get_pipeline_metrics(pipeline)
        
        print(f"\n📊 Pipeline Token Report: {pipeline}\n")
        print(f"Total Cost: ${metrics.total_metrics.total_cost_usd:.6f}")
        print(f"Total Tokens: {metrics.total_metrics.total_tokens:,}")
        print(f"  Input: {metrics.total_metrics.total_input_tokens:,}")
        print(f"  Output: {metrics.total_metrics.total_output_tokens:,}")
        print(f"LLM Calls: {metrics.total_metrics.call_count}")
        print(f"Avg Tokens/Call: {metrics.total_metrics.avg_tokens_per_call:.1f}")
        print(f"Avg Cost/Call: ${metrics.total_metrics.avg_cost_per_call:.6f}\n")
        
        # Phase breakdown
        phase_data = []
        for pm in metrics.phase_metrics:
            phase_data.append([
                pm.phase_name,
                pm.metrics.call_count,
                f"{pm.metrics.total_tokens:,}",
                f"${pm.metrics.total_cost_usd:.6f}"
            ])
        
        print("Phase Breakdown:")
        print(tabulate(
            phase_data,
            headers=["Phase", "Calls", "Tokens", "Cost"],
            tablefmt="grid"
        ))
        
        # Export if requested
        if export:
            with open(export, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Phase", "Calls", "Tokens", "Cost USD"])
                writer.writerows(phase_data)
            print(f"\n✅ Exported to {export}")
    
    elif role:
        # Role report
        metrics = service.get_role_metrics(role, days)
        
        print(f"\n📊 Role Token Report: {role} (last {days} days)\n")
        print(f"Total Cost: ${metrics.total_cost_usd:.6f}")
        print(f"Total Tokens: {metrics.total_tokens:,}")
        print(f"LLM Calls: {metrics.call_count}")
        print(f"Avg Tokens/Call: {metrics.avg_tokens_per_call:.1f}")
        print(f"Avg Cost/Call: ${metrics.avg_cost_per_call:.6f}")
    
    else:
        print("❌ Must specify --pipeline or --role")


if __name__ == '__main__':
    cli()
```

---

## Usage Examples

### During Development

```python
# After each LLM call, see token usage:
result = orchestrator.execute_phase(...)

print(f"Tokens used: {result.token_usage}")
print(f"Cost: ${calculate_cost(input_tokens, output_tokens):.6f}")
```

### Via API

```bash
# Get pipeline metrics
curl http://localhost:8000/metrics/tokens/pipeline/pip_123

# Response:
{
  "pipeline_id": "pip_123",
  "total": {
    "input_tokens": 12500,
    "output_tokens": 3200,
    "total_tokens": 15700,
    "cost_usd": 0.085500,
    "call_count": 3,
    "avg_tokens_per_call": 5233.33,
    "avg_cost_per_call": 0.028500
  },
  "phases": [
    {
      "phase": "pm_phase",
      "input_tokens": 8000,
      "output_tokens": 2000,
      "total_tokens": 10000,
      "cost_usd": 0.054000,
      "call_count": 1
    },
    {
      "phase": "arch_phase",
      "input_tokens": 4500,
      "output_tokens": 1200,
      "total_tokens": 5700,
      "cost_usd": 0.031500,
      "call_count": 2
    }
  ]
}
```

### Via CLI

```bash
# Pipeline report
python manage.py token-report --pipeline pip_123

# Output:
📊 Pipeline Token Report: pip_123

Total Cost: $0.085500
Total Tokens: 15,700
  Input: 12,500
  Output: 3,200
LLM Calls: 3
Avg Tokens/Call: 5233.3
Avg Cost/Call: $0.028500

Phase Breakdown:
+------------+-------+---------+-----------+
| Phase      | Calls | Tokens  | Cost      |
+============+=======+=========+===========+
| pm_phase   | 1     | 10,000  | $0.054000 |
| arch_phase | 2     | 5,700   | $0.031500 |
+------------+-------+---------+-----------+

# Role report
python manage.py token-report --role pm --days 7

# Daily trend
python manage.py token-report --daily 7
```

---

## Optimization Use Cases

### 1. Identify Expensive Phases

```bash
python manage.py token-report --pipeline pip_123

# See which phase costs most
# Optimize that phase's prompt
```

### 2. Compare Before/After JSON Migration

```python
# Before JSON:
metrics_before = service.get_role_metrics("pm", days=7)
print(f"Cost before: ${metrics_before.total_cost_usd}")

# After JSON migration:
metrics_after = service.get_role_metrics("pm", days=7)
print(f"Cost after: ${metrics_after.total_cost_usd}")

reduction = ((metrics_before.total_cost_usd - metrics_after.total_cost_usd) 
             / metrics_before.total_cost_usd * 100)
print(f"Cost reduction: {reduction:.1f}%")
```

### 3. Budget Alerts

```python
# Check budget before advancing
budget_status = service.get_budget_status(pipeline_id, budget_usd=1.00)

if budget_status["over_budget"]:
    logger.warning(f"Pipeline {pipeline_id} over budget!")
    # Alert, pause, or fail
```

### 4. Trend Analysis

```bash
# Daily usage trend
curl http://localhost:8000/metrics/tokens/daily?days=30

# Identify spikes, anomalies
# Optimize prompts causing spikes
```

---

## Testing

```python
class TestTokenTracking:
    """Test token tracking and cost calculation."""
    
    def test_cost_calculation(self):
        """Should calculate cost correctly."""
        cost = calculate_cost(
            input_tokens=10_000,
            output_tokens=2_000
        )
        # (10k / 1M * $3) + (2k / 1M * $15)
        # = $0.03 + $0.03 = $0.06
        assert cost == 0.06
    
    def test_usage_recorder_stores_tokens(self):
        """Should store token counts in database."""
        recorder = UsageRecorder(repo)
        
        usage = UsageRecord(
            pipeline_id="pip_test",
            prompt_id="rp_123",
            role_name="pm",
            phase_name="pm_phase",
            input_tokens=1000,
            output_tokens=500
        )
        
        result = recorder.record_usage(usage)
        assert result is True
        
        # Verify in database
        record = repo.get_by_pipeline("pip_test")[0]
        assert record.input_tokens == 1000
        assert record.output_tokens == 500
        assert record.cost_usd == 0.01050  # Calculated
    
    def test_pipeline_metrics_aggregation(self):
        """Should aggregate metrics correctly."""
        service = TokenMetricsService(repo)
        
        metrics = service.get_pipeline_metrics("pip_test")
        
        assert metrics.total_metrics.total_tokens == 15700
        assert metrics.total_metrics.total_cost_usd == 0.0855
        assert len(metrics.phase_metrics) == 2
```

---

## Deliverables

1. ✅ Migration script: `002_add_token_tracking.py`
2. ✅ Updated `UsageRecorder` with token storage
3. ✅ New `TokenMetricsService` for aggregation
4. ✅ API endpoints: `/metrics/tokens/*`
5. ✅ CLI command: `manage.py token-report`
6. ✅ Cost calculation utilities
7. ✅ Test suite for token tracking
8. ✅ Documentation

---

## Success Criteria

- ✅ Every LLM call tracked with token counts
- ✅ Cost calculated and stored
- ✅ Can query metrics by pipeline, phase, role
- ✅ Can export data to CSV
- ✅ Can see daily trends
- ✅ Can set and monitor budgets
- ✅ <50ms overhead for tracking

**Result:** Full visibility into token usage for optimization and cost control.

---

**Author:** Development Mentor  
**Status:** Ready for Implementation  
**Estimate:** 4 hours
