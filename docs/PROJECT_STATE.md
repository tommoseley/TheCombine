# PROJECT_STATE.md
> Single source of truth for session continuity

## AI Collaboration Notes
Execution constraints for AI collaborators are defined in AI.MD and are considered binding.

## Current Status
**All 10 Implementation Phases Complete** - Production-ready system deployed to AWS
**Document System Architecture Complete** - ADR-030 through ADR-034 implemented
**Document Lifecycle Semantics Frozen** - ADR-036 accepted
**Document Ownership Complete** - ADR-011-Part-2 implemented

## Test Summary
- **Total Tests:** 1,176 passing
- **Phase 0-2 (Core Engine):** Validator, Step Executor, Workflow Executor
- **Phase 3-7:** HTTP API, UI Integration, LLM Integration, Authentication
- **Phase 8-10:** API Integration, E2E Testing, Production Hardening
- **Template Integrity:** Tests ensure all extends/includes resolve correctly
- **BFF Tests:** Epic Backlog, Story Backlog ViewModels and BFF function tests
- **Schema Registry Tests:** CRUD, lifecycle, resolver, cycle detection (28 schemas)
- **Fragment Registry Tests:** CRUD, binding, renderer (18 components)
- **Document Ownership Tests:** 17 tests for cycle detection, scope validation, deletion guards
- **Golden Trace Tests:** RenderModel snapshot tests for docdef validation
- **Component Completeness Tests:** Ensure all components have guidance bullets

---

## Active ADRs

| ADR | Status | Summary |
|-----|--------|---------|
| ADR-009 | Complete | Project Audit — state changes explicit/traceable |
| ADR-010 | Complete | LLM Execution Logging — inputs, outputs, replay |
| ADR-011-Part-2 | Complete | Document Ownership Implementation |
| ADR-030 | Complete | BFF Layer and ViewModel Boundary |
| ADR-031 | Complete | Canonical Schema Types and DB-Backed Registry |
| ADR-032 | Complete | Fragment-Based Rendering |
| ADR-033 | Complete | Data-Only Experience Contracts (RenderModelV1) |
| ADR-034 | Complete | Document Composition Manifest & Canonical Components |
| ADR-035 | Draft | Durable LLM Threaded Queue |
| ADR-036 | **Accepted** | Document Lifecycle & Staleness Semantics |

## Governing Policies
* POL-ADR-EXEC-001: ADR Execution Authorization Process (6-step authorization)
* POL-WS-001: Standard Work Statements (mechanical execution)

---

## Next Logical Work

### Primary: Execute WS-DOCUMENT-SYSTEM-CLEANUP

The document system cleanup plan is ready for execution. See:
- `docs/document-system-charter.md` — Strategic charter (WHY & WHAT)
- `docs/document-cleanup-plan.md` — 9-phase implementation spec (HOW & WHEN)
- `docs/WS-DOCUMENT-SYSTEM-CLEANUP.md` — Work statement for execution

**Phase execution order:**

| Phase | Goal | Can Parallelize |
|-------|------|-----------------|
| 1 | Config → DB only (eliminate DOCUMENT_CONFIG) | ✅ Week 1 |
| 2 | Schema hash persistence (documents store schema_bundle_sha256) | ✅ Week 1 |
| 3 | Document lifecycle states (ADR-036 implementation) | Week 2 |
| 4 | Staleness propagation | Week 3 |
| 5 | Route deprecation with Warning headers | ✅ Week 1 |
| 6 | Legacy template feature flag | ✅ Week 1 |
| 7 | Command route normalization | Week 3 |
| 8 | Debug routes to dev-only | ✅ Week 1 |
| 9 | Data-driven UX (optional) | Week 4 |

**Key principle from ADR-036:** "Partial is not broken. Partial is honest."

### Open Threads
* `recycle/` folder needs review then deletion
* Docs cleanup: review duplicates vs Project Knowledge
* Update ADR-011-Part-2 status from "Draft" to "Accepted" in the ADR file

---

