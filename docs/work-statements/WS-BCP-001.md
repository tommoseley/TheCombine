# WS-BCP-001: Backlog Compilation Pipeline — Foundation (Schemas, Intent Intake, Backlog Generator DCW)

## Status: Draft

## Purpose

Establish the foundation layer of the Backlog Compilation Pipeline: the schemas that define IntentPacket and BacklogItem, a mechanical intake service for persisting raw intent before any LLM runs, and the Backlog Generator DCW that transforms an IntentPacket into a validated list of BacklogItems.

This is the first of four work statements implementing the Backlog Compilation Pipeline Implementation Plan. Nothing downstream (graph validation, ordering, explanation) can be built or tested without these artifacts.

## Governing References

- **Backlog Compilation Pipeline Implementation Plan** (`docs/implementation-plans/BACKLOG-COMPILATION-PIPELINE-Implementation-Plan.md`)
- **ADR-009**: Project Audit (all state changes explicit and traceable)
- **ADR-010**: LLM Execution Logging (inputs, outputs, replay capability)
- **ADR-040**: Stateless LLM Execution (no transcript replay)
- **ADR-045**: System Ontology (Primitives, Composites, Configuration Taxonomy)
- **ADR-049**: No Black Boxes (DCWs must be explicitly composed)
- **POL-WS-001**: Work Statement Standard
- **DQ-1**: IntentPacket is mechanical intake, persisted before any LLM runs
- **DQ-2**: QA gate is narrow (structural invariants only); graph layer owns dependency/hierarchy validation
- **Existing**: `document_generator` template v1.0.0 (reused for generation node)
- **Existing**: `qa_semantic_compliance` task v1.1.0 (reused for QA gate)
- **Existing**: Multi-instance document support via `instance_id` (WS-INSTANCE-ID-001, complete)

## Scope

### In Scope

- Define `intent_packet` JSON schema (v1.0.0)
- Define `backlog_item` JSON schema (v1.0.0)
- Register `intent_packet` document type (cardinality: single)
- Register `backlog_item` document type (cardinality: multi, instance_key: `id`)
- Create Intent Intake API endpoints (`POST /intents`, `GET /intents/{id}`)
- Create minimal Intent Intake UI (textarea + submit)
- Create Backlog Generator task prompt (v1.0.0)
- Create Backlog Generator DCW definition (v1.0.0)
- Create BacklogGeneratorHandler (parse, validate, transform, spawn children)
- Register new artifacts in `active_releases.json`
- Unit tests for handler, schema validation, and intake endpoints

### Out of Scope

- Graph validation (dependency existence, hierarchy rules, cycles) — WS-BCP-002
- Topological sort, wave grouping, ExecutionPlan derivation — WS-BCP-002
- Explanation Generator DCW — WS-BCP-003
- End-to-end pipeline integration — WS-BCP-004
- Replay metadata / observability — WS-BCP-004
- Intent editor, intent versioning, or intent revision UX
- Backlog editing UI or reprioritization loops
- ExecutionPlan schema (derived artifact, created in WS-BCP-002)

## Preconditions

1. Multi-instance document support (`instance_id` column, partial unique indexes) is in place (WS-INSTANCE-ID-001 complete)
2. `document_generator` template v1.0.0 exists and is active
3. `qa_semantic_compliance` task v1.1.0 exists and is active
4. `quality_assurance` role prompt v1.0.0 exists and is active
5. `project_manager` role prompt v1.0.0 exists and is active
6. Handler registry pattern established (`app/domain/handlers/registry.py`)
7. DCW engine and PlanExecutor can execute workflows with generation + QA gate + remediation pattern

---

## Phase 1: Schema Definitions

**Objective:** Define the JSON schemas for IntentPacket and BacklogItem and register both as document types.

### Step 1.1: Create IntentPacket schema

