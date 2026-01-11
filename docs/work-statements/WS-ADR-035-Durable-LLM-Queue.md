# WS-ADR-035: Durable LLM Threaded Queue & Execution Ledger

## Overview

Implement the durable execution infrastructure defined in ADR-035 to ensure no paid LLM work is lost due to user navigation, browser refresh, or system failure.

## References

- ADR-035: Durable LLM Threaded Queue & Execution Ledger
- Existing: `llm_call_records` (telemetry - separate concern)
- Existing: `StoryBacklogService.generate_epic_stories()`

## Problem

Currently, if a user clicks "Generate Stories" and navigates away:
- The LLM call may complete but UI feedback is lost
- User may click again, causing duplicate work/cost
- No way to recover or observe in-flight operations
- No audit trail of what was requested vs. what completed

## Scope

### In Scope

1. **Database Schema** - Three new tables per ADR-035:
   - `llm_threads` - Intent containers
   - `llm_work_items` - Execution units
   - `llm_ledger_entries` - Immutable interaction records

2. **Domain Models** - Python dataclasses/models:
   - `LLMThread`
   - `LLMWorkItem`
   - `LLMLedgerEntry`

3. **Repository Layer**:
   - `ThreadRepository` - CRUD + find by idempotency key
   - `WorkItemRepository` - CRUD + claim next + update status
   - `LedgerRepository` - Append-only writes

4. **Execution Service** - Refactor `StoryBacklogService` to:
   - Create thread on command entry
   - Enqueue work item
   - Record ledger entries (prompt, response, mutation)
   - Update thread/work item status

5. **API Updates**:
   - `POST /commands/story-backlog/generate-epic` returns `{thread_id, status}`
   - `POST /commands/story-backlog/generate-all` returns `{thread_id, status}`
   - `GET /threads/{thread_id}` - Thread status observation
   - `GET /projects/{project_id}/threads?active=true` - Active threads list

6. **Idempotency**:
   - Compute idempotency key from semantic identity
   - Return existing thread if `open|running`
   - Skip if `complete` (unless `force=true`)

7. **UI Updates**:
   - Poll for thread status on page load
   - Show in-progress indicators for active threads
   - Derive button state from thread status, not just document content

### Out of Scope (Deferred)

- Background worker process (in-process async for MVP)
- Retry with backoff (manual retry only for MVP)
- Dead letter queue processing
- Ledger entry blob storage (inline payload only)
- Real-time push/SSE (polling only)
- Admin UI for thread management

## Deliverables

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | Alembic migration | Create 3 tables |
| 2 | SQLAlchemy models | `LLMThread`, `LLMWorkItem`, `LLMLedgerEntry` |
| 3 | Repository classes | Thread, WorkItem, Ledger repositories |
| 4 | `ThreadExecutionService` | Orchestrates thread lifecycle |
| 5 | Refactored `StoryBacklogService` | Uses thread execution |
| 6 | Updated command endpoints | Return thread_id, implement idempotency |
| 7 | Thread observation endpoints | GET thread status |
| 8 | UI thread status integration | Poll and display active threads |
| 9 | Unit tests | Repository and service tests |

## Database Schema (Draft)

