# WS-ADR-034-POC: Canonical Component & Document Composition Proof of Concept

| | |
|---|---|
| **Work Statement** | WS-ADR-034-POC |
| **Version** | 1.2 |
| **Title** | Canonical Component & Document Composition Proof of Concept |
| **ADR** | ADR-034 (as amended by ADR-034-A) |
| **Status** | Complete |
| **Expected Scope** | Multi-commit (phased) |
| **Created** | 2026-01-07 |

---

## Purpose

Implement the minimum infrastructure required to satisfy ADR-034 acceptance criteria using a single concrete document (EpicBacklog) and a single canonical component (OpenQuestion).

This Work Statement proves that:
- Documents can be defined as compositions of canonical components
- LLM prompts are assembled mechanically from component guidance
- RenderModels are constructed from document definitions
- Fragment rendering works unchanged
- An administrator can preview prompt and render output

This WS closes ADR-034.

---

## Governing References

| Reference | Purpose |
|-----------|---------|
| ADR-034 | Document Composition Manifest & Canonical Components |
| ADR-034-A | Amendment: Section completeness, ID conventions, context propagation |
| ADR-031 | Schema registry (dependency) |
| ADR-032 | Fragment registry (dependency) |
| ADR-033 | Data-only experience contracts |
| POL-WS-001 | Work Statement standard |
| POL-ADR-EXEC-001 | Execution authorization |

---

## Scope

### Included

**Database Layer:**
- Create `component_artifacts` table
- Create `document_definitions` table
- Create migrations for both tables

**Schema Layer:**
- Define and seed `schema:CanonicalComponentV1` schema
- Define and seed `schema:DocumentDefinitionV2` schema

**Service Layer:**
- `ComponentRegistryService` (read + resolve + list + create + accept)
- `DocumentDefinitionService` (read + resolve + list + create + accept)
- `PromptAssembler` (mechanical prompt construction)
- `RenderModelBuilder` (docdef sections to RenderBlocks)
- `FragmentRegistryService` extension: alias resolver for canonical fragment IDs

**Seed Data:**
- Migrate `OpenQuestionV1` into a canonical component spec
- Create `EpicBacklog` document definition composing OpenQuestion

**Preview Capabilities (Minimum Viable Composer Backend):**
- Preview compiled prompt for a document definition
- Preview RenderModel structure for sample data (data-only, no HTML)
- Verify existing fragment rendering works unchanged

**Tests:**
- Unit tests for all new services
- Integration test: docdef to prompt assembly to verify bullets present
- Integration test: docdef to RenderModel to verify block structure

### Excluded

- Composer UI (future WS)
- Multiple document types beyond EpicBacklog
- Additional components beyond OpenQuestion
- General update/delete for registry services (only `accept()` permitted)
- Workflow/action bindings (ADR-035)
- Fragment ID migration in DB (alias resolver only)
- Document state machines (ADR-036)

---

## Preconditions

- [ ] ADR-034 accepted
- [ ] ADR-034-A accepted
- [x] ADR-031 complete (schema registry exists)
- [x] ADR-032 complete (fragment registry exists)
- [x] ADR-033 partial (WS-004 complete, RenderModel concept established)
- [ ] All existing tests pass (1071)

---

## Key Design Decisions

### D1: Registry Services Are Read-First + Accept Only

Services implement: `get`, `list`, `create`, `accept`

General update and delete are deferred. The only mutation permitted is `accept()` which transitions `status: draft -> accepted` and sets `accepted_at` timestamp.

### D2: PromptAssembler Runs Server-Side

PromptAssembler executes in the orchestrator/LLM request construction path:
- Reads docdef + component specs from DB
- Outputs: resolved schema bundle (from component schemas), compiled prompt bullets, document-level header
- Logs: `docdef_id`, `component_ids`, `bundle_sha256` (ADR-010 alignment)

No filesystem access. APIs return data only.

