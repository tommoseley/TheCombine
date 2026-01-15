# PROJECT_STATE.md
> Single source of truth for session continuity

## AI Collaboration Notes
Execution constraints for AI collaborators are defined in AI.MD and are considered binding.

## Current Status
**All 10 Implementation Phases Complete** - Production-ready system deployed to AWS
**Document System Architecture Complete** - ADR-030 through ADR-034 implemented
**Document Lifecycle Semantics Frozen** - ADR-036 accepted
**Document Ownership Complete** - ADR-011-Part-2 implemented
**Concierge V1 Implemented** - ADR-025/ADR-026 conversational intake flow

## Test Summary
- **Total Tests:** 1,288 passing
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
| ADR-025 | Complete | Concierge Intake - Conversational Flow |
| ADR-026 | Complete | Concierge Session Management |
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

## Current Session Work: January 14, 2026

### Document Build Status Display Fix - COMPLETE

**Issue:** Status messages during document generation showed spinners for all steps, including completed ones.

**Fix:** Updated `addStatusMessage()` in _document_not_found.html to:
- Track running state via `data-status` attribute on each message div
- When a new step starts, mark all previous running items as complete
- Completed steps now show green checkmark (`check-circle`) instead of spinner

**File Modified:**
- `app/web/templates/public/pages/partials/_document_not_found.html`

### Previous Session Work (Jan 14)

**Concierge Navigation Cleanup - COMPLETE**

1. **Routing Structure** - /start as canonical entry point
2. **Nested Sidebar Issue** - Created _chat_content.html partial for HTMX
3. **Project Creation** - Fixed UUID conversions, success links to Discovery
4. **UI Improvements** - Textarea sizing, container centering, consent reliability

---

## Infrastructure
* **Deployment:** ECS Fargate on `thecombine.ai`
* **Database:** RDS PostgreSQL
* **DNS:** Route 53 with IP workaround (ALB blocked pending AWS ticket)
* **System Config:** `system_config` table for data-driven environment settings

---

## Open Threads
- Fragment dark mode changes require re-seeding
- ArchitecturalSummaryView docdef change (problem_statement order) requires delete + re-seed
- "View Sample Discovery" button needs sample project or static route
- `recycle/` folder needs review then deletion
- Docs cleanup: review duplicates vs Project Knowledge