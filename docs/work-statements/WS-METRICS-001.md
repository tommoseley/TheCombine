# WS-METRICS-001: Developer Execution Metrics Collection and Storage

## Status: Complete

## Governing References

- ADR-010 -- LLM Execution Logging
- ADR-050 -- Work Statement Verification Constitution

## Verification Mode: A

## Allowed Paths

- app/api/
- app/domain/
- app/core/
- alembic/
- tests/

---

## Objective

Build database-backed metrics collection for Work Statement execution. Claude Code and other AI executors POST structured metrics at phase boundaries during WS execution. Metrics are stored in PostgreSQL tables, queryable via API, and aggregatable for dashboards and customer-facing evidence.

---

## Preconditions

- Database accessible (RDS DEV/TEST)
- ADR-010 LLM execution logging operational (cost metrics derive from existing data)

---

## Scope

### In Scope

- Database schema for execution metrics (migrations via Alembic)
- API endpoints for metrics ingestion (POST)
- API endpoints for metrics retrieval (GET)
- Per-WS execution records (start, phases, completion, duration, test counts, file counts)
- Per-bug-fix records (linked to WS execution)
- LLM cost aggregation from existing ADR-010 execution logs
- Dashboard endpoint returning aggregated metrics

### Out of Scope

- SPA dashboard UI (future WS -- API first)
- Real-time streaming / WebSocket metrics
- Historical backfill of pre-metrics WS executions
- Alerting or threshold monitoring

---

## Data Model

### ws_executions Table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| ws_id | VARCHAR | Work Statement identifier (e.g., WS-DCW-001) |
| wp_id | VARCHAR | Parent Work Package identifier |
| scope_id | VARCHAR | Reserved for future tenant/scope isolation (nullable, not enforced in v1) |
| executor | VARCHAR | Who executed (claude_code, human, subagent) |
| status | VARCHAR | Pinned enum: STARTED, COMPLETED, FAILED, HARD_STOP, BLOCKED |
| started_at | TIMESTAMP | WS execution start |
| completed_at | TIMESTAMP | WS execution end (null if in progress) |
| duration_seconds | INTEGER | Wall clock duration |
| phase_metrics | JSONB | Per-phase breakdown (see below) |
| test_metrics | JSONB | Tests written, passing, failing |
| file_metrics | JSONB | Files created, modified, deleted |
| rework_cycles | INTEGER | Times verification bounced to implementation |
| llm_calls | INTEGER | Total LLM invocations during execution |
| llm_tokens_in | INTEGER | Total input tokens |
| llm_tokens_out | INTEGER | Total output tokens |
| llm_cost_usd | DECIMAL | Estimated cost from token counts |
| created_at | TIMESTAMP | Record creation |

### phase_metrics JSONB Structure

**Pinned phase names:** `failing_tests`, `implement`, `verify`, `do_no_harm_audit`

Each phase event includes an `event_id` for idempotent updates. Server enforces `(ws_execution_id, event_id)` uniqueness -- duplicate POSTs are safely ignored.

```json
{
  "phases": [
    {
      "event_id": "550e8400-e29b-41d4-a716-446655440001",
      "sequence": 1,
      "name": "failing_tests",
      "started_at": "2026-02-23T10:00:00Z",
      "completed_at": "2026-02-23T10:04:30Z",
      "duration_seconds": 270,
      "result": "pass",
      "tests_written": 6
    },
    {
      "event_id": "550e8400-e29b-41d4-a716-446655440002",
      "sequence": 2,
      "name": "implement",
      "started_at": "2026-02-23T10:04:30Z",
      "completed_at": "2026-02-23T10:18:00Z",
      "duration_seconds": 810,
      "result": "pass",
      "files_modified": 4
    },
    {
      "event_id": "550e8400-e29b-41d4-a716-446655440003",
      "sequence": 3,
      "name": "verify",
      "started_at": "2026-02-23T10:18:00Z",
      "completed_at": "2026-02-23T10:22:00Z",
      "duration_seconds": 240,
      "result": "pass",
      "tests_passing": 6,
      "tests_failing": 0
    }
  ]
}
```

### test_metrics JSONB Structure

```json
{
  "written": 6,
  "passing": 6,
  "failing": 0,
  "skipped": 0
}
```

### file_metrics JSONB Structure

```json
{
  "created": ["app/domain/services/new_service.py"],
  "modified": ["app/api/v1/routers/production.py"],
  "deleted": []
}
```

### ws_bug_fixes Table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| ws_execution_id | UUID | FK to ws_executions |
| scope_id | VARCHAR | Reserved for future tenant/scope isolation (nullable, not enforced in v1) |
| description | TEXT | One-line bug description |
| root_cause | TEXT | One-line root cause |
| test_name | VARCHAR | Reproducing test name |
| fix_summary | TEXT | What was changed |
| files_modified | JSONB | List of files touched |
| autonomous | BOOLEAN | True if fixed without human escalation |
| created_at | TIMESTAMP | Record creation |

---

## API Endpoints

### Ingestion (POST)

```
POST /api/v1/metrics/ws-execution
```

Body: WS execution start or update. Accepts partial updates (start event, phase completion, final completion).

```
POST /api/v1/metrics/bug-fix
```