**Note:** The schema bundle is assembled from component schemas, not from document_schema_id (which may be null in MVP). This allows prompt assembly to work without a full document schema.

### D3: ComponentSpec Owns Fragment Bindings (Canonical IDs + Alias Resolution)

`component_spec.view_bindings` stores canonical fragment IDs per ADR-034-A.3 format:
`fragment:<SchemaType>:<channel>:<semver>`

Example: `fragment:OpenQuestionV1:web:1.0.0`

**Alias Resolution:** FragmentRegistryService resolves canonical IDs to existing legacy fragment records via a mapping function (no DB migration required). This satisfies ADR-034-A without migrating existing fragment_artifacts rows.

**POC Constraint:** `FRAGMENT_ALIASES` constant is acceptable only for seeded POC mappings. Future: move aliases into a DB table or fragment_bindings table.

Document definitions do NOT override fragment bindings.

### D4: DocDef Sections Produce RenderBlocks Directly

Single rule: Each section in a document definition produces 0..n `RenderBlock`s.

**RenderBlock.type** equals the canonical schema ID string directly (e.g., `schema:OpenQuestionV1`). No double-prefixing.

This is the glue between ADR-034 (composition) and ADR-033 (render model).

### D5: Single-Field ID Convention (No Separate Version Column)

Per ADR-034-A, identifiers embed semver:
- `component_id = component:OpenQuestionV1:1.0.0` (unique, no separate version column)
- `document_def_id = docdef:EpicBacklog:1.0.0` (unique, no separate version column)

This avoids double-versioning and aligns with amendment conventions.

### D6: RenderModelBuilder Is Channel-Neutral

RenderModelBuilder lives in `app/domain/services/` (not web/bff) because it produces data structures, not channel-specific output. Channel-specific rendering happens downstream.

### D7: get_accepted() Uses accepted_at DESC

When resolving "latest accepted" for a prefix match:
- Filter by status = 'accepted'
- Order by `accepted_at DESC`
- Return first result

Semver parsing from ID is not required for MVP. Acceptance timestamp is the deterministic ordering.

### D8: Migration Sequencing

Incremental, not big-bang:
1. Add tables + schemas (no behavior change)
2. Insert OpenQuestion component spec + EpicBacklog docdef
3. Wire PromptAssembler for EpicBacklog only
4. Wire RenderModelBuilder for EpicBacklog only
5. Verify existing fragment rendering unchanged

---

## Procedure

Execute phases in order. Do not skip, reorder, or merge phases.

---

### PHASE 1: Database Tables

---

#### Step 1.1: Create component_artifacts Migration

**Action:** Create `alembic/versions/20260107_001_add_component_artifacts.py`

**Table: component_artifacts**

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| component_id | VARCHAR(150) | NOT NULL, UNIQUE |
| schema_artifact_id | UUID | NOT NULL, FK to schema_artifacts.id |
| schema_id | VARCHAR(100) | NOT NULL (denormalized for convenience) |
| generation_guidance | JSONB | NOT NULL |
| view_bindings | JSONB | NOT NULL |
| status | VARCHAR(20) | NOT NULL, default 'draft' |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL, default now() |
| created_by | VARCHAR(100) | |
| accepted_at | TIMESTAMP WITH TIME ZONE | |

**Indexes:**
- UNIQUE on (component_id)
- Index on (schema_artifact_id)
- Index on (status)
- Index on (accepted_at) for get_accepted queries

**Notes:**
- `component_id` embeds semver per D5 (e.g., `component:OpenQuestionV1:1.0.0`)
- `schema_artifact_id` is the UUID FK; `schema_id` is denormalized string for queries
- All timestamps are UTC

**Verification:** Migration applies without error.

---

#### Step 1.2: Create document_definitions Migration

**Action:** Create `alembic/versions/20260107_002_add_document_definitions.py`

