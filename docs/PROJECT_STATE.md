# PROJECT_STATE.md
> Single source of truth for session continuity

## AI Collaboration Notes
Execution constraints for AI collaborators are defined in AI.MD and are considered binding.

## Current Status
**All 10 Implementation Phases Complete** - Production-ready system deployed to AWS
**BFF/Schema/Fragment Architecture Complete** - ADR-030 through ADR-033 implemented
**Document Ownership Complete** - ADR-011-Part-2 implemented

## Test Summary
- **Total Tests:** 1071 passing
- **Phase 0-2 (Core Engine):** Validator, Step Executor, Workflow Executor
- **Phase 3-7:** HTTP API, UI Integration, LLM Integration, Authentication
- **Phase 8-10:** API Integration, E2E Testing, Production Hardening
- **Template Integrity:** Tests ensure all extends/includes resolve correctly
- **BFF Tests:** Epic Backlog ViewModel and BFF function tests
- **Schema Registry Tests:** CRUD, lifecycle, resolver, cycle detection
- **Fragment Registry Tests:** CRUD, binding, renderer
- **Document Ownership Tests:** 17 tests for cycle detection, scope validation, deletion guards

---

## Completed Work

### Session: January 6, 2026 — BFF/Schema/Fragment Architecture

Implemented foundational architecture for schema-driven, fragment-based UI rendering.

#### WS-001: Epic Backlog BFF Refactor (ADR-030)
- Created `app/web/viewmodels/` with `EpicBacklogVM`, `EpicCardVM`, etc.
- Created `app/web/bff/` with `get_epic_backlog_vm()` function
- Templates now access `vm.*` only (ViewModel boundary enforced)
- 21 BFF tests added

#### WS-002: Schema Registry Implementation (ADR-031)
- Created `schema_artifacts` table with migration
- Created `SchemaArtifact` ORM model
- Created `SchemaRegistryService` with CRUD and status lifecycle
- Created `SchemaResolver` with bundle resolution and cycle detection
- Seeded 4 canonical types: `OpenQuestionV1`, `RiskV1`, `DependencyV1`, `ScopeItemV1`
- Extended `llm_execution_logs` with schema tracking columns
- 38 new tests

#### WS-003: Fragment Registry Implementation (ADR-032)
- Created `fragment_artifacts` and `fragment_bindings` tables
- Created `FragmentArtifact` and `FragmentBinding` ORM models
- Created `FragmentRegistryService` with binding lookup
- Created `FragmentRenderer` service
- Seeded `OpenQuestionV1Fragment` with active binding
- Integrated fragment rendering into Epic Backlog
- 32 new tests

#### WS-004: Remove HTML from BFF (ADR-033)
- Removed `rendered_open_questions` from ViewModels
- Removed `fragment_renderer` parameter from BFF
- Created `PreloadedFragmentRenderer` for async template use
- Created `render_fragment` Jinja2 global
- Templates invoke fragment rendering directly
- 7 new tests

### Session: January 5, 2026 — Document Ownership + UI Consolidation

#### ADR-011-Part-2: Document Ownership Implementation
- Created migration `20260105_001_add_parent_document_id.py`
- Updated Document model with `parent_document_id`, parent/children relationships
- Extended DocumentService with ownership validation methods:
  - `validate_parent_assignment()` - main entry point
  - `_check_no_cycle()` - cycle detection via parent chain walk
  - `_check_ownership_validity()` - workflow may_own validation
  - `_check_scope_monotonicity()` - child scope >= parent scope
  - `validate_deletion()` - guard against deleting docs with children
- Exception classes: `OwnershipError`, `CycleDetectedError`, `InvalidOwnershipError`, `IncomparableScopesError`, `ScopeViolationError`, `HasChildrenError`
- 17 tests in `tests/unit/test_document_ownership.py`

#### UI Consolidation
- Consolidated split UI structure into unified `app/web/` with admin/public subfolders
- Fixed template extends statements missing `public/` prefix
- Added `tests/ui/test_template_integrity.py`
- Archived 10 obsolete planning documents to `docs/archive/`

---

## AWS Infrastructure

### Current Environment (Staging)

| Resource | Name/ID | Status |
|----------|---------|--------|
| **ECS Cluster** | the-combine-cluster | Running |
| **ECS Service** | the-combine-service | Running |
| **Task Definition** | the-combine-task | Active |
| **ECR Repository** | the-combine | Active |
| **RDS PostgreSQL** | (default) | Running |
| **Route 53** | thecombine.ai | Configured |
| **ACM Certificate** | thecombine.ai + *.thecombine.ai | Issued |
| **Target Group** | the-combine-tg (IP, port 8000) | Created |
| **ALB** | - | Blocked (ticket pending) |

### Environment Variables (ECS Task Definition)
- ADMIN_EMAILS = tommoseley@outlook.com (Configured)

### ALB Issue
Support tickets filed for **us-east-1** and **us-east-2**. Awaiting AWS response.

### Current Workaround
Using `fixip.ps1` to update Route 53 A record after each deployment.

---

## Governing ADRs

| ADR | Status | Execution | Summary |
|-----|--------|-----------|---------|
| ADR-009 | Accepted | Complete | Project Audit - state changes explicit/traceable |
| ADR-010 | Accepted | Complete | LLM Execution Logging - inputs, outputs, replay |
| ADR-011 | Accepted | Complete | Document Ownership Model - conceptual |
| ADR-011-Part-2 | Accepted | Complete | Document Ownership Implementation |
| ADR-012 | Accepted | - | Interaction Model - closed-loop execution |
| ADR-024 | Accepted | - | Clarification Question Protocol |
| ADR-027 | Accepted | - | Workflow Definition & Governance |
| ADR-030 | Accepted | Complete | BFF Layer and ViewModel Boundary |
| ADR-031 | Accepted | Complete | Canonical Schema Types and DB-Backed Registry |
| ADR-032 | Accepted | Complete | Fragment-Based Rendering |
| ADR-033 | Accepted | Partial | Data-Only Experience Contracts (WS-004 done) |

## Work Statements

| WS | ADR | Status | Summary |
|----|-----|--------|---------|
| WS-001 | ADR-030 | Complete | Epic Backlog BFF Refactor |
| WS-002 | ADR-031 | Complete | Schema Registry Implementation |
| WS-003 | ADR-032 | Complete | Fragment Registry Implementation |
| WS-004 | ADR-033 | Complete | Remove HTML from BFF Contracts |

---

## Next Session

**Continue ADR-033:** Full Render Model implementation (Experience JSON to Render Model to Channel Viewers).

Or pick up other pending ADRs that need execution authorization.

---

## Open Threads

- `recycle/` folder needs review then deletion
- Docs cleanup: review duplicates vs Project Knowledge
- Update ADR-011-Part-2 status from "Draft" to "Accepted" in the ADR file
- Update ADR-011-Part-2 Implementation Plan status to "Complete"

## Run Tests

    cd "C:\Dev\The Combine"
    python -m pytest tests/ -v

---
_Last updated: 2026-01-07_