```sql
-- Intent container
CREATE TABLE llm_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind VARCHAR(100) NOT NULL,           -- story_generate_epic, story_generate_all
    space_type VARCHAR(50) NOT NULL,      -- project
    space_id UUID NOT NULL,
    target_ref JSONB NOT NULL,            -- {doc_type, doc_id, epic_id?}
    status VARCHAR(20) NOT NULL DEFAULT 'open',  -- open|running|complete|failed|canceled
    parent_thread_id UUID REFERENCES llm_threads(id),
    idempotency_key VARCHAR(255),
    created_by VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at TIMESTAMPTZ
);

-- Execution unit
CREATE TABLE llm_work_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES llm_threads(id),
    sequence INT NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'queued',  -- queued|claimed|running|applied|failed|dead_letter
    attempt INT NOT NULL DEFAULT 1,
    lock_scope VARCHAR(255),              -- project:{id} or epic:{id}
    not_before TIMESTAMPTZ,
    error_code VARCHAR(50),               -- LOCKED|PROVIDER_RATE_LIMIT|PROVIDER_TIMEOUT|SCHEMA_INVALID|MUTATION_CONFLICT|UNKNOWN
    error_message TEXT,                   -- Human-readable summary (informational only)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    
    CONSTRAINT uq_thread_sequence UNIQUE (thread_id, sequence)
);

-- Immutable ledger
CREATE TABLE llm_ledger_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES llm_threads(id),
    work_item_id UUID REFERENCES llm_work_items(id),
    entry_type VARCHAR(50) NOT NULL,      -- prompt|response|parse_report|mutation_report|error
    payload JSONB NOT NULL,
    payload_hash VARCHAR(64),             -- SHA256 for dedup/verification
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_threads_space ON llm_threads(space_type, space_id, status);
CREATE INDEX idx_work_items_thread ON llm_work_items(thread_id);
CREATE INDEX idx_work_items_status ON llm_work_items(status) WHERE status = 'queued';
CREATE INDEX idx_ledger_thread ON llm_ledger_entries(thread_id);

-- Partial unique index for idempotency (only active threads)
CREATE UNIQUE INDEX uq_threads_idempotency_active 
    ON llm_threads(idempotency_key) 
    WHERE status IN ('open', 'running');
```

## Error Code Enum

| Code | Meaning | UI Action |
|------|---------|-----------|
| `LOCKED` | Resource lock conflict | Retry later |
| `PROVIDER_RATE_LIMIT` | LLM provider 429 | Retry later |
| `PROVIDER_TIMEOUT` | LLM provider timeout | Retry |
| `SCHEMA_INVALID` | Output failed validation | No retry (needs investigation) |
| `MUTATION_CONFLICT` | Document mutation failed | Retry |
| `UNKNOWN` | Unexpected error | No retry (needs investigation) |

**Note:** `error_code` and `error_message` are informational; authoritative failure context resides in immutable ledger entries (`entry_type='error'`).

## Idempotency Key Format

```
{operation}:{space_type}:{space_id}:{target_doc_type}:{target_id}

Examples:
- story_generate_epic:project:96f07606-...:story_backlog:demo-core-system
- story_generate_all:project:96f07606-...:story_backlog:all
```

## Execution Flow (Single Epic)

```
1. POST /commands/story-backlog/generate-epic {project_id, epic_id}
2. Compute idempotency_key
3. Check for existing thread (open|running) → return if found
4. Create LLMThread (status=open)
5. Create LLMWorkItem (status=queued)
6. Return {thread_id, status: "open"}
7. (async) Claim work item (status=running)
8. Record prompt ledger entry
9. Execute LLM call
10. Record response ledger entry
11. Validate output
12. Apply mutation to StoryBacklog
13. Record mutation_report ledger entry
14. Mark work item (status=applied)
15. Mark thread (status=complete, closed_at=now)
```

## UI Behavior Changes

| Current | New |
|---------|-----|
| Button click → wait for response | Button click → get thread_id → poll status |
| Navigate away = lose feedback | Navigate away = thread continues, UI recovers on return |
| Button enabled if no stories | Button enabled if no stories AND no active thread |
| No visibility of in-flight work | Show "Generation in progress..." from thread status |

## Testing Strategy

- **Unit tests**: Repository methods, idempotency logic, status transitions
- **Integration tests**: Full flow from command to document mutation
- **Manual tests**: Navigate away during generation, return, verify completion

## Estimated Effort

| Component | Estimate |
|-----------|----------|
| Migration + Models | 1 hour |
| Repositories | 1 hour |
| ThreadExecutionService | 2 hours |
| Refactor StoryBacklogService | 2 hours |
| API endpoints | 1 hour |
| UI integration | 2 hours |
| Tests | 2 hours |
| **Total** | **~11 hours** |

## Open Questions

1. **Retention policy** - How long to keep completed threads/ledger entries?
2. **Correlation with telemetry** - Add `thread_id` to `llm_call_records`?
3. **Worker model** - In-process async now, separate worker later?

## Acceptance Criteria

- [ ] User clicks Generate, navigates away, returns → sees completed stories
- [ ] User double-clicks Generate → only one thread created
- [ ] Thread status visible via API
- [ ] All LLM interactions recorded in ledger
- [ ] No duplicate paid work for same semantic request