**Table: document_definitions**

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| document_def_id | VARCHAR(150) | NOT NULL, UNIQUE |
| document_schema_id | UUID | FK to schema_artifacts.id (nullable) |
| prompt_header | JSONB | NOT NULL |
| sections | JSONB | NOT NULL |
| status | VARCHAR(20) | NOT NULL, default 'draft' |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL, default now() |
| created_by | VARCHAR(100) | |
| accepted_at | TIMESTAMP WITH TIME ZONE | |

**Indexes:**
- UNIQUE on (document_def_id)
- Index on (status)
- Index on (accepted_at) for get_accepted queries

**Notes:**
- `document_def_id` embeds semver per D5 (e.g., `docdef:EpicBacklog:1.0.0`)
- `document_schema_id` is nullable for MVP; schema bundle comes from component schemas
- `sections` JSONB permits empty arrays
- All timestamps are UTC

**Verification:** Migration applies without error.

---

#### Step 1.3: Create ORM Models

**Action:** Create `app/api/models/component_artifact.py`

**Action:** Create `app/api/models/document_definition.py`

**Action:** Update `app/api/models/__init__.py` to export both models.

**Verification:** Models import successfully.

---

### PHASE 2: Canonical Schemas

---

#### Step 2.1: Define schema:CanonicalComponentV1

**Action:** Add to seed_schema_artifacts.py

**Schema ID:** `schema:CanonicalComponentV1`

Schema must validate:
- `component_id` matches pattern `^component:[A-Za-z0-9._-]+:[0-9]+\.[0-9]+\.[0-9]+$`
- `schema_id` matches pattern `^schema:[A-Za-z0-9._-]+$`
- `generation_guidance.bullets` is string array (minItems: 1)
- `view_bindings` structure for channel mappings

**Verification:** Schema seeds successfully with id `schema:CanonicalComponentV1`, passes self-validation.

---

#### Step 2.2: Define schema:DocumentDefinitionV2

**Action:** Add to seed_schema_artifacts.py

**Schema ID:** `schema:DocumentDefinitionV2`

Schema must validate:
- `document_def_id` matches pattern `^docdef:[A-Za-z0-9._-]+:[0-9]+\.[0-9]+\.[0-9]+$`
- `prompt_header` with role and constraints
- `sections` array (minItems: 0 permitted) with required fields per ADR-034-A.1

**Verification:** Schema seeds successfully with id `schema:DocumentDefinitionV2`.

---

### PHASE 3: Registry Services

---

#### Step 3.1: Create ComponentRegistryService

**Action:** Create `app/api/services/component_registry_service.py`

**Methods:**
- `async get(component_id: str) -> ComponentArtifact | None` (exact match)
- `async get_accepted(component_id_prefix: str) -> ComponentArtifact | None` (latest accepted matching prefix, ordered by accepted_at DESC)
- `async list_by_schema(schema_id: str) -> List[ComponentArtifact]`
- `async create(component_id, schema_artifact_id, schema_id, generation_guidance, view_bindings, ...) -> ComponentArtifact`
- `async accept(component_id: str) -> ComponentArtifact` (sets status=accepted, accepted_at=now)

**Rules:**
- `get` returns exact match only
- `get_accepted` filters status='accepted', orders by accepted_at DESC, returns first
- `create` validates component_id format matches convention
- `accept` is the only mutation permitted; raises if already accepted
- Status lifecycle: draft to accepted only

**Verification:** Service instantiates, methods callable.

---

#### Step 3.2: Create DocumentDefinitionService

**Action:** Create `app/api/services/document_definition_service.py`

**Methods:**
- `async get(document_def_id: str) -> DocumentDefinition | None` (exact match)
- `async get_accepted(document_def_id_prefix: str) -> DocumentDefinition | None` (latest accepted, ordered by accepted_at DESC)
- `async list_all(status: str = None) -> List[DocumentDefinition]`
- `async create(document_def_id, prompt_header, sections, document_schema_id=None, ...) -> DocumentDefinition`
- `async accept(document_def_id: str) -> DocumentDefinition`