**File:** `combine-config/schemas/intent_packet/releases/1.0.0/schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "IntentPacket",
  "description": "Raw user intent normalized for pipeline input. Immutable once persisted.",
  "type": "object",
  "required": ["raw_intent"],
  "properties": {
    "raw_intent": {
      "type": "string",
      "minLength": 1,
      "description": "The raw intent text as provided by the user. Never LLM-normalized."
    },
    "constraints": {
      "type": ["string", "null"],
      "description": "Known constraints on the work (technical, timeline, resource, etc.)."
    },
    "success_criteria": {
      "type": ["string", "null"],
      "description": "What success looks like for this intent."
    },
    "context": {
      "type": ["string", "null"],
      "description": "Additional context (project background, domain notes, etc.)."
    },
    "schema_version": {
      "type": "string",
      "const": "1.0.0"
    }
  },
  "additionalProperties": false
}
```

### Step 1.2: Create BacklogItem schema

**File:** `combine-config/schemas/backlog_item/releases/1.0.0/schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "BacklogItem",
  "description": "Unified backlog item with level discriminator. One schema for EPIC, FEATURE, and STORY.",
  "type": "object",
  "required": ["id", "level", "title", "description", "priority_score", "depends_on"],
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^[EFS]\\d{3}$",
      "description": "Level-prefixed ID: E### for EPIC, F### for FEATURE, S### for STORY."
    },
    "level": {
      "type": "string",
      "enum": ["EPIC", "FEATURE", "STORY"]
    },
    "title": {
      "type": "string",
      "minLength": 1
    },
    "description": {
      "type": "string",
      "minLength": 1
    },
    "priority_score": {
      "type": "integer",
      "minimum": 1,
      "description": "Priority as integer. Higher = more important. Used for intra-tier ordering."
    },
    "depends_on": {
      "type": "array",
      "items": {
        "type": "string",
        "pattern": "^[EFS]\\d{3}$"
      },
      "description": "IDs this item depends on. Empty array if no dependencies."
    },
    "parent_id": {
      "type": ["string", "null"],
      "pattern": "^[EFS]\\d{3}$",
      "description": "Parent item ID. Null for EPICs. Required for FEATURE (must ref EPIC) and STORY (must ref FEATURE)."
    }
  },
  "additionalProperties": false,
  "if": {
    "properties": { "level": { "const": "EPIC" } }
  },
  "then": {
    "properties": { "parent_id": { "const": null } }
  },
  "else": {
    "required": ["parent_id"],
    "properties": {
      "parent_id": { "type": "string", "pattern": "^[EFS]\\d{3}$" }
    }
  }
}
```

Note: The schema enforces that EPICs have `parent_id: null` and FEATURE/STORY have non-null `parent_id`. Level-to-level validation (FEATURE→EPIC, STORY→FEATURE) is enforced by the graph validator in WS-BCP-002.

### Step 1.3: Create BacklogItem list wrapper schema

**File:** `combine-config/schemas/backlog_item/releases/1.0.0/list.schema.json`

The DCW output is a list of backlog items, wrapped for document persistence:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "BacklogItemList",
  "description": "Output of the Backlog Generator DCW. A list of BacklogItems for a single intent.",
  "type": "object",
  "required": ["intent_id", "items"],
  "properties": {
    "intent_id": {
      "type": "string",
      "description": "Reference to the source IntentPacket."
    },
    "items": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "schema.json" }
    }
  },
  "additionalProperties": false
}
```

### Step 1.4: Register document types

**File:** `combine-config/document_types/intent_packet/releases/1.0.0/package.yaml`

```yaml
doc_type_id: intent_packet
display_name: Intent Packet
version: 1.0.0

description: >
  Raw user intent persisted as an immutable input to the Backlog Compilation Pipeline.
  Created by mechanical intake (no LLM involvement). Never modified after creation.

authority_level: descriptive
creation_mode: manual
production_mode: intake
scope: project

required_inputs: []
optional_inputs: []

schema_ref: "schema:intent_packet:1.0.0"

artifacts:
  schema: schemas/output.schema.json

ui:
  icon: lightbulb
  category: planning
  display_order: 1
