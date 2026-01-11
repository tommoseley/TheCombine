# ADR-035 — Durable LLM Threaded Queue & Execution Ledger

| Field | Value |
|-------|-------|
| ADR ID | ADR-035 |
| Title | Durable LLM Threaded Queue & Execution Ledger |
| Status | Accepted |
| Decision Type | Architectural |
| Supersedes | N/A |
| Related ADRs | ADR-030 (BFF), ADR-031 (Schema Registry), ADR-032 (Fragment Registry), ADR-033 (Document Canonicality), ADR-034 (Document Composition) |
| Date | 2026-01-09 |

## 1. Context

The Combine executes user-initiated, paid LLM operations that result in incremental, lock-safe mutations to canonical stored documents (e.g., StoryBacklog, EpicArchitecture).

Users may:
- Navigate away
- Refresh the application
- Trigger the same command multiple times

LLM execution:
- Is asynchronous
- May fail or require retries
- Incurs cost and therefore must not be lost

The system must guarantee:
- Durable capture of user intent
- Zero loss of paid LLM work
- Resumable execution independent of UI session
- Auditability and replayability
- Strict separation between execution correctness and telemetry

## 2. Problem Statement

Without a durable execution model:
- Paid LLM work can be lost on navigation or crash
- Retries can duplicate cost or corrupt documents
- Partial execution is difficult to recover
- UI state becomes implicitly authoritative

A robust execution model is required that preserves intent, execution, LLM artifacts, and document mutations as first-class, governable entities.

## 3. Decision

Adopt a Durable LLM Threaded Queue with Execution Ledger.

All LLM-driven operations SHALL be executed via:
- **Threads** — durable containers for user intent
- **Work Items** — queue-executed units of work
- **Ledger Entries** — immutable records of LLM interactions
- **Explicit Mutations** — the only mechanism that alters canonical documents

This system is execution infrastructure, not logging or telemetry.

## 4. Explicit Non-Goals

This ADR does not:
- Introduce conversational chat as canonical state
- Allow LLM output to directly mutate documents
- Mix execution ledger with logging/telemetry
- Require real-time push (polling is sufficient)
- Mandate a specific worker implementation technology

## 5. Definitions

### 5.1 Thread (Intent Container)

A Thread represents one semantic user intent (e.g., "Generate stories for Epic X").

Threads are:
- Durable
- Idempotent by semantic identity
- Resumable
- Eventually closed

Threads are operation-scoped, not conversational.

### 5.2 Work Item (Execution Unit)

A Work Item is a single executable unit, typically:
- One LLM call
- Followed by validation
- Followed by a lock-safe mutation

Work Items define retry and failure boundaries.

### 5.3 Ledger Entry (Immutable Execution Record)

A Ledger Entry records what the system paid for and received.

Examples:
- Rendered prompt snapshot
- Raw LLM response
- Parse/validation report
- Mutation summary
- Execution error

Ledger entries are immutable and append-only.

### 5.4 Mutation

A Mutation is the sole allowed mechanism for modifying canonical stored documents.

All mutations:
- Run under explicit locks
- Are idempotent
- Validate against canonical schemas
- Record a mutation ledger entry

## 6. Canonical Data Structures (Minimum)

### 6.1 Thread

```
thread_id
kind                     // story_generate_epic, story_generate_all, etc.
space_type
space_id
target_ref               // document + optional epic
status                   // open | running | complete | failed | canceled
parent_thread_id         // for orchestration
idempotency_key
created_at
closed_at
```

### 6.2 Work Item

```
work_item_id
thread_id
sequence
status                   // queued | claimed | running | applied | failed | dead_letter
attempt
lock_scope               // project | epic:{id}
not_before
error_message            // last error if failed/dead_letter (optional but recommended)
created_at
started_at
finished_at
```

### 6.3 Ledger Entry

```
entry_id
thread_id
work_item_id (optional)
entry_type               // prompt | response | parse_report | mutation_report | error
payload | blob_ref
hash
created_at
```

## 7. Execution Semantics

### 7.1 Single-Epic Generation

1. Command creates or reuses a Thread
2. One Work Item is enqueued
3. Worker:
   - Records prompt ledger entry
   - Executes LLM call
   - Records response ledger entry
   - Validates output
   - Applies mutation under epic lock
4. Work Item marked terminal
5. Thread transitions to complete or failed

### 7.2 Generate-All Orchestration

1. Parent thread acquires project-level orchestration lock
2. Child threads are created per epic
3. Child threads execute independently
4. Parent thread closes when all children reach terminal state

Failure policy:
- Default: `continue_on_error`
- Parent thread records child outcomes

## 8. Idempotency Rules

Commands SHALL be idempotent by semantic identity, not UI session.

Example identity:
```
(project_id, story_backlog_id, epic_id, operation=generate_stories)
```

Rules:
- If a matching thread exists in `open | running` → return it
- If thread is `complete` → no-op unless explicit override (e.g., `force=true`)
- No duplicate Work Items may exist for the same semantic target concurrently

## 9. Locking Rules

- Epic-level locks are required for mutations
- Project-level lock is required for orchestration

Lock ordering:
- Project lock MAY NOT be acquired while holding an epic lock

Lock implementation is not mandated (DB, advisory, etc.), but semantics are required.

## 10. Failure & Retry Policy

Work Item failure does not automatically fail parent thread.

Retry rules:
- Transient failure → retry with backoff (`attempt++`)
- Permanent failure → `dead_letter`

User-triggered retry:
- Creates a new Work Item on the same Thread
- Must not violate idempotency

Work Item `error_message` field (optional but recommended): `error_message` is informational and MUST NOT be treated as authoritative execution state; authoritative failure context resides in immutable ledger entries.

## 11. UI & Navigation Guarantees

- UI navigation SHALL NOT affect execution
- Threads and Work Items continue independently

UI state is derived solely from:
- Canonical stored documents
- Thread metadata

No client-side state is authoritative.

## 12. API Contracts (Minimum)

### Commands

- `POST /commands/story-backlog/generate-epic`
- `POST /commands/story-backlog/generate-all`

Returns:
```
thread_id
status
```

### Observation

- `GET /threads/{thread_id}`
- `GET /projects/{project_id}/threads?active=true`

`GET /threads/{id}` MUST return:
```
thread_id
status
target_ref
created_at
closed_at
child_summary?   // counts by status for orchestration threads
```

## 13. Relationship to Telemetry / Logging

Execution Ledger and telemetry SHALL coexist but remain separate.

**Execution Ledger:**
- Correctness, audit, replay
- Product-visible

**Telemetry (e.g., `llm_call_records`):**
- Latency, metrics, provider diagnostics
- Ops-visible only

Telemetry MAY reference `thread_id` / `work_item_id` for correlation.

Execution Ledger MUST NOT depend on telemetry for correctness.

## 14. Consequences

### Positive

- No paid LLM work is lost
- Deterministic recovery and retries
- Clear audit trail
- UI decoupled from execution lifecycle

### Trade-offs

- Additional persistence entities
- Increased implementation complexity
- Requires disciplined schema governance

## 15. Acceptance Criteria

ADR-035 is correctly implemented if:

- All LLM calls produce immutable ledger entries
- User navigation does not interrupt execution
- No duplicate paid work occurs for the same semantic request
- All document mutations are explicit and idempotent
- Thread state can reconstruct execution post-hoc

## 16. Decision

**Option A is accepted:** full Thread + Work Item + Ledger model is implemented from the outset.

Deferral of these elements is explicitly rejected.