## Infrastructure
* **Deployment:** ECS Fargate on `thecombine.ai`
* **Database:** RDS PostgreSQL
* **DNS:** Route 53 with IP workaround (ALB blocked pending AWS ticket)

---

## Recent Completed Work

### Session: January 12, 2026 - Document System Cleanup Planning

Comprehensive planning session establishing governance and implementation path for document system stabilization.

#### Strategic Documents Created
- `docs/document-system-charter.md` — Charter v3 identifying Three Drifts (Config, Schema, Route)
- `docs/document-cleanup-plan.md` — 9-phase implementation with tests and rollback paths
- `docs/WS-DOCUMENT-SYSTEM-CLEANUP.md` — Work statement for execution
- `docs/adr-amendment-analysis.md` — Governance gap analysis

#### ADR-036: Document Lifecycle & Staleness (Accepted)
- 5 states: missing, generating, partial, complete, stale
- **Partial is a valid end state** (selective generation is intentional)
- Staleness is informational, not destructive
- Regeneration is always explicit
- Non-blocking visibility in all states except missing

#### Key Decisions
- Tabs are data-driven (supersedes WS-DOCUMENT-VIEWER-TABS enum approach)
- UX is data-driven (CTAs, badges, variants, visibility all configurable without code)
- Schema hash persistence: documents store `schema_bundle_sha256` at generation time
- RenderModelV1 is the "hourglass waist" — sole rendering contract

#### Bug Fixes
- 6 component `generation_guidance` format fixes (string → dict with bullets)
- 6 schema `additionalProperties` fixes (True → False)
- Schema count test updated (22 → 28)

### Session: January 12, 2026 (Earlier) - Document Viewer & Story Backlog

#### Document Viewer Implementation (ADR-034)
- Generic `_document_viewer.html` template
- RenderModelBuilder with shape semantics (single, list, nested_list, container)
- Fragment-based rendering for all block types
- Tab support (Overview/Details tabs for EpicBacklogView)

#### Story Backlog Views
- `StoryBacklogView` with epic cards and story summaries
- `StoryDetailView` for full BA output
- `EpicStoriesCardBlockV1` component for story grouping

#### Architecture Views
- `EpicArchitectureView` with components, quality attributes, interfaces, workflows, data models
- `ArchitecturalSummaryView` for architecture overview

#### Governance Documents
- `DOCUMENT_VIEWER_CONTRACT.md` (Frozen)
- `RENDER_SHAPES_SEMANTICS.md` (Frozen)
- `SUMMARY_VIEW_CONTRACT.md` (Frozen)

### Session: January 6-7, 2026 - BFF/Schema/Fragment Architecture

#### WS-001: Epic Backlog BFF Refactor (ADR-030)
- Created `app/web/viewmodels/` with `EpicBacklogVM`, `EpicCardVM`, etc.
- Created `app/web/bff/` with `get_epic_backlog_vm()` function
- Templates now access `vm.*` only (ViewModel boundary enforced)

#### WS-002: Schema Registry Implementation (ADR-031)
- Created `schema_artifacts` table with migration
- Created `SchemaRegistryService` with CRUD and status lifecycle
- Created `SchemaResolver` with bundle resolution and cycle detection
- Seeded canonical types

#### WS-003: Fragment Registry Implementation (ADR-032)
- Created `fragment_artifacts` and `fragment_bindings` tables
- Created `FragmentRenderer` service
- Integrated fragment rendering into document viewer

#### WS-004: Remove HTML from BFF (ADR-033)
- Removed `rendered_open_questions` from ViewModels
- Templates invoke fragment rendering directly via `render_fragment` Jinja2 global

### Session: January 5, 2026 - Document Ownership + UI Consolidation

#### ADR-011-Part-2: Document Ownership Implementation
- Created migration for `parent_document_id`
- Document model with parent/children relationships
- DocumentService with ownership validation methods
- 17 tests for cycle detection, scope validation, deletion guards

#### UI Consolidation
- Consolidated split UI structure into unified `app/web/` with admin/public subfolders
- Fixed template extends statements
