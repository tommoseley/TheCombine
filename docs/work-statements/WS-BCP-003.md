# WS-BCP-003: Backlog Compilation Pipeline — Plan Explanation Generator

## Status: Draft

## Purpose

Build the human explanation layer: an LLM-powered DCW that takes the mechanically derived ExecutionPlan and produces a 1-2 paragraph explanation of why the ordering makes sense. The LLM explains — it never computes or reorders.

This is the third of four work statements. WS-BCP-001 delivered schemas and the Backlog Generator DCW. WS-BCP-002 delivered graph validation and deterministic ordering. This work statement adds the explanation that makes the mechanical output legible to humans.

## Governing References

- **Backlog Compilation Pipeline Implementation Plan** (`docs/implementation-plans/BACKLOG-COMPILATION-PIPELINE-Implementation-Plan.md`)
- **WS-BCP-001** (complete): Foundation — schemas, intent intake, backlog generator DCW
- **WS-BCP-002** (complete): Graph validation, ordering engine, ExecutionPlan derivation
- **ADR-010**: LLM Execution Logging (inputs, outputs, replay)
- **ADR-040**: Stateless LLM Execution (no transcript replay)
- **ADR-045**: System Ontology
- **ADR-049**: No Black Boxes (DCWs explicitly composed)
- **Design Principle**: "LLMs generate. Machines order." — the LLM shines at explanation, not computation

## Scope

### In Scope

- **Task 8**: Plan Explanation Generator DCW
- `plan_explanation` task prompt (v1.0.0)
- `plan_explanation` DCW definition (v1.0.0) — QA-only pattern
- `plan_explanation` JSON schema (v1.0.0)
- `plan_explanation` document type registration (cardinality: single)
- `PlanExplanationHandler` document handler
- Alembic migration for `plan_explanation` document type
- Update `active_releases.json`

### Out of Scope

- End-to-end pipeline integration (triggering the full pipeline) — WS-BCP-004
- Replay metadata / observability — WS-BCP-004
- Explanation editing or regeneration UI — future work
- Multi-language explanation — future work
- Explanation as input to any downstream process — explanation is terminal output

## Preconditions

1. WS-BCP-002 complete: `execution_plan` document type, `derive_execution_plan` function, `compute_waves` function all exist
2. BacklogItem schema and backlog_generator DCW produce validated items
3. `document_generator` template v1.0.0 active
4. `qa_semantic_compliance` task v1.1.0 active
5. `project_manager` role prompt v1.0.0 active
6. `quality_assurance` role prompt v1.0.0 active

---

## Phase 1: Plan Explanation Schema & Document Type

**Objective:** Define what a plan explanation looks like and register it as a document type.

### Step 1.1: Create PlanExplanation schema

**File:** `combine-config/schemas/plan_explanation/releases/1.0.0/schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "PlanExplanation",
  "description": "Human-readable explanation of a mechanically derived execution plan.",
  "type": "object",
  "required": ["backlog_hash", "explanation", "wave_summaries"],
  "properties": {
    "backlog_hash": {
      "type": "string",
      "pattern": "^[a-f0-9]{64}$",
      "description": "The backlog_hash of the ExecutionPlan being explained."
    },
    "explanation": {
      "type": "string",
      "minLength": 1,
      "description": "1-2 paragraph natural language explanation of the ordering rationale."
    },
    "wave_summaries": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["wave_number", "summary"],
        "properties": {
          "wave_number": { "type": "integer", "minimum": 1 },
          "summary": { "type": "string", "minLength": 1 }
        },
        "additionalProperties": false
      },
      "minItems": 1,
      "description": "Per-wave one-line summary explaining what the wave delivers and why it's safe to parallelize."
    }
  },
  "additionalProperties": false
}
```

The explanation includes both a holistic narrative (`explanation`) and per-wave summaries (`wave_summaries`), giving operators context at two levels of detail.

### Step 1.2: Create document type package

**File:** `combine-config/document_types/plan_explanation/releases/1.0.0/package.yaml`

```yaml
doc_type_id: plan_explanation
display_name: Plan Explanation
version: 1.0.0

description: >
  LLM-generated explanation of a mechanically derived execution plan.
  Explains why the ordering makes sense — never computes or reorders.
  Stored separately from ExecutionPlan.

authority_level: descriptive
creation_mode: llm_generated
production_mode: generate
scope: project

required_inputs:
  - execution_plan
optional_inputs: []

role_prompt_ref: "prompt:role:project_manager:1.0.0"
template_ref: "prompt:template:document_generator:1.0.0"
schema_ref: "schema:plan_explanation:1.0.0"

artifacts:
  task_prompt: prompts/task.prompt.txt
  schema: schemas/output.schema.json

ui:
  icon: message-square
  category: planning
  display_order: 4
```

**File:** `combine-config/document_types/plan_explanation/releases/1.0.0/schemas/output.schema.json`

Copy of the canonical schema.

### Step 1.3: Create database migration

**File:** `alembic/versions/YYYYMMDD_NNN_add_plan_explanation_document_type.py`

```sql
INSERT INTO document_types (doc_type_id, display_name, cardinality, instance_key)
VALUES ('plan_explanation', 'Plan Explanation', 'single', NULL);
```

### Step 1.4: Update active_releases.json

Add to `document_types`: `"plan_explanation": "1.0.0"`
Add to `schemas`: `"plan_explanation": "1.0.0"`

**Verification:**

- Schema validates against JSON Schema 2020-12
- Schema rejects: missing `explanation`, missing `backlog_hash`, empty `wave_summaries`
- Document type registered in DB with cardinality `single`
- `active_releases.json` updated