Body: Bug fix record linked to a WS execution.

### Retrieval (GET)

```
GET /api/v1/metrics/ws-executions
```

List all WS executions. Filterable by wp_id, status, date range.

```
GET /api/v1/metrics/ws-executions/{id}
```

Single WS execution with phase breakdown and linked bug fixes.

```
GET /api/v1/metrics/dashboard
```

Aggregated metrics:
- Total WSs completed (period)
- Average duration per WS
- Total tests written (period)
- Total bugs fixed autonomously
- Total LLM cost (period)
- Rework cycle average
- Cost per WS trend

```
GET /api/v1/metrics/cost-summary
```

LLM cost aggregation from ADR-010 execution logs + WS execution cost fields. Breakdown by document type, WS, date.

```
GET /api/v1/metrics/scoreboard?window=7d
```

One-screen summary for demos and operator review. Returns:
- Total runs (in window)
- Success rate (COMPLETED / total)
- Average + p95 duration
- First-pass verify rate (rework_cycles == 0 as percentage)
- Total LLM cost + cost per completed WS
- Autonomous bug-fix count

Window parameter accepts: 24h, 7d, 30d, 90d, all. Default: 7d.

### Correlation ID (Mandatory)

All LLM calls made during WS execution MUST include the `ws_execution_id` as a correlation ID. This is not optional -- without it, cost attribution requires timestamp-based joins that are fragile and lossy.

Claude Code MUST pass `ws_execution_id` to every LLM invocation during WS execution so that ADR-010 execution logs can be joined to WS metrics for precise cost-per-WS and cost-per-phase reporting.

---

## Tier 1 Verification Criteria

All new Tier-1 tests written for this WS must fail prior to implementation and pass after.

1. **WS execution record created**: POST to ws-execution endpoint creates a database record
2. **Phase metrics stored**: Phase completion updates append to phase_metrics JSONB
3. **Bug fix linked**: POST to bug-fix endpoint creates record linked to ws_execution_id
4. **Duration calculated**: completed_at - started_at produces correct duration_seconds
5. **LLM cost aggregated**: Dashboard endpoint returns cost totals consistent with stored execution data
6. **Filtering works**: GET ws-executions with wp_id filter returns only matching records
7. **Dashboard aggregates**: GET dashboard returns correct sums/averages across multiple executions
8. **Partial updates**: Posting a phase completion to an existing execution appends, does not overwrite
9. **Migration clean**: Alembic migration applies and rolls back cleanly
10. **Idempotent phase updates**: Duplicate POST with same event_id is safely ignored, not double-appended
11. **Status enum enforced**: POST with invalid status value is rejected (only STARTED, COMPLETED, FAILED, HARD_STOP, BLOCKED accepted)
12. **Phase name enum enforced**: Phase with invalid name is rejected (only failing_tests, implement, verify, do_no_harm_audit accepted)
13. **Scoreboard returns correct data**: GET scoreboard returns runs, success rate, avg/p95 duration, first-pass rate, cost, bug-fix count
14. **Scoreboard window filtering**: Scoreboard with window=7d returns only data from last 7 days
15. **Correlation ID present**: LLM execution logs linked to WS execution via ws_execution_id correlation

---

## Procedure

### Phase 1: Write Failing Tests (Intent-First)

Write tests asserting criteria 1-9. Verify all fail.

### Phase 2: Implement

1. Create Alembic migration for ws_executions and ws_bug_fixes tables
2. Create domain models (SQLAlchemy ORM)
3. Create repository for metrics CRUD
4. Create service layer for aggregation and dashboard calculations
5. Create API router with POST and GET endpoints
6. Wire LLM cost aggregation from existing ADR-010 llm_execution_logs
7. Add correlation: ws_execution_id can be passed to LLM calls during WS execution for cost attribution

### Phase 3: Verify

1. All Tier 1 tests pass
2. Tier 0 returns zero

---

## Prohibited Actions

- Do not modify ADR-010 logging tables or infrastructure
- Do not build SPA dashboard UI (API only for this WS)
- Do not implement real-time streaming
- Do not backfill historical executions
- Do not hardcode cost-per-token rates (load from configuration)

---

## Verification Checklist

- [x] All new Tier-1 tests fail before implementation
- [x] Alembic migration created and applies cleanly
- [x] ws_executions table created with all columns (including scope_id)
- [x] ws_bug_fixes table created with FK to ws_executions (including scope_id)
- [x] POST ws-execution creates and updates records
- [x] POST bug-fix creates linked records
- [x] GET ws-executions returns filtered results
- [x] GET dashboard returns correct aggregations
- [x] GET cost-summary returns LLM cost breakdown
- [x] GET scoreboard returns correct demo-ready summary
- [x] Scoreboard window filtering works (24h, 7d, 30d, 90d, all)
- [x] Phase metrics append correctly
- [x] Duplicate phase POSTs with same event_id safely ignored
- [x] Invalid status values rejected
- [x] Invalid phase names rejected
- [x] Duration calculation correct
- [x] Correlation ID links LLM logs to WS execution
- [x] All new Tier-1 tests pass after implementation
- [x] Tier 0 returns zero

---

_End of WS-METRICS-001_