```

**File:** `combine-config/document_types/intent_packet/releases/1.0.0/schemas/output.schema.json`

Copy of `combine-config/schemas/intent_packet/releases/1.0.0/schema.json`.

**File:** `combine-config/document_types/backlog_item/releases/1.0.0/package.yaml`

```yaml
doc_type_id: backlog_item
display_name: Backlog Item
version: 1.0.0

description: >
  Unified backlog item (EPIC/FEATURE/STORY) generated by the Backlog Generator DCW.
  Multi-instance document type: one document per backlog item, keyed by item ID.

authority_level: constructive
creation_mode: llm_generated
production_mode: generate
scope: project

required_inputs:
  - intent_packet
optional_inputs: []

role_prompt_ref: "prompt:role:project_manager:1.0.0"
template_ref: "prompt:template:document_generator:1.0.0"
schema_ref: "schema:backlog_item:1.0.0"

artifacts:
  task_prompt: prompts/task.prompt.txt
  schema: schemas/output.schema.json

ui:
  icon: list
  category: planning
  display_order: 2
```

**File:** `combine-config/document_types/backlog_item/releases/1.0.0/schemas/output.schema.json`

Copy of `combine-config/schemas/backlog_item/releases/1.0.0/schema.json`.

### Step 1.5: Register document types in database

**File:** `alembic/versions/YYYYMMDD_NNN_add_bcp_document_types.py`

Insert rows into `document_types`:

```sql
INSERT INTO document_types (doc_type_id, display_name, cardinality, instance_key)
VALUES ('intent_packet', 'Intent Packet', 'single', NULL);

INSERT INTO document_types (doc_type_id, display_name, cardinality, instance_key)
VALUES ('backlog_item', 'Backlog Item', 'multi', 'id');
```

### Step 1.6: Update active_releases.json

**File:** `combine-config/_active/active_releases.json`

Add to `document_types`:
```json
"intent_packet": "1.0.0",
"backlog_item": "1.0.0"
```

Add to `schemas`:
```json
"intent_packet": "1.0.0",
"backlog_item": "1.0.0"
```

**Verification:**

- Both schemas validate against JSON Schema draft 2020-12
- `BacklogItem` schema rejects: missing `id`, non-integer `priority_score`, invalid `level`, EPIC with non-null `parent_id`, FEATURE with null `parent_id`, `id` not matching `^[EFS]\d{3}$`
- `IntentPacket` schema rejects: missing `raw_intent`, additional properties
- Database has both document type rows with correct cardinality
- `active_releases.json` includes both types and schemas

---

## Phase 2: Intent Intake Service

**Objective:** Create API endpoints and minimal UI for persisting IntentPackets before any LLM runs.

### Step 2.1: Create intent intake router

**File:** `app/api/v1/routers/intents.py`

```python
# POST /api/v1/intents
# - Accepts: { raw_intent, constraints?, success_criteria?, context? }
# - Validates against intent_packet schema
# - Persists as Document (doc_type_id='intent_packet', space_type='project', space_id=project_id)
# - Returns: { intent_id: <document.id>, created_at: <timestamp> }

