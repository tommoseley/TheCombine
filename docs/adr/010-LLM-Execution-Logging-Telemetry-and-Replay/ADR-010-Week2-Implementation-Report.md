# ADR-010 Week 2 Implementation Report
## LLM Execution Logging - Repository Pattern Integration

**Date:** January 1, 2026  
**Status:** Complete ✓  
**Sprint:** Week 2 of 2

---

## Executive Summary

Week 2 delivered the repository pattern integration for LLM execution logging, enabling full telemetry capture for all document builds. The implementation follows a three-tier testing strategy with no database dependencies in unit tests, proper transaction boundary management, and seamless integration with the existing DocumentBuilder pipeline.

**Key Outcome:** Every LLM call is now traced with inputs, outputs, token usage, and correlation IDs stored in PostgreSQL.

---

## Objectives Achieved

| Objective | Status |
|-----------|--------|
| Repository pattern for LLM logging | ✓ Complete |
| Three-tier test strategy (no DB in Tier-1/2) | ✓ Complete |
| Transaction boundary management | ✓ Complete |
| Content deduplication | ✓ Complete |
| DocumentBuilder integration | ✓ Complete |
| Web route integration | ✓ Complete |
| Correlation ID propagation | ✓ Complete |

---

## Architecture

### Repository Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                    LLMExecutionLogger                        │
│                   (Business Logic Layer)                     │
│  - Content hashing (SHA-256)                                │
│  - Deduplication detection                                  │
│  - Error summary management                                 │
│  - Transaction boundary ownership                           │
└─────────────────────┬───────────────────────────────────────┘
                      │ LLMLogRepository Protocol
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Repository Implementations                      │
├─────────────────────┬─────────────────┬─────────────────────┤
│ InMemoryLLMLog      │ SpyLLMLog       │ PostgresLLMLog      │
│ Repository          │ Repository      │ Repository          │
│ (Tier-1 Tests)      │ (Tier-2 Tests)  │ (Production)        │
└─────────────────────┴─────────────────┴─────────────────────┘
```

### Test Tier Strategy

| Tier | Purpose | Implementation | Speed | DB Required |
|------|---------|----------------|-------|-------------|
| Tier-1 | Business logic + persistence semantics | InMemoryLLMLogRepository | 0.09s | No |
| Tier-2 | Wiring / call contracts | SpyLLMLogRepository | 0.09s | No |
| Tier-3 | PostgreSQL dialect/constraints | PostgresLLMLogRepository | Slow | Yes |

### Transaction Boundaries

**Key Design Rule:** Repository does NOT commit. Service owns transaction boundaries.

```python
# Service commits at safe boundaries
async def start_run(...):
    await self.repo.insert_run(record)
    await self.repo.commit()  # ← Service commits

async def log_error(...):
    await self.repo.insert_error(record)
    await self.repo.bump_error_summary(run_id, code, msg)  # Atomic
    await self.repo.commit()  # ← Single commit for both
```

### Data Flow

```
HTTP Request
    │
    ▼ X-Correlation-ID header (string)
┌─────────────────────┐
│ CorrelationID       │ → Parses to UUID, stores in request.state
│ Middleware          │
└─────────────────────┘
    │
    ▼ UUID
┌─────────────────────┐
│ Web Route           │ → Creates PostgresLLMLogRepository
│ (document_routes)   │ → Creates LLMExecutionLogger
└─────────────────────┘
    │
    ▼ llm_logger injected
┌─────────────────────┐
│ DocumentBuilder     │ → Calls logger at each stage
│ .build_stream()     │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ LLMExecutionLogger  │ → start_run, add_input, add_output, complete_run
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ PostgresLLMLog      │ → Raw SQL inserts (no ORM)
│ Repository          │ → Does NOT commit
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ PostgreSQL          │ → llm_run, llm_content, llm_run_input_ref, etc.
└─────────────────────┘
```

---

## Files Created

### Repository Layer

| File | Purpose | Lines |
|------|---------|-------|
| `app/domain/repositories/llm_log_repository.py` | Protocol + DTOs | ~120 |
| `app/domain/repositories/in_memory_llm_log_repository.py` | Tier-1 tests | ~180 |
| `app/domain/repositories/postgres_llm_log_repository.py` | Production | ~220 |
| `app/domain/repositories/__init__.py` | Exports | ~20 |

### Service Layer

| File | Purpose | Lines |
|------|---------|-------|
| `app/domain/services/llm_execution_logger.py` | Refactored with repo injection | ~200 |

### Dependency Injection

| File | Purpose | Lines |
|------|---------|-------|
| `app/core/dependencies/llm_logging.py` | FastAPI DI providers | ~25 |

### Test Infrastructure

| File | Purpose | Tests |
|------|---------|-------|
| `tests/helpers/spy_llm_log_repository.py` | Tier-2 spy | N/A |
| `tests/tier1/test_llm_execution_logger.py` | Business logic | 7 |
| `tests/tier2/test_llm_logging_wiring.py` | Call contracts | 10 |

---

## Files Modified

| File | Changes |
|------|---------|
| `app/core/dependencies/__init__.py` | Added llm_logging exports |
| `app/api/routers/documents.py` | Injected llm_logger into get_document_builder |
| `app/web/routes/document_routes.py` | Added llm_logger creation in web route |
| `app/domain/services/document_builder.py` | Added ADR-010 diagnostic logging |

---

## Database Schema (Created in Week 1)

```sql
llm_run                 -- Main execution record
├── llm_run_input_ref   -- Input references (many per run)
├── llm_run_output_ref  -- Output references (many per run)  
└── llm_run_error       -- Error records (many per run)

