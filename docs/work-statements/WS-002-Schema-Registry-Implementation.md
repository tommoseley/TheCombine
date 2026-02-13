# WS-002: Schema Registry Implementation

| | |
|---|---|
| **Status** | Complete |
| **Created** | 2026-01-06 |
| **Executor** | AI Agent (Claude) |
| **Approver** | Product Owner |

---

## Purpose

Implement the DB-backed Schema Registry and Resolver per ADR-031 (Canonical Schema Types and DB-Backed Schema Registry).

This Work Statement:
- Creates the schema artifact storage infrastructure
- Implements the schema resolver that produces self-contained bundles
- Seeds the first canonical type (`OpenQuestionV1`)
- Extends LLM execution logging to capture schema identity
- Integrates resolved bundles with DocumentBuilder

---

## Governing References

| Reference | Purpose |
|-----------|---------|
| ADR-031 | Defines schema registry requirements and acceptance criteria |
| ADR-010 | LLM execution logging requirements (extended by this work) |
| POL-WS-001 | Governs Work Statement structure and execution |
| ADR-031 Implementation Plan | Provides phase structure and file inventory |

---

## Scope

### Included

- Create `schema_artifact` database table with migration
- Create `SchemaArtifact` ORM model
- Create `SchemaRegistryService` with CRUD and status lifecycle
- Create `SchemaResolver` with bundle resolution and cycle detection
- Seed `OpenQuestionV1` canonical type
- Extend `llm_execution_logs` table with schema tracking columns
- Extend `LLMExecutionLogger` to record schema identity
- Integrate `SchemaResolver` with `DocumentBuilder`
- Create tests for all new components (~30 tests)

### Excluded

- Fragment registry and UI composition (ADR-032)
- Migration of existing inline schemas to registry
- Schema authoring UI
- Additional canonical types beyond `OpenQuestionV1`

---

## Preconditions

Before execution:

- [ ] ADR-031 is committed and approved
- [ ] ADR-031 Implementation Plan is committed
- [ ] All existing tests pass (999)
- [ ] Database is accessible for migration

---

## Procedure

Execute steps in order. Do not skip, reorder, or merge steps.

### Step 1: Create Database Migration for schema_artifact

**Action:** Create `alembic/versions/20260106_001_add_schema_artifact.py`

**Table columns:**
- `id` (UUID, PK)
- `schema_id` (VARCHAR(100), NOT NULL)
- `version` (VARCHAR(20), NOT NULL, default '1.0')
- `kind` (VARCHAR(20), NOT NULL) — 'type', 'document', 'envelope'
- `status` (VARCHAR(20), NOT NULL) — 'draft', 'accepted', 'deprecated'
- `schema_json` (JSONB, NOT NULL)
- `sha256` (VARCHAR(64), NOT NULL)
- `governance_refs` (JSONB)
- `created_at` (TIMESTAMP, NOT NULL)
- `created_by` (VARCHAR(100))
- `updated_at` (TIMESTAMP)

**Indexes:**
- UNIQUE on (schema_id, version)
- Index on (status)
- Index on (kind)

**Verification:** Migration applies without error.

---

### Step 2: Create SchemaArtifact ORM Model

**Action:** Create `app/api/models/schema_artifact.py`

**Requirements:**
- SQLAlchemy model matching migration schema
- Proper type hints
- Table name: `schema_artifacts`

**Action:** Update `app/api/models/__init__.py` to export `SchemaArtifact`

**Verification:** Model imports successfully.

---

### Step 3: Create Schema Registry Service

**Action:** Create `app/api/services/schema_registry_service.py`

**Methods required:**
- `async create(schema_id, version, kind, schema_json, governance_refs) -> SchemaArtifact`
- `async get_by_id(schema_id, version=None) -> SchemaArtifact | None`
- `async get_accepted(schema_id) -> SchemaArtifact | None`
- `async set_status(schema_id, version, status) -> SchemaArtifact`
- `async list_by_kind(kind, status=None) -> List[SchemaArtifact]`
- `compute_hash(schema_json) -> str` (deterministic JSON + SHA256)