# GET /api/v1/intents/{intent_id}
# - Returns the IntentPacket document content
# - 404 if not found
```

Key constraints:
- No LLM involvement — this is a mechanical write
- Validate against `intent_packet` schema before persisting
- Set `is_latest = TRUE`, `version = 1`, `status = 'complete'`
- IntentPacket is immutable — no PUT/PATCH endpoint. To revise, create a new one.

### Step 2.2: Register router

**File:** `app/api/v1/__init__.py` (or wherever routers are mounted)

Mount the intents router at `/api/v1/intents`.

### Step 2.3: Create minimal intake UI

**File:** `spa/src/pages/IntentIntake.jsx` (or appropriate SPA location)

Minimal form:
- Textarea for `raw_intent` (required)
- Textarea for `constraints` (optional)
- Textarea for `success_criteria` (optional)
- Textarea for `context` (optional)
- Submit button
- On submit: POST to `/api/v1/intents`, display returned `intent_id`
- No edit capability — display "Intent saved" with ID for reference

### Step 2.4: Add SPA route

Wire the intake page into the SPA router so it's navigable.

**Verification:**

- `POST /api/v1/intents` with valid payload returns 201 with `intent_id`
- `POST /api/v1/intents` with empty `raw_intent` returns 422
- `POST /api/v1/intents` with extra fields returns 422 (additionalProperties: false)
- `GET /api/v1/intents/{id}` returns persisted content
- `GET /api/v1/intents/{invalid_id}` returns 404
- Document is persisted with `doc_type_id='intent_packet'`, `is_latest=TRUE`
- UI form submits successfully and displays intent_id
- No LLM calls made during intake

---

## Phase 3: Backlog Generator DCW

**Objective:** Create the DCW that transforms an IntentPacket into a validated list of BacklogItems, with a narrow QA gate enforcing structural invariants only.

### Step 3.1: Create Backlog Generator task prompt

**File:** `combine-config/prompts/tasks/backlog_generator/releases/1.0.0/task.prompt.txt`

The prompt must instruct the LLM to:
- Read the IntentPacket content (raw_intent, constraints, success_criteria, context)
- Decompose into a structured backlog with EPICs, FEATUREs, and STORYs
- Use ID format: `E###` for EPICs, `F###` for FEATUREs, `S###` for STORYs
- Assign integer `priority_score` to each item (higher = more important)
- Set `depends_on` arrays referencing valid IDs within the output
- Set `parent_id`: null for EPICs, EPIC ID for FEATUREs, FEATURE ID for STORYs
- Output as JSON matching the BacklogItemList schema
- Produce at least 1 EPIC

**File:** `combine-config/prompts/tasks/backlog_generator/releases/1.0.0/meta.yaml`

```yaml
task_id: backlog_generator
version: 1.0.0
description: Generate structured backlog from intent packet
document_type: backlog_item
```

### Step 3.2: Create Backlog Generator DCW definition

**File:** `combine-config/workflows/backlog_generator/releases/1.0.0/definition.json`

Follow the existing DCW pattern (workflow.v2 schema). Structure:

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
|------|------|------------|---------|
| `generation` | task (LLM) | role: `project_manager:1.0.0`, task: `backlog_generator:1.0.0`, schema: `backlog_item:1.0.0` | DRAFT (1) |
| `qa_gate` | gate (qa) | role: `quality_assurance:1.0.0`, task: `qa_semantic_compliance:1.1.0` | QA (2) |
| `remediation` | task (LLM) | same as generation + QA feedback input | QA (2) |
| `end_stabilized` | end | terminal_outcome: stabilized | DONE (3) |
| `end_blocked` | end | terminal_outcome: blocked | DONE (3) |

QA gate scope (narrow, per DQ-2):
- Schema-valid JSON
- All IDs present, unique, match `^[EFS]\d{3}$`
- All `priority_score` values are integers
- `parent_id` required on FEATURE and STORY, null on EPIC
- At least 1 EPIC in the output
- QA gate does NOT validate: dependency existence, cycles, hierarchy level rules

Circuit breaker: max 2 remediation attempts.

### Step 3.3: Create BacklogGeneratorHandler

**File:** `app/domain/handlers/backlog_generator_handler.py`

Extends `BaseDocumentHandler`:

```python
class BacklogGeneratorHandler(BaseDocumentHandler):
    doc_type_id = "backlog_item"

    def parse(self, raw_content: str) -> dict:
        # Extract JSON from LLM output (handle markdown fences)

    def validate(self, data: dict) -> dict:
        # Validate against backlog_item list.schema.json

    def get_child_documents(self, content: dict, **kwargs) -> list[dict]:
        # Extract each item from content["items"]
        # Return child specs with identifier = item["id"]
        # Each becomes a backlog_item document with instance_id = item id
```

### Step 3.4: Register handler

