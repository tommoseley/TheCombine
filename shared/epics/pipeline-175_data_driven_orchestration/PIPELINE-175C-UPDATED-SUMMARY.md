# PIPELINE-175C: Updated With Token Tracking

**Status:** Ready for Implementation  
**Effort:** 22 hours (3 days)  
**Token Budget:** 6,000 tokens

---

## What Changed

Added **Story 5: Token Usage Tracking & Cost Reporting** to PIPELINE-175C.

**Why:** You're absolutely right - we need visibility into token costs for every LLM call to optimize effectively during bootstrap.

---

## Updated Story List

1. **Environment Setup Script** (4h) - One-command setup
2. **API Server Startup** (2h) - Start local server
3. **First Self-Hosted Execution** (4h) - Prove it works
4. **JSON Schema Migration** (8h) - 77% token reduction
5. **Token Usage Tracking** (4h) - **NEW** - Cost visibility

**Total:** 22 hours (3 days)

---

## Story 5: Token Usage Tracking

### What It Delivers

**Database Changes:**
```sql
ALTER TABLE pipeline_prompt_usage ADD COLUMN:
- input_tokens INTEGER
- output_tokens INTEGER  
- total_tokens INTEGER (computed)
- cost_usd DECIMAL(10, 6)
- model VARCHAR(64)
- execution_time_ms INTEGER
```

**New Service: TokenMetricsService**
- Aggregate by pipeline, phase, role
- Calculate costs based on Anthropic pricing
- Budget monitoring and alerts
- Trend analysis

**API Endpoints:**
```
GET /metrics/tokens/pipeline/{id}  - Full pipeline breakdown
GET /metrics/tokens/role/{name}    - Role metrics over time
GET /metrics/tokens/daily          - Daily trends
GET /metrics/tokens/budget/{id}    - Budget status
```

**CLI Command:**
```bash
python manage.py token-report --pipeline pip_123
python manage.py token-report --role pm --days 7
python manage.py token-report --daily 7 --export report.csv
```

### Example Output

```bash
$ python manage.py token-report --pipeline pip_123

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
```

### Use Cases

**1. Measure JSON Migration Impact:**
```bash
# Before JSON
python manage.py token-report --role pm --days 7
# Cost: $2.50 for 10 epics

# After JSON  
python manage.py token-report --role pm --days 7
# Cost: $0.50 for 10 epics
# = 80% reduction ✅
```

**2. Identify Expensive Prompts:**
```bash
# See which phase costs most
python manage.py token-report --pipeline pip_123

# Optimize that phase's prompt
# Re-run, verify cost reduction
```

**3. Budget Monitoring:**
```bash
curl http://localhost:8000/metrics/tokens/budget/pip_123?budget_usd=1.00

# Response:
{
  "budget_usd": 1.00,
  "spent_usd": 0.73,
  "remaining_usd": 0.27,
  "percent_used": 73.0,
  "over_budget": false
}
```

---

## Pricing Model

**Anthropic (Dec 2025):**
- Input: $3 per million tokens
- Output: $15 per million tokens

**Example:**
- Input: 10,000 tokens = $0.03
- Output: 2,000 tokens = $0.03
- **Total: $0.06 per call**

**Stored with 6 decimal precision** for accurate tracking.

---

## Integration with 175B

Token tracking integrates seamlessly with existing components:

```python
# PhaseExecutionOrchestrator already gets token data from LLMCaller
llm_result = self._llm_caller.call(...)

# Now passes it to UsageRecorder
usage = UsageRecord(
    pipeline_id=pipeline_id,
    prompt_id=prompt_id,
    role_name=config.role_name,
    phase_name=phase_name,
    input_tokens=llm_result.token_usage["input_tokens"],
    output_tokens=llm_result.token_usage["output_tokens"],
    execution_time_ms=llm_result.execution_time_ms,
    model="claude-sonnet-4-20250514"
)
self._usage_recorder.record_usage(usage)
```

**No changes needed to LLMCaller or Orchestrator** - just enhanced UsageRecorder and new reporting layer.

---

## Files to Create

1. `app/orchestrator_api/persistence/migrations/002_add_token_tracking.py`
2. `app/orchestrator_api/services/token_metrics_service.py`
3. `app/orchestrator_api/routers/metrics.py`
4. `scripts/manage.py` (CLI commands)
5. Updated `usage_recorder.py`
6. Tests for token tracking

**Total: ~400 lines of code**

---

## Success Metrics

**After Story 5:**
- ✅ Every LLM call shows exact token count and cost
- ✅ Can see cost breakdown by phase in real-time
- ✅ Can compare before/after optimization efforts
- ✅ Can set budgets and get alerts
- ✅ Can export data for analysis

**During Bootstrap:**
- See exactly how much each JSON prompt saves
- Identify which role/phase needs most optimization
- Track daily costs as we iterate
- Prove 77% reduction claim with data

---

## Updated Documents

📄 **[PIPELINE-175C-PM-Phase.md](computer:///mnt/user-data/outputs/PIPELINE-175C-PM-Phase.md)** - Updated with Story 5

📄 **[PIPELINE-175C-Story5-Token-Tracking.md](computer:///mnt/user-data/outputs/PIPELINE-175C-Story5-Token-Tracking.md)** - Detailed specification

---

## Next Steps

1. Review updated 175C scope (now 5 stories)
2. Approve for implementation
3. Begin bootstrap with token tracking from day 1
4. Use metrics to optimize as we go

**With token tracking, we'll have hard data to validate every optimization decision.**

---

**Updated By:** Development Mentor  
**Date:** 2025-12-05  
**Total Effort:** 22 hours (was 18)  
**Priority:** CRITICAL