**Rules:**
- `document_schema_id` may be None for MVP
- `get_accepted` filters status='accepted', orders by accepted_at DESC
- `create` validates document_def_id format
- `accept` is the only mutation permitted
- Status lifecycle: draft to accepted only

**Verification:** Service instantiates, methods callable.

---

#### Step 3.3: Extend FragmentRegistryService with Alias Resolver

**Action:** Modify `app/api/services/fragment_registry_service.py`

**Add method:**
- `async resolve_fragment_id(canonical_id: str) -> FragmentArtifact | None`

**Alias mapping (temporary, code-based):**

`python
# POC only - future: move to DB table or fragment_bindings
FRAGMENT_ALIASES = {
    "fragment:OpenQuestionV1:web:1.0.0": "OpenQuestionV1Fragment",
}
`

**Algorithm:**
1. If canonical_id is in FRAGMENT_ALIASES, look up by legacy id
2. Otherwise, look up by canonical_id directly
3. Return FragmentArtifact or None

This allows component specs to store canonical IDs while existing fragment_artifacts rows remain unchanged.

**Verification:** Resolver returns correct fragment for both formats.

---

### PHASE 4: PromptAssembler

---

#### Step 4.1: Create PromptAssembler Service

**Action:** Create `app/domain/services/prompt_assembler.py`

**Data classes:**

`python
@dataclass
class AssembledPrompt:
    document_def_id: str
    header: dict  # role, constraints
    component_bullets: List[str]  # concatenated from all components
    component_ids: List[str]  # for logging/audit
    schema_bundle: dict  # resolved schema bundle (always included)
    bundle_sha256: str
`

**Class: PromptAssembler**

**Constructor dependencies:**
- `DocumentDefinitionService`
- `ComponentRegistryService`
- `SchemaResolver`

**Methods:**
- `async assemble(document_def_id: str) -> AssembledPrompt`
- `format_prompt_text(assembled: AssembledPrompt) -> str`

**Assembly algorithm:**
1. Load document definition by exact id
2. Collect unique component_ids from sections (preserve section order)
3. Resolve each component spec
4. Concatenate generation_guidance.bullets:
   - Preserve section order
   - Preserve bullet order within each component
   - Dedupe exact duplicates only, keeping first occurrence
5. Resolve schema bundle from component schemas via SchemaResolver (always included)
6. Compute bundle_sha256
7. Return AssembledPrompt

**Note:** Schema bundle is built from component schemas, not from document_schema_id. This allows prompt assembly without a full document schema.

**Logging:** On assembly, log `document_def_id`, `component_ids`, `bundle_sha256` per ADR-010 alignment.

**Verification:** Assembler produces expected prompt structure with schema bundle.

---

### PHASE 5: RenderModelBuilder

---

#### Step 5.1: Create RenderModelBuilder Service

**Action:** Create `app/domain/services/render_model_builder.py`

**Data classes:**

`python
@dataclass
class RenderBlock:
    type: str      # canonical schema id, e.g., "schema:OpenQuestionV1"
    key: str       # unique key within document
    data: dict     # validated block data
    context: Optional[dict] = None  # parent-supplied metadata

@dataclass
class RenderModel:
    document_def_id: str
    blocks: List[RenderBlock]
    metadata: dict  # document-level metadata
`

**Class: RenderModelBuilder**

**Constructor dependencies:**
- `DocumentDefinitionService`
- `ComponentRegistryService`

**Methods:**
- `async build(document_def_id: str, document_data: dict) -> RenderModel`

**Build algorithm:**
1. Load document definition by exact id
2. For each section (ordered by `order` field):
   - Resolve component spec to get schema_id
   - Based on shape:
     - `single`: Resolve source_pointer from root, create one RenderBlock
     - `list`: Resolve source_pointer from root, iterate array, create RenderBlock per item
     - `nested_list`: Iterate repeat_over array; for each parent object, resolve source_pointer **relative to that parent**, create RenderBlock per item
   - Set `RenderBlock.type` = component's schema_id (e.g., `schema:OpenQuestionV1`)
   - Set `RenderBlock.key` = `{section_id}:{index}` or item id if available
   - Attach context by resolving context pointers **relative to the parent object**