**File:** `app/domain/handlers/registry.py`

Add:
```python
"backlog_item": BacklogGeneratorHandler(),
```

### Step 3.5: Update active_releases.json

**File:** `combine-config/_active/active_releases.json`

Add to `workflows`:
```json
"backlog_generator": "1.0.0"
```

Add to `tasks`:
```json
"backlog_generator": "1.0.0"
```

**Verification:**

- DCW definition validates against workflow.v2 schema
- Starting the Backlog Generator DCW with a valid IntentPacket produces backlog items
- QA gate rejects: missing IDs, non-integer priorities, FEATURE with null parent_id, output with 0 EPICs
- QA gate accepts: structurally valid backlog (even if dependencies reference non-existent IDs — graph layer's job)
- Each backlog item is spawned as a `backlog_item` document with `instance_id` = item `id`
- Re-running with same intent updates existing items (idempotent via instance_id)
- Remediation loop works: QA failure triggers regeneration, max 2 attempts, then blocked
- Prompt version and model version logged per ADR-010
- All existing tests pass

---

## Prohibited Actions

- Do not validate dependency existence, hierarchy level rules, or cycles in the QA gate — graph layer owns these (DQ-2)
- Do not allow the LLM to normalize or rewrite the IntentPacket content — intake is mechanical
- Do not create PUT/PATCH endpoints for IntentPacket — revise by creating a new one
- Do not add `status`, `sprint`, `effort`, `owner`, or `velocity` fields to BacklogItem
- Do not create the ExecutionPlan schema or derivation logic — that is WS-BCP-002
- Do not use fractional `priority_score` — integer only (per backlog_hash canonicalization rule)
- Do not set `instance_id` on `intent_packet` documents — they are single-instance
- Do not create separate schemas for EPIC, FEATURE, and STORY — one schema, one `level` field
- Do not build intent versioning, editing, or revision tracking UX

## Verification Checklist

1. **IntentPacket schema valid:** Schema validates against JSON Schema 2020-12; rejects missing `raw_intent`, extra fields
2. **BacklogItem schema valid:** Schema validates; rejects missing ID, non-integer priority, invalid level, ID format violations, EPIC with parent_id, FEATURE without parent_id
3. **Document types registered:** Both rows exist in `document_types` with correct cardinality and instance_key
4. **active_releases.json updated:** Both document types, schemas, workflow, and task prompt registered
5. **Intent intake works:** `POST /intents` persists packet, returns ID; `GET /intents/{id}` returns content; no LLM calls
6. **Intent intake rejects invalid:** Empty `raw_intent` returns 422; extra fields return 422
7. **DCW produces backlog:** Starting backlog_generator with a valid IntentPacket produces structurally valid BacklogItem list
8. **QA gate is narrow:** QA gate rejects structural violations; accepts backlog with invalid dependency references (graph layer's job)
9. **Child documents spawned:** Each backlog item persisted as `backlog_item` document with `instance_id` = item `id`
10. **Idempotent re-run:** Re-running DCW with same intent updates existing items, no duplicates
11. **Remediation works:** QA failure triggers remediation; circuit breaker at 2 attempts
12. **UI works:** Intake form submits, displays intent_id
13. **Tests pass:** All existing tests pass; new tests cover handler, schema validation, intake endpoints (`python -m pytest tests/ -x -q`)

## Definition of Done

- `intent_packet` and `backlog_item` schemas exist and validate correctly
- Both document types registered in DB and `active_releases.json`
- Intent Intake API persists packets mechanically (no LLM) and returns stable IDs
- Minimal intake UI exists and is navigable in the SPA
- Backlog Generator DCW exists with generation → QA gate → remediation pattern
- QA gate enforces structural invariants only (narrow scope per DQ-2)
- BacklogGeneratorHandler parses, validates, and spawns child documents with `instance_id`
- Task prompt instructs correct ID format (`E###`/`F###`/`S###`), integer priorities, and hierarchy rules
- All new code covered by tests
- SPA builds clean
