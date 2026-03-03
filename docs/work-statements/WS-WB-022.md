# WS-WB-022: Implement Task Execution Primitive for Non-Workflow Call Sites

**Parent:** WP-WB-002
**Dependencies:** None

## Problem

We cannot let routers invent their own prompt loading / logging / validation path. We need a reusable service primitive.

## Deliverables

Create a small service module:
- `app/domain/services/task_execution_service.py`

With a function like:
- `execute_task(task_id, version, inputs, expected_schema_id) -> dict`

## Requirements

- Uses certified prompt loading convention (from combine-config task path)
- Centralizes:
  - prompt resolution (task_id + version as separate args)
  - LLM invocation
  - ADR-010-aligned logging hooks (whatever the system uses today)
  - output JSON parsing
  - schema validation before returning
- Governance enforcement:
  - Prompt must exist in combine-config (hard fail if missing)
  - Prompt version must be active/certified (hard fail if not)
  - Schema must exist and resolve (hard fail if missing)
  - LLM output must validate against schema before returning
  - All runs must produce a `correlation_id` for audit traceability
- **No persistence inside this primitive** — 022 is pure execution + validation. Persistence belongs to the calling station (e.g., WS-WB-025).
- Tier-1 tests:
  - missing prompt → hard fail
  - invalid JSON → hard fail
  - schema violation → hard fail
  - happy path with stubbed LLM client → returns validated output
  - correlation_id is present in return/log

## Acceptance

- WB propose endpoint (WS-WB-025) uses this service, not inline prompt handling
- No duplicate prompt-loading logic added to routers

## Allowed Paths

- `app/domain/services/task_execution_service.py`
- `tests/tier1/`

## Prohibited

- Do not modify existing workflow engine node executors
- Do not duplicate PromptLoader — reuse it