3. Return RenderModel with all blocks

**Rules:**
- Each section produces 0..n RenderBlocks
- `RenderBlock.type` equals the component's `schema_id` directly (no prefixing)
- For `nested_list`: `source_pointer` and `context` pointers are evaluated relative to each repeated parent object, not from document root
- Context propagation per ADR-034-A.4
- Returns data only; no HTML rendering

**Verification:** Builder produces expected block structure.

---

### PHASE 6: Seed Data

---

#### Step 6.1: Create OpenQuestionV1 Component Spec

**Action:** Create `app/domain/registry/seed_component_artifacts.py`

**OpenQuestionV1 Component:**

`python
OPEN_QUESTION_V1_COMPONENT = {
    "component_id": "component:OpenQuestionV1:1.0.0",
    "schema_id": "schema:OpenQuestionV1",
    "generation_guidance": {
        "bullets": [
            "Provide a stable question id (e.g., Q-001).",
            "Write a clear, specific question that requires human decision.",
            "Set blocking=true only if work cannot proceed responsibly without an answer.",
            "Explain why_it_matters in one sentence.",
            "Include options only if there are meaningful discrete choices.",
            "If options exist, default_response SHOULD match one option.",
            "Use notes for assumptions, context, or follow-up suggestions."
        ]
    },
    "view_bindings": {
        "web": {
            "fragment_id": "fragment:OpenQuestionV1:web:1.0.0"
        }
    },
    "status": "accepted"
}
`

**Note:** `fragment_id` uses canonical format; FragmentRegistryService alias resolver maps to existing `OpenQuestionV1Fragment` record.

**Verification:** Component seeded, can be retrieved, fragment resolves correctly.

---

#### Step 6.2: Create EpicBacklog Document Definition

**Action:** Add EpicBacklog docdef to seed_component_artifacts.py (or separate seed file)

**EpicBacklog DocDef:**

`python
EPIC_BACKLOG_DOCDEF = {
    "document_def_id": "docdef:EpicBacklog:1.0.0",
    "document_schema_id": None,  # nullable for MVP; schema bundle from components
    "prompt_header": {
        "role": "You are a Business Analyst creating an Epic Backlog for a software project.",
        "constraints": [
            "Output valid JSON matching the document schema.",
            "Be specific and actionable.",
            "Do not invent requirements not supported by inputs.",
            "Each epic must have at least one open question if unknowns exist."
        ]
    },
    "sections": [
        {
            "section_id": "epic_open_questions",
            "title": "Open Questions",
            "description": "Questions requiring human decision before implementation",
            "order": 10,
            "component_id": "component:OpenQuestionV1:1.0.0",
            "shape": "nested_list",
            "source_pointer": "/open_questions",
            "repeat_over": "/epics",
            "context": {
                "epic_id": "/id",
                "epic_title": "/title"
            }
        }
    ],
    "status": "accepted"
}
`

**Note:** For `nested_list`, `source_pointer` (`/open_questions`) and `context` pointers (`/id`, `/title`) are evaluated relative to each epic in `/epics`, not from document root.

**Verification:** DocDef seeded, can be retrieved.

---

### PHASE 7: Preview Capabilities

---

#### Step 7.1: Create Preview Endpoints (Admin API)

**Action:** Create `app/api/routes/composer_routes.py`

**Endpoints:**

`GET /api/admin/composer/preview/prompt/{document_def_id}`
- Returns: AssembledPrompt as JSON
- Fields: document_def_id, header, component_bullets, component_ids, schema_bundle, bundle_sha256

`POST /api/admin/composer/preview/render/{document_def_id}`
- Body: `{ "document_data": { ... } }`
- Returns: RenderModel as JSON
- Fields: document_def_id, blocks (array of RenderBlock), metadata

