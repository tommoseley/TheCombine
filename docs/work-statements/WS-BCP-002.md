# WS-BCP-002: Backlog Compilation Pipeline — Graph Validation & Deterministic Ordering

## Status: Draft

## Purpose

Build the mechanical core of the Backlog Compilation Pipeline: the graph validator that enforces dependency and hierarchy correctness, the cycle detector, the topological sort that produces deterministic ordering, and the ExecutionPlan derivation that computes waves and persists the result.

This is the second of four work statements. WS-BCP-001 delivered the schemas, intent intake, and Backlog Generator DCW. This work statement takes the raw LLM-generated backlog and compiles it into a validated, ordered, deterministic execution plan. No LLM is involved — this is pure mechanical compilation.

## Governing References

- **Backlog Compilation Pipeline Implementation Plan** (`docs/implementation-plans/BACKLOG-COMPILATION-PIPELINE-Implementation-Plan.md`)
- **WS-BCP-001** (complete): Foundation — schemas, intent intake, backlog generator DCW
- **ADR-009**: Project Audit (all state changes explicit and traceable)
- **ADR-045**: System Ontology
- **DQ-2**: Fail-fast in graph layer, no self-heal. Graph validator is single authority for graph correctness.
- **DQ-3**: Waves are derived, non-authoritative. Total order is authoritative.
- **Design Principle**: "LLMs generate. Machines order."

## Scope

### In Scope

- **Task 4a**: Dependency validation service (`validate_dependencies`)
- **Task 4b**: Hierarchy validation service (`validate_hierarchy`)
- **Task 5**: Dependency cycle detection (`detect_dependency_cycles`)
- **Task 6**: Topological sort with priority tie-breaking (`order_backlog`)
- **Task 7**: ExecutionPlan derivation with wave grouping (`derive_execution_plan`)
- ExecutionPlan schema and document type registration
- `backlog_hash` computation function
- Comprehensive tier-1 unit tests for all domain functions
- Alembic migration for `execution_plan` document type

### Out of Scope

- Explanation Generator DCW (LLM-produced rationale) — WS-BCP-003
- End-to-end pipeline integration (trigger full pipeline from intent) — WS-BCP-004
- Replay metadata / observability — WS-BCP-004
- Auto-regeneration loops (re-prompt on dependency errors) — future work
- UI for graph validation results — future work
- Backlog editing or dependency editing UI — explicit non-goal

## Preconditions

1. WS-BCP-001 complete: `intent_packet` and `backlog_item` schemas, document types, and handlers exist
2. `BacklogItem` schema enforces ID format `^[EFS]\d{3}$`, integer `priority_score`, and parent_id presence rules
3. Backlog Generator DCW produces structurally valid `BacklogItemList` (schema-valid, IDs present/unique)
4. Multi-instance document support via `instance_id` is in place

---

## Phase 1: Graph Validation Services

**Objective:** Create the domain service functions that validate a backlog's dependency graph and hierarchy. These are pure functions — no DB, no LLM, no side effects.

### Step 1.1: Create graph validation module

**File:** `app/domain/services/graph_validator.py`

This module contains all validation functions. Each returns a typed result, never raises exceptions for validation failures.

#### Data types

```python
@dataclass
class DependencyError:
    """A single dependency validation failure."""
    item_id: str
    error_type: str  # "missing_reference" | "self_reference"
    detail: str

@dataclass
class DependencyResult:
    """Result of dependency validation."""
    valid: bool
    errors: list[DependencyError]

@dataclass
class HierarchyError:
    """A single hierarchy validation failure."""
    item_id: str
    error_type: str  # "hierarchy_violation" | "invalid_level_transition" | "orphaned_item" | "parent_not_found" | "parent_cycle"
    detail: str

@dataclass
class HierarchyResult:
    """Result of hierarchy validation."""
    valid: bool
    errors: list[HierarchyError]

@dataclass
class CycleTrace:
    """A detected dependency cycle."""
    cycle: list[str]  # e.g., ["E001", "F002", "S003", "E001"]

@dataclass
class CycleResult:
    """Result of dependency cycle detection."""
    has_cycles: bool
    cycles: list[CycleTrace]
```

