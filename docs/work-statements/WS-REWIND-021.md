# WS-REWIND-021 — Preserve Authority Context Across Rewind Regeneration

**Status:** Draft
**Parent WP:** WP-REWIND-003
**Governing ADR:** ADR-063

## Objective

When the pipeline regenerates a stage after rewind, carry forward the authority context (PGC questions, PGC answers, bound constraints, correlation_id) from the prior execution so that QA gates can perform full compliance audits.

## Design Principle

> Rewind invalidates artifacts, not authority context.

PGC questions and answers represent user intent and decisions. They remain valid even when the generated artifacts they governed become stale. The regeneration should produce new artifacts governed by the same authority — not artifacts with no governance at all.

## Scope

### In Scope
- When regeneration starts a new execution for a stage, seed its context_state with authority context from the most recent prior execution of that stage
- Authority context includes: pgc_questions, pgc_answers, bound constraints
- If the prior execution had PGC phases, the new execution should skip PGC and proceed directly to generation (since answers are carried forward)
- Log that authority context was inherited, not freshly gathered

### Out of Scope
- Re-running PGC with new questions (that's a fresh execution, not regeneration)
- Modifying PGC questions based on upstream changes
- Cross-stage authority inheritance (each stage owns its own PGC context)

## Procedure

### Step 1: Identify authority context fields
- `pgc_questions`: list of PGC questions asked
- `pgc_answers`: dict of user answers
- `input_documents`: upstream documents used as input
- Bound constraints from intake/discovery

### Step 2: On regeneration, load prior execution context
- Query most recent execution for the same (project_id, document_type) with status=completed
- Extract authority context fields from its context_state
- Seed the new execution's context_state with these fields

### Step 3: Skip PGC phase when authority context is inherited
- If context_state already has pgc_questions and pgc_answers, the PGC gate should auto-resolve
- Log: "Authority context inherited from prior execution {execution_id}"

### Step 4: Update input_documents with current upstream
- While PGC context is carried forward, input_documents must reference the NEW upstream artifacts (the regenerated ones), not the stale ones

### Step 5: QA gate receives full authority bundle
- With carried-forward PGC context, QA semantic compliance can perform full audit
- WS-REWIND-020 graceful degradation remains as safety net

## Verification Criteria
- Regeneration after rewind produces documents that pass QA with full compliance audit
- PGC phase is skipped when authority context is inherited
- Authority context is logged as inherited
- Input documents reference current (not stale) upstream artifacts
- QA gate receives pgc_questions, pgc_answers, and bound constraints

## Allowed Paths
- app/domain/workflow/plan_executor.py
- app/domain/workflow/pg_state_persistence.py
- app/domain/services/regeneration_service.py
- tests/tier1/

## Prohibited Actions
- Do not modify PGC question generation logic
- Do not change PGC user interaction flow
- Do not carry forward stale input_documents