llm_content             -- Deduplicated content storage
```

### Verified Data Capture

For a Story Backlog build:

| Table | Rows | Contents |
|-------|------|----------|
| llm_run | 1 | correlation_id, model, tokens, status |
| llm_run_input_ref | 5 | system_prompt, user_prompt, 2x context_doc, schema |
| llm_run_output_ref | 1 | raw_text |
| llm_content | 6 | Deduplicated content (5 inputs + 1 output) |

---

## Test Results

```
tests/tier1/test_llm_execution_logger.py    7 passed
tests/tier2/test_llm_logging_wiring.py     10 passed
────────────────────────────────────────────────────
Total                                      17 passed in 0.09s
```

### Full Suite (Post-Implementation)

```
111 passed, 0 failed, 8 warnings
```

---

## Key Design Decisions

### 1. Repository Does Not Commit

**Decision:** All repository methods execute SQL but never commit. The service layer owns transaction boundaries.

**Rationale:** Prevents partial writes, enables proper rollback on failure, supports future Unit of Work pattern.

### 2. Atomic Error Summary Updates

**Decision:** Single `bump_error_summary()` method instead of separate increment + update calls.

```sql
UPDATE llm_run SET
    error_count = error_count + 1,
    primary_error_code = :code,
    primary_error_message = :msg
WHERE id = :id
```

**Rationale:** Eliminates race conditions under concurrency.

### 3. UUID Everywhere for Correlation ID

**Decision:** Parse string to UUID once in middleware, use UUID everywhere downstream.

**Rationale:** Type safety, better PostgreSQL indexing, no string/UUID mismatches in domain layer.

### 4. Content Deduplication at Storage Layer

**Decision:** `llm_content` stores unique content by hash; ref tables point to content by hash.

**Rationale:** Same system prompts used across many runs don't multiply storage costs.

### 5. Graceful Degradation

**Decision:** If llm_logger is None or logging fails, document build continues.

**Rationale:** Telemetry failure should never block production document generation.

---

## Deleted Files

| File | Reason |
|------|--------|
| `tests/domain/services/test_llm_execution_logger.py` | Old tests for session-based interface |
| `tests/integration/test_llm_logging_integration.py` | Old integration tests incompatible with repo pattern |
| `app/domain/services/llm_execution_logger_original.py` | Backup of pre-refactor version (can delete) |

---

## Configuration

No new configuration required. The system uses existing:
- `DATABASE_URL` for PostgreSQL connection
- `ANTHROPIC_API_KEY` for LLM calls

---

## Observability

### Log Messages (ADR-010 Tagged)

```
[ADR-010] Web route build_document - correlation_id=...
[ADR-010] Created LLMExecutionLogger for web route
[ADR-010] DocumentBuilder.build_stream() - llm_logger=PRESENT
[ADR-010] PostgresRepo.insert_run() - id=..., correlation_id=...
[ADR-010] PostgresRepo.commit() called
[ADR-010] Started LLM run ...
[ADR-010] Added input ref (run: ..., kind: system_prompt)
[ADR-010] Content deduplicated (hash: abc123...)
[ADR-010] Completed LLM run ...: SUCCESS (1500 tokens)
```

### Useful Queries

```sql
-- Recent LLM runs with input/output counts
SELECT r.id, r.artifact_type, r.status, r.input_tokens, r.output_tokens,
       (SELECT COUNT(*) FROM llm_run_input_ref WHERE llm_run_id = r.id) as inputs,
       (SELECT COUNT(*) FROM llm_run_output_ref WHERE llm_run_id = r.id) as outputs
FROM llm_run r ORDER BY r.started_at DESC LIMIT 10;

-- Content reuse analysis
SELECT content_hash, COUNT(*) as times_used
FROM llm_run_input_ref GROUP BY content_hash HAVING COUNT(*) > 1;

-- Cost by artifact type
SELECT artifact_type, COUNT(*) as runs, SUM(total_tokens) as tokens
FROM llm_run WHERE status = 'SUCCESS' GROUP BY artifact_type;
```

---

## Known Limitations

1. **Tier-3 tests not implemented** - PostgreSQL-specific constraint validation deferred
2. **No cost_usd population** - Cost calculation not yet implemented
3. **Manual web route wiring** - Web routes create logger manually (not via DI)

---

## Future Work

1. **Cost calculation** - Populate `cost_usd` based on model pricing
2. **Prompt replay UI** - View/replay past LLM calls from telemetry
3. **Analytics dashboard** - Token usage, cost trends, error rates
4. **Streaming token estimation** - Approximate tokens during stream
5. **Centralized DI for web routes** - Unify API and web route dependency injection

---

## Conclusion

ADR-010 Week 2 successfully delivered a production-ready LLM execution logging system with:

- **Clean architecture** via repository pattern
- **Fast tests** (17 tests in 0.09s) with no database dependencies
- **Full telemetry** capture for all document builds
- **Content deduplication** for storage efficiency
- **Proper transaction management** at service layer

The system is now capturing all LLM interactions, providing the foundation for cost analysis, debugging, and future prompt optimization.