**Rules:**
- Both endpoints return data-only (no HTML anywhere)
- Authentication: admin required

**Verification:** Endpoints return expected preview data as JSON.

---

#### Step 7.2: Integration Verification

**Action:** Manual verification of EpicBacklog flow

**Checks:**
- [ ] Call prompt preview for `docdef:EpicBacklog:1.0.0` - verify OpenQuestion bullets present
- [ ] Call render preview with sample epic data - verify RenderBlocks with `type: schema:OpenQuestionV1`
- [ ] Verify nested_list: blocks have correct context from parent epic
- [ ] Verify fragment alias resolution works (canonical ID maps to legacy fragment)
- [ ] Load actual Epic Backlog in UI - verify fragment rendering unchanged
- [ ] Verify no regression in existing Epic Backlog functionality

**Verification:** End-to-end flow works.

---

### PHASE 8: Tests

---

#### Step 8.1: Service Unit Tests

**Action:** Create `tests/api/test_component_registry_service.py` (~7 tests)

Required tests:
1. `test_create_component_artifact`
2. `test_get_component_by_exact_id`
3. `test_get_accepted_returns_latest_by_accepted_at`
4. `test_list_by_schema`
5. `test_accept_transitions_status`
6. `test_accept_sets_accepted_at`
7. `test_component_id_format_validation`

**Action:** Create `tests/api/test_document_definition_service.py` (~6 tests)

Required tests:
1. `test_create_document_definition`
2. `test_create_with_null_document_schema_id`
3. `test_get_docdef_by_exact_id`
4. `test_get_accepted_returns_latest_by_accepted_at`
5. `test_accept_transitions_status`
6. `test_list_all_docdefs`

**Action:** Create `tests/api/test_fragment_alias_resolver.py` (~3 tests)

Required tests:
1. `test_resolve_canonical_id_via_alias`
2. `test_resolve_legacy_id_directly`
3. `test_resolve_unknown_returns_none`

**Verification:** All service tests pass.

---

#### Step 8.2: PromptAssembler Tests

**Action:** Create `tests/domain/test_prompt_assembler.py` (~7 tests)

Required tests:
1. `test_assemble_loads_docdef`
2. `test_assemble_resolves_components`
3. `test_assemble_preserves_section_order`
4. `test_assemble_preserves_bullet_order`
5. `test_assemble_dedupes_exact_duplicates_keeps_first`
6. `test_assemble_includes_schema_bundle_from_components`
7. `test_format_prompt_text`

**Verification:** All assembler tests pass.

---

#### Step 8.3: RenderModelBuilder Tests

**Action:** Create `tests/domain/test_render_model_builder.py` (~8 tests)

Required tests:
1. `test_build_single_shape`
2. `test_build_list_shape`
3. `test_build_nested_list_shape`
4. `test_build_nested_list_resolves_pointer_relative_to_parent`
5. `test_build_propagates_context_from_parent`
6. `test_build_block_type_equals_schema_id`
7. `test_build_empty_data_produces_no_blocks`
8. `test_build_returns_data_only`

**Verification:** All builder tests pass.

---

#### Step 8.4: Integration Tests

**Action:** Create `tests/integration/test_adr034_proof.py` (~4 tests)

Required tests:
1. `test_epic_backlog_prompt_assembly_includes_open_question_bullets`
2. `test_epic_backlog_render_model_produces_question_blocks_with_context`
3. `test_fragment_alias_resolution_in_view_bindings`
4. `test_existing_fragment_rendering_unchanged`

**Verification:** All integration tests pass.

---

### PHASE 9: Final Verification

---

#### Step 9.1: Run Full Test Suite

**Action:** Execute `python -m pytest tests/ -v`

**Verification:** All tests pass (1071 existing + ~35 new).

---

#### Step 9.2: Acceptance Criteria Verification

Per ADR-034 Section 11:

