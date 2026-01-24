# PROJECT_STATE.md

**Last Updated:** 2026-01-24
**Updated By:** Claude (Session Close)

## Current Focus

Document workflow end-to-end complete. PGC payload contract hardened. Semantic QA implemented (prompt-based). Ready for UX integration to surface PGC questions in document workflow experience.

## Document Workflow - FUNCTIONAL (2026-01-24)

### End-to-End Flow Working
```
Start → PGC (questions) → User Input (JSON) → Generation → QA → Persist → Complete
```

### What Was Built (This Session)

#### Document Persistence
- Documents persist to `documents` table on successful completion
- System-owned metadata enforced:
  - `meta.created_at` - Execution timestamp (UTC ISO 8601)
  - `meta.artifact_id` - `{DOC_TYPE}-{execution_id}` format
  - `meta.correlation_id` - Links to execution_id
  - `meta.workflow_id` - Links to workflow definition
- LLM-minted values logged as warnings and overwritten

#### PGC Payload Contract
| Field | Purpose |
|-------|---------|
| `pending_user_input_payload` | Structured JSON object (source of truth) |
| `pending_user_input_schema_ref` | Schema identifier (e.g., "schema://clarification_question_set.v2") |
| `pending_user_input_rendered` | Optional human-readable text (NOT JSON) |

#### Schema Consistency Rules
PGC questions now enforce derivation from priority:

| priority | required | blocking |
|----------|----------|----------|
| must     | true     | true     |
| should   | false    | false    |
| could    | false    | false    |

#### Decision Promotion Rules (PD v1.3)
- Only "must" answers with specific choices → `known_constraints`
- "should"/"could" answers → `assumptions` (never constraints)
- No budget/funding/authority questions anywhere
- Internal consistency: item cannot be both assumption and constraint

#### Semantic QA (v1.1)
New check categories (prompt-based, non-deterministic):
- **Promotion Validity**: Warns if constraint derived from non-must answer
- **Internal Contradiction**: Errors if same item in assumptions AND constraints
- **Policy Conformance**: Warns on budget/authority questions
- **Grounding Validation**: Warns if guardrails are inferred not stated

### Verified Test Run
```
Execution: exec-af0796d77fc6
PGC: 7 questions (3 must, 3 should, 1 could)
Schema consistency: ✅ All questions correctly derived
Answers: JSON object with all fields
Generation: ✅ Document produced
QA: ✅ Passed (warning: missing optional mvp_guardrails)
Persistence: ✅ Document in database with correct meta
```

### Known Gap
Semantic QA v1.1 (LLM-based) did not catch promotion violations:
- CNS-5 "Must include progress tracking" came from `should` priority
- CNS-6 "Must align with Common Core" came from `should` priority
- CNS-7 "Must meet accessibility" came from `could` priority

**Root cause:** LLM-based QA is non-deterministic.
**Solution:** Code-based validation layer (technical debt).

## Prompt Versions (Current)

| Prompt | Version | Key Features |
|--------|---------|--------------|
| Clarification Questions Generator | v1.1 | Schema consistency rules |
| Project Discovery | v1.3 | Strict promotion rules, no budget questions |
| Project Discovery QA | v1.1 | Semantic checks (4 categories) |

## Workflow Version

`project_discovery.v1.json` → **v1.7.0**
- PGC: Clarification Questions Generator v1.1
- Generation: Project Discovery v1.3
- QA: Project Discovery QA v1.1 (semantic mode)

## Immediate Next Steps

### 1. UX Integration (Priority)
- Build PGC questions UI in document workflow experience
- Render questions from `pending_user_input_payload`
- Handle different answer types (single_choice, multi_choice, yes_no, free_text)
- Submit answers as JSON object

### 2. Database Integration
- Store PGC answers as first-class document with provenance
- Pass PGC answers explicitly to QA node for validation
- Build document viewer in Admin UI

### 3. Code-Based Validation (Technical Debt)
- Deterministic promotion validation (bypass LLM non-determinism)
- Run before LLM-based semantic QA
- Fail fast on promotion violations

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

### Run to Completion
```
POST /api/v1/document-workflows/executions/{id}/run
```

### Get Final Document
```
GET /api/v1/document-workflows/executions/{id}
→ produced_documents.document_project_discovery
```

## Database Schema Update Required

```sql
ALTER TABLE workflow_executions 
ADD COLUMN pending_user_input_payload JSONB,
ADD COLUMN pending_user_input_schema_ref VARCHAR(255);
```

Or run: `alembic upgrade head`

## Key Files (Updated This Session)

### Workflow System
- `app/domain/workflow/plan_executor.py` - Document persistence, pause handling
- `app/domain/workflow/document_workflow_state.py` - New payload fields
- `app/domain/workflow/pg_state_persistence.py` - Persistence layer
- `app/domain/workflow/nodes/task.py` - PGC payload handling
- `app/domain/workflow/nodes/base.py` - NodeResult fields

### API
- `app/api/v1/routers/document_workflows.py` - Response models
- `app/api/models/workflow_execution.py` - DB columns

### Prompts
- `seed/prompts/tasks/Clarification Questions Generator v1.1.txt`
- `seed/prompts/tasks/Project Discovery v1.3.txt`
- `seed/prompts/tasks/Project Discovery QA v1.1.txt`
- `seed/workflows/project_discovery.v1.json` (v1.7.0)

## Technical Debt

### Code-Based Promotion Validation (2026-01-24)
**Issue:** LLM-based semantic QA is non-deterministic; promotion violations slip through.

**Preferred approach:** Deterministic code-based validation layer that:
- Validates constraint sources against PGC answer priorities
- Checks internal consistency (assumption ≠ constraint)
- Runs before LLM-based QA

**Files affected:** New module in `app/domain/workflow/validation/`

### PGC Answers Not First-Class Document (2026-01-24)
**Issue:** PGC answers stored only in `context_state["pgc_answers"]`, not as document with provenance.

**Preferred approach:** Persist as document with:
- `correlation_id` linking to workflow execution
- Schema reference for validation
- Audit trail for answer changes

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

### Field Rename (2026-01-24)
- `pending_prompt` → `pending_user_input_rendered`
- DB column alias for backward compatibility

## Environment

- Local dev: WSL Ubuntu, Python 3.10, FastAPI
- Database: PostgreSQL (needs migration for new columns)
- LLM: Anthropic Claude API
- Tests: Pending run after field rename
- Workflow: `project_discovery.v1.json` v1.7.0