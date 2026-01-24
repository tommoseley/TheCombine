# PROJECT_STATE.md

**Last Updated:** 2026-01-24
**Updated By:** Claude (WS-PGC-VALIDATION-001 Complete)

## Current Focus

WS-PGC-VALIDATION-001 complete. Code-based promotion validation implemented and integrated. PGC answers now persist as first-class documents with full provenance. Ready for UX integration to surface PGC questions in document workflow experience.

## WS-PGC-VALIDATION-001 - COMPLETE (2026-01-24)

### What Was Built

#### Phase 1: Code-Based Promotion Validation
Deterministic validation layer that runs BEFORE LLM-based QA:

| Rule | Type | Description |
|------|------|-------------|
| Promotion Validity | WARNING | Constraints must trace to must-priority answers or intake |
| Internal Contradiction | ERROR | Same concept cannot be in both constraints and assumptions |
| Policy Conformance | WARNING | No budget/authority questions in unknowns |
| Grounding Validation | WARNING | Guardrails must trace to explicit input |

**Implementation:**
```
app/domain/workflow/validation/
â”œâ”€â”€ __init__.py
â”œâ”€â”€ validation_result.py    # Data classes
â”œâ”€â”€ rules.py                # Rule implementations (keyword extraction, Jaccard similarity)
â””â”€â”€ promotion_validator.py  # PromotionValidator class
```

**Integration:** `app/domain/workflow/nodes/qa.py` calls `_run_code_based_validation()` before LLM QA.

#### Phase 2: PGC Answer Persistence
PGC answers now stored as first-class documents with full provenance:

**Model:** `app/api/models/pgc_answer.py`
```python
class PGCAnswer:
    id: UUID
    execution_id: str
    workflow_id: str
    project_id: UUID
    pgc_node_id: str
    schema_ref: str
    questions: JSONB      # Snapshot at time of answer
    answers: JSONB        # User's responses
    created_at: DateTime
```

**Repository:** `app/domain/repositories/pgc_answer_repository.py`
- `add()` - Does NOT commit (caller owns transaction)
- `get_by_execution()` - Load by execution ID
- `get_by_project()` - Load all for project, newest first

**New Endpoint:**
```
GET /api/v1/document-workflows/executions/{id}/pgc-answers
```

**Integration Flow:**
1. User submits at PGC node â†’ answers persisted to `pgc_answers` table
2. QA node executes â†’ `plan_executor` loads answers into context
3. Validation runs â†’ uses `pgc_questions` and `pgc_answers` from context

### Test Coverage
- **Phase 1:** 29 tests in `tests/tier1/workflow/validation/`
- **Phase 2:** 7 tests in `tests/tier1/repositories/`
- All tests passing

### Migration Required
```
alembic upgrade head
```
Creates `pgc_answers` table (migration: `20260124_001_create_pgc_answers_table.py`)

## Document Workflow - FUNCTIONAL (2026-01-24)

### End-to-End Flow
```
Start â†’ PGC (questions) â†’ User Input (JSON) â†’ Generation â†’ Code Validation â†’ LLM QA â†’ Persist â†’ Complete
```

### PGC Payload Contract
| Field | Purpose |
|-------|---------|
| `pending_user_input_payload` | Structured JSON object (source of truth) |
| `pending_user_input_schema_ref` | Schema identifier (e.g., "schema://clarification_question_set.v2") |
| `pending_user_input_rendered` | Optional human-readable text (NOT JSON) |

### Schema Consistency Rules
PGC questions enforce derivation from priority:

| priority | required | blocking |
|----------|----------|----------|
| must     | true     | true     |
| should   | false    | false    |
| could    | false    | false    |

### Decision Promotion Rules (PD v1.3 + Code Validation)
- Only "must" answers with specific choices â†’ `known_constraints`
- "should"/"could" answers â†’ `assumptions` (never constraints)
- No budget/funding/authority questions anywhere
- Internal consistency: item cannot be both assumption and constraint
- **Now enforced by code-based validation, not just LLM prompts**

## Prompt Versions (Current)

| Prompt | Version | Key Features |
|--------|---------|--------------|
| Clarification Questions Generator | v1.1 | Schema consistency rules |
| Project Discovery | v1.3 | Strict promotion rules, no budget questions |
| Project Discovery QA | v1.1 | Semantic checks (4 categories) |

## Workflow Version

`project_discovery.v1.json` â†’ **v1.7.0**
- PGC: Clarification Questions Generator v1.1
- Generation: Project Discovery v1.3
- QA: Project Discovery QA v1.1 (semantic mode)
- **NEW:** Code-based validation integrated before LLM QA

## Immediate Next Steps

### 1. WS-PGC-UX-001: PGC Questions UI (Ready for Claude Code)
Work statement created. Implements:
- Workflow-based document builds (replaces background task for PGC types)
- PGC questions form rendering
- Answer submission and workflow resume
- Progress polling during generation
- Success/failure UI states

**Files to create:**
- `app/web/routes/public/workflow_build_routes.py`
- `app/web/templates/public/pages/partials/_workflow_build_container.html`
- `app/web/templates/public/pages/partials/_pgc_questions.html`