### Step 1.2: Implement dependency validation (Task 4a)

**Function:** `validate_dependencies(items: list[dict]) -> DependencyResult`

Checks:
- Every ID in every item's `depends_on` list exists in the item set
- No item depends on itself

Error types:
- `MissingReference` — `depends_on` contains an ID not present in the backlog
- `SelfReference` — item's `depends_on` contains its own ID

Returns all errors (not just the first). Fail hard — no silent correction.

### Step 1.3: Implement hierarchy validation (Task 4b)

**Function:** `validate_hierarchy(items: list[dict]) -> HierarchyResult`

Checks (per Hierarchy Rules table in implementation plan):
- EPIC: `parent_id` must be `null`
- FEATURE: `parent_id` must reference an item with `level: EPIC`
- STORY: `parent_id` must reference an item with `level: FEATURE`
- Every `parent_id` (when non-null) must reference an existing item
- Parent chain must terminate — no cycles in parent_id references

Error types:
- `HierarchyViolation` — `parent_id` points to wrong level (e.g., FEATURE→FEATURE)
- `InvalidLevelTransition` — invalid parent/child level combination
- `OrphanedItem` — FEATURE or STORY with null `parent_id`
- `ParentNotFound` — `parent_id` references non-existent item
- `ParentCycle` — parent_id chain forms a cycle (A→B→A)

Returns all errors. Fail hard — no silent correction.

### Step 1.4: Implement dependency cycle detection (Task 5)

**Function:** `detect_dependency_cycles(items: list[dict]) -> CycleResult`

Scope: `depends_on` edges only. Parent cycles are Task 4b's responsibility.

Algorithm: DFS-based cycle detection over the `depends_on` directed graph. Returns human-readable cycle traces (e.g., `["E001", "F002", "S003", "E001"]`).

Deterministic: same input always produces same cycle trace (process nodes in sorted ID order).

### Step 1.5: Create composite validation entry point

**Function:** `validate_backlog(items: list[dict]) -> BacklogValidationResult`

Runs all three validators in sequence:
1. `validate_dependencies` — fail fast if errors
2. `validate_hierarchy` — fail fast if errors
3. `detect_dependency_cycles` — fail fast if cycles

```python
@dataclass
class BacklogValidationResult:
    valid: bool
    dependency_errors: list[DependencyError]
    hierarchy_errors: list[HierarchyError]
    cycle_traces: list[CycleTrace]
```

Design note: All three validations run even if earlier ones fail, so the caller gets the complete picture. "Fail fast" means the pipeline halts — not that we skip remaining checks within the validator.

**Verification:**

- `validate_dependencies`: rejects missing refs, self-refs; accepts valid deps, empty deps
- `validate_hierarchy`: rejects STORY→EPIC, FEATURE→null, missing parent, parent cycle; accepts valid tree
- `detect_dependency_cycles`: detects simple cycle, multi-node cycle; accepts large acyclic DAG
- `validate_backlog`: aggregates all errors from all three validators
- All functions are pure — no DB, no LLM, no side effects
- Deterministic: same input always produces same output

---

## Phase 2: Deterministic Ordering Engine

**Objective:** Implement the topological sort, wave grouping, backlog_hash computation, and ExecutionPlan derivation. All mechanical — no LLM.

### Step 2.1: Implement topological sort (Task 6)

**File:** `app/domain/services/backlog_ordering.py`

**Function:** `order_backlog(items: list[dict]) -> list[str]`