- [ ] At least one canonical component (OpenQuestion) exists with schema, prompt guidance, and fragment binding
- [ ] A document type (EpicBacklog) composes components without duplicating prompt text
- [ ] LLM prompts are assembled mechanically from component guidance
- [ ] Web rendering uses fragment bindings without API HTML leakage
- [ ] An administrator can preview prompt and render output (data-only)

**Verification:** All acceptance criteria satisfied.

---

## Prohibited Actions

1. **Do not implement Composer UI** - Out of scope (future WS)
2. **Do not add general update/delete to registry services** - Only `accept()` permitted
3. **Do not migrate fragment_artifacts rows** - Use alias resolver only
4. **Do not add multiple document types** - POC uses EpicBacklog only
5. **Do not add workflow/action bindings** - ADR-035
6. **Do not modify existing fragment rendering logic** - Must remain unchanged
7. **Do not embed component-specific prompts in document definitions** - Violates ADR-034
8. **Do not skip migration sequencing** - Follow phased approach
9. **Do not return HTML from preview endpoints** - Data-only contracts
10. **Do not double-prefix RenderBlock.type** - Use schema_id directly
11. **Do not resolve source_pointer from root for nested_list** - Resolve relative to parent
12. **Do not infer missing steps** - If unclear, STOP and escalate

---

## Verification Checklist

**Database:**
- [ ] `component_artifacts` table exists with all columns and indexes
- [ ] `document_definitions` table exists with all columns and indexes
- [ ] ORM models import and work correctly
- [ ] All timestamps use UTC
- [ ] `accepted_at` indexed for get_accepted queries

**Schemas:**
- [ ] `schema:CanonicalComponentV1` schema seeded and accepted
- [ ] `schema:DocumentDefinitionV2` schema seeded and accepted
- [ ] ID patterns allow underscores, dots, hyphens

**Services:**
- [ ] `ComponentRegistryService` read + create + accept operations work
- [ ] `DocumentDefinitionService` read + create + accept operations work
- [ ] `get_accepted` orders by accepted_at DESC
- [ ] `FragmentRegistryService` alias resolver works
- [ ] `PromptAssembler` produces expected prompt structure with schema bundle from components
- [ ] `RenderModelBuilder` produces expected block structure (data-only)
- [ ] `RenderModelBuilder` resolves nested_list pointers relative to parent

**Seed Data:**
- [ ] `OpenQuestionV1` component spec seeded and accepted
- [ ] `EpicBacklog` document definition seeded and accepted
- [ ] `document_schema_id` is null (acceptable for MVP)
- [ ] Fragment alias resolution maps canonical to legacy ID

**Preview:**
- [ ] Prompt preview endpoint returns AssembledPrompt JSON
- [ ] Render preview endpoint returns RenderModel JSON (no HTML)
- [ ] Existing Epic Backlog UI rendering unchanged

**Tests:**
- [ ] All new tests pass (~35)
- [ ] All existing tests pass (1071)

---

## Definition of Done

This Work Statement is complete when:

1. All procedure steps (Phases 1-9) have been executed in order
2. All verification checklist items are checked
3. No prohibited actions were taken
4. ADR-034 acceptance criteria are satisfied
5. ADR-034 execution_state can be set to `complete`

---

## Rollback

Revert migrations and seed data. No existing functionality affected.

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-07 | Initial draft |
| 1.1 | 2026-01-07 | Fixed: fragment alias resolver (D3), RenderBlock.type no double-prefix (D4), single-field ID convention (D5), RenderModelBuilder location (D6), schema_id FK to UUID, accept() method, UTC timestamps, schema_id canonical format |
| 1.2 | 2026-01-07 | Fixed: relaxed ID patterns to allow `_.-` (future-proofing), get_accepted uses accepted_at DESC (D7), document_schema_id nullable clarified, deduplication preserves order (first occurrence), nested_list source_pointer relative to parent, FRAGMENT_ALIASES POC-only note, explicit schema IDs in Phase 2 |

---

*End of Work Statement*