### 2. Admin UI (After UX)
- Document viewer in Admin UI
- PGC answers display with audit trail
- Validation results display

### 3. Production Verification
- End-to-end test with real LLM
- Verify promotion violations caught
- Move old prompts to recycle/
## API Contract (Document Workflows)

### Start Workflow
```
POST /api/v1/document-workflows/start
{
  "project_id": "uuid",
  "document_type": "project_discovery"
}
```

### Get Status (When Paused)
```json
{
  "execution_id": "exec-xxx",
  "status": "paused",
  "current_node_id": "pgc",
  "pending_user_input": true,
  "pending_user_input_payload": { /* structured questions */ },
  "pending_user_input_schema_ref": "schema://clarification_question_set.v2",
  "pending_user_input_rendered": "Human-readable text..."
}
```

### Submit Answers
```
POST /api/v1/document-workflows/executions/{id}/input
{
  "user_input": {
    "TARGET_PLATFORM": "web",
    "MATH_SCOPE": ["counting", "addition"],
    "USE_CONTEXT": "classroom"
  }
}
```

### Get PGC Answers (NEW)
```
GET /api/v1/document-workflows/executions/{id}/pgc-answers
```

### Run to Completion
```
POST /api/v1/document-workflows/executions/{id}/run
```

### Get Final Document
```
GET /api/v1/document-workflows/executions/{id}
â†’ produced_documents.document_project_discovery
```

## Key Files (Updated This Session)

### Validation System (NEW)
- `app/domain/workflow/validation/__init__.py` - Module exports
- `app/domain/workflow/validation/validation_result.py` - Data classes
- `app/domain/workflow/validation/rules.py` - Rule implementations
- `app/domain/workflow/validation/promotion_validator.py` - PromotionValidator

### PGC Answer Persistence (NEW)
- `app/api/models/pgc_answer.py` - SQLAlchemy model
- `app/domain/repositories/pgc_answer_repository.py` - Repository
- `alembic/versions/20260124_001_create_pgc_answers_table.py` - Migration

### Modified Files
- `app/domain/workflow/nodes/qa.py` - Integrated code-based validation
- `app/domain/workflow/plan_executor.py` - Load PGC answers for QA
- `app/api/v1/routers/document_workflows.py` - Persist answers, new endpoint
- `app/api/models/__init__.py` - Export PGCAnswer

### Tests (NEW)
- `tests/tier1/workflow/validation/test_promotion_validator.py` - 29 tests
- `tests/tier1/repositories/test_pgc_answer_repository.py` - 7 tests

## Technical Debt

### ~~Code-Based Promotion Validation~~ âœ… RESOLVED (2026-01-24)
**Was:** LLM-based semantic QA is non-deterministic; promotion violations slip through.
**Resolution:** WS-PGC-VALIDATION-001 Phase 1 implemented deterministic validation.

### ~~PGC Answers Not First-Class Document~~ âœ… RESOLVED (2026-01-24)
**Was:** PGC answers stored only in `context_state["pgc_answers"]`, not as document with provenance.
**Resolution:** WS-PGC-VALIDATION-001 Phase 2 implemented `pgc_answers` table with full provenance.

### Old Prompt Cleanup (2026-01-24)
**Issue:** Old prompt versions (v1.0, v1.2) still exist after migration.

**Preferred approach:** Move to `recycle/` after production verification:
- `Clarification Questions Generator v1.0.txt`
- `Project Discovery v1.1.txt` (if exists)
- `Project Discovery v1.2.txt`
- `Project Discovery QA v1.0.txt`

### Two PromptAssembler Classes (2026-01-23)
**Issue:** Two classes named similarly exist:
- `app/domain/services/prompt_assembler.py` - ADR-034 database-driven assembly
- `app/domain/prompt/assembler.py` - ADR-041 filesystem template assembly

**Preferred approach:** Rename or consolidate.

### Project ID Scoping (2026-01-22)
**Issue:** Project IDs globally unique across all users.

**Preferred approach:** User-scoped IDs with ownership verification.

### Tier-3 Tests Deferred (2026-01-22)
**Issue:** Real PostgreSQL integration tests are deferred.

**Preferred approach:** Implement with real test database infrastructure.

## Recently Completed

### WS-PGC-VALIDATION-001 (2026-01-24)
- **Phase 1:** Code-based promotion validation with 4 rule checks
- **Phase 2:** PGC answer persistence with full provenance
- 36 new tests (29 validation + 7 repository)
- New API endpoint for retrieving PGC answers

### Document Persistence (2026-01-24)
- Documents persist on workflow completion
- System-owned metadata fields enforced
- Provenance tracking via correlation_id

### PGC Payload Hardening (2026-01-24)
- Structured payload object (not JSON string)
- Schema reference for validation
- Human-readable rendering separate from data

### Semantic QA Implementation (2026-01-24)
- Promotion validity checks
- Internal contradiction detection
- Policy conformance (no budget questions)
- Grounding validation

## Environment

- Local dev: WSL Ubuntu, Python 3.11, FastAPI
- Database: PostgreSQL (run migration for new table)
- LLM: Anthropic Claude API
- Tests: 36 new tests passing
- Workflow: `project_discovery.v1.json` v1.7.0