Algorithm:
1. Build adjacency graph from `depends_on` edges
2. Topological sort (Kahn's algorithm)
3. Within same topological tier, sort by `priority_score` DESC
4. Tie-break by `id` ASC (lexicographic)

Precondition: caller has already validated no cycles exist. If a cycle is present, raise `ValueError` (programming error, not user error).

Returns: list of item IDs in execution order.

Deterministic: same input always produces same output. Unit tests assert exact output order.

### Step 2.2: Implement wave grouping

**Function:** `compute_waves(items: list[dict]) -> list[list[str]]`

Algorithm (Kahn-style tiers):
1. Wave 0 = all nodes with in-degree 0 (no dependencies)
2. Remove Wave 0 nodes from graph
3. Wave 1 = all nodes with in-degree 0 in remaining graph
4. Repeat until all nodes assigned
5. Within each wave, order by `priority_score` DESC, tie-break by `id` ASC

Returns: list of waves, each wave is a list of item IDs.

Derived from the same dependency graph as `order_backlog`. The flattened wave list must equal `order_backlog` output.

### Step 2.3: Implement backlog_hash computation

**Function:** `compute_backlog_hash(items: list[dict]) -> str`

Algorithm (per implementation plan):
1. Sort items by `id` ASC
2. For each item, extract structure-only tuple: `(id, level, int(priority_score), sorted(depends_on), parent_id)`
3. Serialize as canonical JSON (sorted keys, no whitespace)
4. SHA-256 the serialized string
5. Return hex digest

Included fields: `id`, `level`, `priority_score`, `depends_on`, `parent_id`
Excluded fields: `title`, `description`

### Step 2.4: Implement ExecutionPlan derivation (Task 7)

**Function:** `derive_execution_plan(items: list[dict], intent_id: str, run_id: str) -> dict`

Mechanical function:
1. Call `order_backlog(items)` → `ordered_backlog_ids`
2. Call `compute_waves(items)` → `waves`
3. Call `compute_backlog_hash(items)` → `backlog_hash`
4. Assemble ExecutionPlan document content:

```python
{
    "backlog_hash": backlog_hash,
    "intent_id": intent_id,
    "run_id": run_id,
    "ordered_backlog_ids": ordered_backlog_ids,
    "waves": waves,
    "generator_version": "1.0.0",
}
```

Never LLM-authored. Pure computation.

**Verification:**

- `order_backlog`: deterministic output for fixed input; priority ordering within tier; tie-break by ID
- `compute_waves`: correct tier assignment; flattened waves == ordered output; handles items with no deps
- `compute_backlog_hash`: same structural input → same hash; changing title doesn't change hash; changing priority changes hash
- `derive_execution_plan`: assembles all fields correctly; deterministic end-to-end

---

## Phase 3: ExecutionPlan Schema & Document Type

**Objective:** Define the ExecutionPlan schema and register it as a document type so it can be persisted.

### Step 3.1: Create ExecutionPlan schema

**File:** `combine-config/schemas/execution_plan/releases/1.0.0/schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ExecutionPlan",
  "description": "Deterministically derived execution plan. Never LLM-authored. Single per backlog_hash.",
  "type": "object",
  "required": ["backlog_hash", "ordered_backlog_ids", "waves", "generator_version"],
  "properties": {
    "backlog_hash": {
      "type": "string",
      "pattern": "^[a-f0-9]{64}$",
      "description": "SHA-256 of structural backlog fields. Identity key."
    },
    "intent_id": {
      "type": "string",
      "description": "Reference to the source IntentPacket. Metadata, not identity."
    },
    "run_id": {
      "type": "string",
      "description": "Reference to the workflow run that produced the backlog. Metadata, not identity."
    },
    "ordered_backlog_ids": {
      "type": "array",
      "items": { "type": "string", "pattern": "^[EFS]\\d{3}$" },
      "minItems": 1,
      "description": "Flattened total order. Authoritative."
    },
    "waves": {
      "type": "array",
      "items": {
        "type": "array",
        "items": { "type": "string", "pattern": "^[EFS]\\d{3}$" },
        "minItems": 1
      },
      "minItems": 1,
      "description": "Kahn-style tiers. Derived view, required but non-authoritative."
    },
    "generator_version": {
      "type": "string",
      "description": "Version of the ordering engine that produced this plan."
    }
  },
  "additionalProperties": false
}
```

### Step 3.2: Create ExecutionPlan document type package

**File:** `combine-config/document_types/execution_plan/releases/1.0.0/package.yaml`

```yaml
doc_type_id: execution_plan
display_name: Execution Plan
version: 1.0.0

description: >
  Deterministically derived execution plan for a validated backlog.
  Produced mechanically by topological sort + wave grouping.
  Never LLM-authored. Single per backlog_hash.

authority_level: constructive
creation_mode: constructed
production_mode: construct
scope: project

required_inputs:
  - backlog_item
optional_inputs: []

schema_ref: "schema:execution_plan:1.0.0"

artifacts:
  schema: schemas/output.schema.json

ui:
  icon: route
  category: planning
  display_order: 3
```

**File:** `combine-config/document_types/execution_plan/releases/1.0.0/schemas/output.schema.json`

Copy of `combine-config/schemas/execution_plan/releases/1.0.0/schema.json`.

### Step 3.3: Create ExecutionPlan handler

**File:** `app/domain/handlers/execution_plan_handler.py`

Extends `BaseDocumentHandler`:
- `doc_type_id = "execution_plan"`
- `extract_title()` — returns "Execution Plan"
- `render()` — renders ordered_backlog_ids and waves for display
- `render_summary()` — item count + wave count summary
- No LLM, no children

### Step 3.4: Register handler

**File:** `app/domain/handlers/registry.py`

Add: `"execution_plan": ExecutionPlanHandler()`

### Step 3.5: Create database migration

**File:** `alembic/versions/YYYYMMDD_NNN_add_execution_plan_document_type.py`

```sql
INSERT INTO document_types (doc_type_id, display_name, cardinality, instance_key)
VALUES ('execution_plan', 'Execution Plan', 'single', NULL);
```

### Step 3.6: Update active_releases.json

Add to `document_types`: `"execution_plan": "1.0.0"`
Add to `schemas`: `"execution_plan": "1.0.0"`

**Verification:**

- Schema validates against JSON Schema 2020-12
- Schema rejects: missing `ordered_backlog_ids`, invalid `backlog_hash` format, non-array `waves`
- Document type registered in DB with cardinality `single`
- Handler registered in registry
- `active_releases.json` updated

---

## Phase 4: Unit Tests

**Objective:** Comprehensive tier-1 tests for all domain functions. Pure in-memory, no DB.

### Step 4.1: Graph validator tests

**File:** `tests/tier1/services/test_graph_validator.py`

Dependency validation tests:
- Valid dependencies (all refs exist) → `DependencyResult(valid=True)`
- Missing reference → `MissingReference` error with item_id and missing ID
- Self-reference → `SelfReference` error
- Empty depends_on → valid
- Multiple errors in one backlog → all reported

Hierarchy validation tests:
- Valid tree (EPIC→FEATURE→STORY) → `HierarchyResult(valid=True)`
- STORY with parent_id pointing to EPIC → `InvalidLevelTransition`
- FEATURE with null parent_id → `OrphanedItem`
- parent_id references non-existent item → `ParentNotFound`
- Parent cycle (A→B→A via parent_id) → `ParentCycle`
- FEATURE with parent_id pointing to FEATURE → `HierarchyViolation`
- Deeply nested valid tree → valid

Cycle detection tests:
- Simple cycle (A→B→A via depends_on) → `CycleTrace` returned
- Multi-node cycle (A→B→C→A) → detected
- Large acyclic DAG (10+ nodes) → no cycles
- Multiple independent cycles → all detected
- Self-dependency handled by dependency validator (not cycle detector)

Composite validation tests:
- All valid → `BacklogValidationResult(valid=True)`
- Mix of dependency + hierarchy errors → both reported
- Cycle + hierarchy errors → both reported

### Step 4.2: Ordering engine tests

**File:** `tests/tier1/services/test_backlog_ordering.py`

Topological sort tests:
- Linear chain (A→B→C) → [A, B, C]
- Priority ordering within tier → higher priority first
- Tie-break by ID → lexicographic ASC
- No dependencies → all in one tier, sorted by priority then ID
- Diamond dependency (A→B, A→C, B→D, C→D) → correct order

Wave grouping tests:
- All independent → single wave
- Linear chain → one per wave
- Diamond → correct wave assignment
- Flattened waves == order_backlog output (invariant)

Backlog hash tests:
- Same structural input → same hash
- Changing title → same hash
- Changing description → same hash
- Changing priority_score → different hash
- Changing depends_on → different hash
- Changing parent_id → different hash
- Item order doesn't matter → same hash (sorted by ID)

ExecutionPlan derivation tests:
- End-to-end: items in → plan out with correct fields
- Deterministic: same items → same plan
- backlog_hash matches manual computation

**Verification:**

- All tests are tier-1 (in-memory, no DB, no LLM)
- Each test asserts exact expected output (not "is valid" — exact order, exact errors)
- Tests cover both happy path and error paths
- `python -m pytest tests/tier1/services/test_graph_validator.py tests/tier1/services/test_backlog_ordering.py -v` — all pass

---

## Prohibited Actions

- Do not use an LLM for any ordering, validation, or plan derivation — "LLMs generate. Machines order."
- Do not silently correct invalid dependencies or hierarchy — fail hard, return all errors
- Do not validate dependency existence or hierarchy rules in the QA gate — graph validator owns these
- Do not store waves as authoritative — total order is authoritative, waves are derived view
- Do not allow fractional priority_score in hash computation — `int(priority_score)` always
- Do not create UI for graph validation results — future work
- Do not create auto-regeneration loops (re-prompt on failure) — future work
- Do not make cycle detection non-deterministic — process nodes in sorted ID order
- Do not create the Explanation Generator — that is WS-BCP-003

## Verification Checklist

1. **Dependency validation works:** Rejects missing refs, self-refs; accepts valid deps; returns all errors
2. **Hierarchy validation works:** Enforces EPIC→null, FEATURE→EPIC, STORY→FEATURE; detects orphans, parent cycles, missing parents
3. **Cycle detection works:** Detects simple and multi-node dependency cycles; accepts acyclic graphs; deterministic traces
4. **Composite validator:** Runs all three; aggregates all errors; returns complete picture
5. **Topological sort deterministic:** Same input → same output; priority ordering correct; tie-break correct
6. **Wave grouping correct:** Tiers match Kahn's algorithm; flattened waves == topological order
7. **Backlog hash stable:** Title/description changes don't affect hash; structural changes do; item order irrelevant
8. **ExecutionPlan derivation correct:** Assembles all fields; deterministic end-to-end
9. **ExecutionPlan schema valid:** Validates against JSON Schema 2020-12; rejects invalid hash format, empty arrays
10. **Document type registered:** `execution_plan` in DB with cardinality single; in `active_releases.json`
11. **Handler registered:** `ExecutionPlanHandler` in registry; renders correctly
12. **All tier-1 tests pass:** `python -m pytest tests/tier1/services/test_graph_validator.py tests/tier1/services/test_backlog_ordering.py -v`
13. **Full suite passes:** `python -m pytest tests/ -x -q` — no regressions

## Definition of Done

- `validate_dependencies`, `validate_hierarchy`, `detect_dependency_cycles` exist as pure functions in `app/domain/services/graph_validator.py`
- `order_backlog`, `compute_waves`, `compute_backlog_hash`, `derive_execution_plan` exist as pure functions in `app/domain/services/backlog_ordering.py`
- All functions are deterministic — same input always produces same output
- Two separate error buckets: dependency errors and hierarchy errors (per DQ-2)
- ExecutionPlan schema, document type, and handler registered
- Comprehensive tier-1 tests with exact expected outputs
- All existing tests continue to pass
- No LLM involved in any function — pure mechanical compilation