---

## Phase 2: Task Prompt & DCW Definition

**Objective:** Create the task prompt that instructs the LLM to explain the plan, and the DCW that orchestrates generation + QA.

### Step 2.1: Create plan explanation task prompt

**File:** `combine-config/prompts/tasks/plan_explanation/releases/1.0.0/task.prompt.txt`

The prompt must instruct the LLM to:
- Receive: backlog items (with levels, dependencies, priorities), the execution plan (ordered_backlog_ids, waves), and the original intent
- Produce: a holistic 1-2 paragraph explanation + per-wave summaries
- Reference dependencies, priority scores, and wave grouping explicitly
- Explain *why* the order makes sense, not just *what* the order is
- Note which items are safe to parallelize within each wave and why
- NOT reorder, add, remove, or modify any backlog items
- NOT suggest changes to priorities or dependencies
- Output as JSON matching the `plan_explanation` schema

**File:** `combine-config/prompts/tasks/plan_explanation/releases/1.0.0/meta.yaml`

```yaml
task_id: plan_explanation
version: 1.0.0
description: Explain the rationale behind a mechanically derived execution plan
document_type: plan_explanation
```

### Step 2.2: Create Plan Explanation DCW definition

**File:** `combine-config/workflows/plan_explanation/releases/1.0.0/definition.json`

QA-only pattern (same structure as backlog_generator):

```
generation (task/LLM)
  -> qa_gate (gate/qa)
      -> pass: end_stabilized
      -> fail (retries < 2): remediation (task/LLM)
      -> fail (retries >= 2): end_blocked
  remediation -> qa_gate (re-evaluate)
```

Node details:

| Node | Type | Prompt Refs | Station |
|------|------|-------------|---------|
| `generation` | task (LLM) | role: `project_manager:1.0.0`, task: `plan_explanation:1.0.0`, schema: `plan_explanation:1.0.0` | DRAFT (1) |
| `qa_gate` | gate (qa) | role: `quality_assurance:1.0.0`, task: `qa_semantic_compliance:1.1.0` | QA (2) |
| `remediation` | task (LLM) | same as generation + QA feedback | QA (2) |
| `end_stabilized` | end | terminal_outcome: stabilized | DONE (3) |
| `end_blocked` | end | terminal_outcome: blocked | DONE (3) |

QA gate scope:
- Schema-valid JSON
- `backlog_hash` present and matches the input execution plan's hash
- `explanation` is non-empty
- `wave_summaries` array has same length as waves in the execution plan
- Each wave_summary has a non-empty `summary`

QA gate does NOT validate:
- Quality of the explanation prose (subjective)
- Whether explanation accurately reflects the ordering (would require understanding the graph)

Circuit breaker: max 2 remediation attempts.

### Step 2.3: Update active_releases.json

Add to `workflows`: `"plan_explanation": "1.0.0"`
Add to `tasks`: `"plan_explanation": "1.0.0"`

**Verification:**

- DCW definition validates against workflow.v2 schema
- Task prompt includes clear instructions for what to explain and what not to modify
- Prompt version stored with every run (per ADR-010)
- QA gate checks structural validity of explanation output

---

## Phase 3: Handler & Registry

**Objective:** Create the handler that processes plan explanation documents and register it.

### Step 3.1: Create PlanExplanationHandler

**File:** `app/domain/handlers/plan_explanation_handler.py`

Extends `BaseDocumentHandler`:
- `doc_type_id = "plan_explanation"`
- `extract_title()` — returns "Plan Explanation"
- `render()` — renders explanation paragraph + wave summaries
- `render_summary()` — first sentence of explanation
- No children, no transform

### Step 3.2: Register handler

**File:** `app/domain/handlers/registry.py`

Add: `"plan_explanation": PlanExplanationHandler()`

**Verification:**

- Handler registered in registry
- `render()` produces readable HTML with explanation and wave summaries
- `render_summary()` returns concise summary text

---

## Prohibited Actions

- Do not allow the LLM to reorder, add, remove, or modify backlog items — explanation is read-only
- Do not allow the LLM to suggest changes to priorities or dependencies
- Do not use the explanation as input to any downstream computation or ordering
- Do not store the explanation inside the ExecutionPlan document — it is a separate document
- Do not create a PGC gate — this is QA-only pattern (no operator questions needed)
- Do not build explanation editing or regeneration UI
- Do not build end-to-end pipeline integration — that is WS-BCP-004

## Verification Checklist

1. **Schema valid:** PlanExplanation schema validates; rejects missing explanation, empty wave_summaries
2. **Document type registered:** `plan_explanation` in DB with cardinality single; in `active_releases.json`
3. **Task prompt correct:** Instructs explanation only, prohibits reordering, requires JSON output matching schema
4. **DCW definition valid:** QA-only pattern with generation → QA gate → remediation; circuit breaker at 2
5. **QA gate scope correct:** Checks schema validity, backlog_hash match, wave_summaries count; does not evaluate prose quality
6. **Handler registered:** PlanExplanationHandler in registry; renders explanation + wave summaries
7. **active_releases.json complete:** document type, schema, workflow, and task all registered
8. **All tests pass:** `python -m pytest tests/ -x -q` — no regressions

## Definition of Done

- `plan_explanation` schema defines explanation + wave_summaries structure
- Document type registered in DB and `active_releases.json`
- Task prompt instructs LLM to explain (never compute) the execution plan
- DCW uses QA-only pattern with remediation loop and circuit breaker
- PlanExplanationHandler registered and renders correctly
- Explanation is stored as a separate document from ExecutionPlan
- All existing tests continue to pass