**Rules:**
- Hash computed on create/update
- Status transitions: draft → accepted, accepted → deprecated
- `get_by_id` without version returns latest accepted

**Action:** Update `app/api/services/__init__.py` to export

**Verification:** Service instantiates, methods callable.

---

### Step 4: Create Schema Resolver Service

**Action:** Create `app/domain/services/schema_resolver.py`

**Data classes:**
- `SchemaDependency(schema_id, version, sha256)`
- `ResolvedSchemaBundle(root_schema_id, root_schema_version, bundle_json, bundle_sha256, dependencies)`

**Class: SchemaResolver**

**Methods:**
- `async resolve_bundle(root_schema_id, version=None) -> ResolvedSchemaBundle`
- `_find_schema_refs(schema) -> List[str]` — find all `$ref: "schema:..."`
- `_detect_cycle(schema_id, visited) -> bool`
- `_inline_to_defs(root, resolved) -> dict` — build `$defs`, rewrite refs

**Resolution algorithm:**
1. Load root schema from registry (accepted only)
2. Walk schema, find all `$ref: "schema:<id>"` references
3. For each ref, recursively resolve (track visited for cycle detection)
4. If cycle detected, raise `CircularSchemaReferenceError`
5. Build `$defs` section with all resolved schemas
6. Rewrite `$ref` from `"schema:<id>"` to `"#/$defs/<id>"`
7. Compute bundle hash
8. Return `ResolvedSchemaBundle`

**Verification:** Resolver instantiates, can resolve a simple schema.

---

### Step 5: Seed OpenQuestionV1 Canonical Type

**Action:** Create `app/domain/registry/seed_schema_artifacts.py`

**OpenQuestionV1 schema:** (as defined in implementation plan)

**Seed function:**
```python
async def seed_schema_artifacts(db: AsyncSession) -> int:
    # Create OpenQuestionV1 with status="accepted"
```

**Verification:** Seed runs, `OpenQuestionV1` exists with status=accepted.

---

### Step 6: Extend LLM Execution Log Schema

**Action:** Create `alembic/versions/20260106_002_add_schema_to_llm_log.py`

**Add columns to `llm_execution_logs`:**
- `schema_id` (VARCHAR(100), nullable)
- `schema_bundle_hash` (VARCHAR(64), nullable)

**Action:** Update `app/api/models/llm_execution_log.py` with new columns

**Verification:** Migration applies, columns exist.

---

### Step 7: Extend LLM Execution Logger

**Action:** Modify `app/domain/services/llm_execution_logger.py`

**Changes:**
- Add `schema_id` and `schema_bundle_hash` parameters to logging methods
- Store in log record

**Verification:** Logger accepts and stores schema fields.

---

### Step 8: Integrate with DocumentBuilder

**Action:** Modify `app/domain/services/document_builder.py`

**Changes:**
1. Inject `SchemaResolver` dependency
2. Before LLM call, check if document type has `schema_id`
3. If yes, resolve bundle via `SchemaResolver.resolve_bundle()`
4. Include `bundle_json` in LLM context/prompt
5. Pass `root_schema_id` and `bundle_sha256` to logger

**Note:** This is incremental. Document types without `schema_id` continue to work as before.

**Verification:** DocumentBuilder accepts resolver, uses it when schema_id present.

---

### Step 9: Create Registry Service Tests

**Action:** Create `tests/api/test_schema_registry_service.py`

**Required tests:**
1. `test_create_schema_artifact` — happy path
2. `test_create_computes_hash` — hash is computed
3. `test_get_by_id_with_version` — exact version lookup
4. `test_get_by_id_latest_accepted` — no version returns accepted
5. `test_get_accepted` — returns only accepted status
6. `test_set_status_draft_to_accepted` — valid transition
7. `test_set_status_accepted_to_deprecated` — valid transition
8. `test_list_by_kind` — filters correctly
9. `test_hash_determinism` — same JSON = same hash

**Verification:** All tests pass.

---

### Step 10: Create Resolver Tests

**Action:** Create `tests/domain/test_schema_resolver.py`

**Required tests:**
1. `test_resolve_simple_schema` — no refs
2. `test_resolve_with_single_ref` — one `$ref: "schema:..."` resolved
3. `test_resolve_with_nested_refs` — refs within refs
4. `test_resolve_rewrites_refs` — `$ref` becomes `#/$defs/<id>`
5. `test_resolve_builds_defs` — `$defs` section populated
6. `test_resolve_computes_bundle_hash` — hash present
7. `test_resolve_tracks_dependencies` — dependency list correct
8. `test_resolve_rejects_circular_ref` — direct cycle
9. `test_resolve_rejects_indirect_circular_ref` — A→B→C→A
10. `test_resolve_only_accepted` — draft schemas rejected

**Verification:** All tests pass.

---

### Step 11: Create Seed Tests

**Action:** Create `tests/domain/test_seed_schema_artifacts.py`

**Required tests:**
1. `test_seed_creates_open_question_v1` — artifact created
2. `test_seed_open_question_v1_accepted` — status is accepted
3. `test_seed_open_question_v1_valid_schema` — JSON Schema is valid
4. `test_seed_idempotent` — running twice doesn't duplicate

**Verification:** All tests pass.

---

### Step 12: Integration Verification

**Action:** Manually verify end-to-end:

1. Run migrations
2. Run seed
3. Verify `OpenQuestionV1` in database
4. Call resolver for a test schema referencing `OpenQuestionV1`
5. Verify bundle is self-contained

**Verification:** Bundle contains `$defs` with `OpenQuestionV1`, no unresolved refs.

---

### Step 13: Run Full Test Suite

**Action:** Execute `python -m pytest tests/ -v`

**Verification:** All tests pass (999 existing + ~30 new).

---

## Prohibited Actions

1. **Do not modify existing document generation behavior** — Schema integration is additive
2. **Do not create additional canonical types** — Only `OpenQuestionV1` in this WS
3. **Do not implement fragment rendering** — Out of scope (ADR-032)
4. **Do not migrate existing inline schemas** — Separate Work Statement
5. **Do not add filesystem-based schema loading** — DB only per ADR-031
6. **Do not allow unresolved `$ref` in bundles** — Hard requirement
7. **Do not skip cycle detection** — Must be implemented
8. **Do not infer missing steps** — If unclear, STOP and escalate

---

## Verification Checklist

- [ ] `schema_artifacts` table exists with all columns and indexes
- [ ] `SchemaArtifact` ORM model works
- [ ] `SchemaRegistryService` CRUD operations work
- [ ] Status lifecycle enforced (draft → accepted → deprecated)
- [ ] SHA256 computed deterministically
- [ ] `SchemaResolver` resolves `$ref: "schema:<id>"` correctly
- [ ] Circular references detected and rejected
- [ ] Bundle includes `$defs` with resolved schemas
- [ ] Bundle `$ref` rewritten to `#/$defs/<id>`
- [ ] `OpenQuestionV1` seeded and accepted
- [ ] `llm_execution_logs` has schema columns
- [ ] `LLMExecutionLogger` records schema identity
- [ ] `DocumentBuilder` uses resolver when schema_id present
- [ ] All new tests pass (~30)
- [ ] All existing tests pass (999)

---

## Definition of Done

This Work Statement is complete when:

1. All procedure steps (1-13) have been executed in order
2. All verification checklist items are checked
3. No prohibited actions were taken
4. ADR-031 acceptance criteria are met
5. ~30 new tests passing, 999 existing tests still passing

---

## Closure

| Field | Value |
|-------|-------|
| Completed | 2026-01-06 |
| Verified By | Product Owner |
| Deviations | None |
| Notes | 38 new tests, 1034 total passing. 4 canonical types seeded. |

---

*End of Work Statement*