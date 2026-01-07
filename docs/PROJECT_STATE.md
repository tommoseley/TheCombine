# PROJECT_STATE.md
> Single source of truth for session continuity

## AI Collaboration Notes
Execution constraints for AI collaborators are defined in AI.MD and are considered binding.

## Current Status
**All 10 Implementation Phases Complete** - Production-ready system deployed to AWS

## Test Summary
- **Total Tests:** 943 passing
- **Phase 0-2 (Core Engine):** Validator, Step Executor, Workflow Executor
- **Phase 3-7:** HTTP API, UI Integration, LLM Integration, Authentication
- **Phase 8-10:** API Integration, E2E Testing, Production Hardening
- **Template Integrity:** Tests ensure all extends/includes resolve correctly

---

## Session: January 5, 2026

### UI Consolidation Complete

Consolidated split UI structure into unified `app/web/` with admin/public subfolders.

**New Unified Structure:**
```
app/web/
  routes/
    admin/        <- dashboard.py, pages.py, documents.py, partials.py, admin_routes.py
    public/       <- home_routes.py, project_routes.py, document_routes.py, etc.
    shared.py     <- Jinja2 templates, filters (localtime, pluralize)
  templates/
    admin/        <- Admin pages, components, partials
    public/       <- Public pages, layout, components
  static/
    admin/        <- CSS/JS (websocket.js, styles.css)
    public/       <- login.html, accounts.html
```

### Template Path Fixes

Fixed template extends statements missing `public/` prefix in document_page.html, document_wrapper.html, project_detail.html.

### New Template Integrity Tests

Added `tests/ui/test_template_integrity.py` - catches template path issues before deployment.

### Documentation Cleanup

**Archived (moved to docs/archive/):**
- ARCHITECTURE-RESTRUCTURE-PROPOSAL-v3.md
- document-centric-execution-plan.md
- interface-architecture-plan.md
- TEMPLATE_PATTERN.md, TEMPLATE_PATTERN_V2.md, Template Pattern V2 Implementation.md
- MODEL-SELECTION-IMPLEMENTATION.md
- STAGE_6_INSTALLATION.md
- PHASE-11-SHAKEDOWN.md
- FSO-1 - Floating Status Overlay.txt

**Pending Review (duplicates in Project Knowledge):**
- the-combine-design-manifesto.md
- the-combine-design-constitution-and-design-tokens.md
- The Combine - Canonical Coding Standards.md
- the-combine-architecture-design-record.md
- the-combine-architecture-ux-reference.md
- the-combine-ui-constitution-v2.md

### ADR-011-Part-2 Updated (v0.92)

Document ownership implementation ADR updated with:
- Canonical scope ordering: org=400, project=300, epic=200, story=100, file=0
- Cycle detection algorithm (walk parent chain)
- ON DELETE RESTRICT for orphan prevention
- Migration path (NULL by default)
- Section 4 clarifies generation deps vs UI/navigation
- Implementation order guidance

---

## AWS Infrastructure

### Current Environment (Staging)

| Resource | Name/ID | Status |
|----------|---------|--------|
| **ECS Cluster** | `the-combine-cluster` | âœ… Running |
| **ECS Service** | `the-combine-service` | âœ… Running |
| **Task Definition** | `the-combine-task` | âœ… Active |
| **ECR Repository** | `the-combine` | âœ… Active |
| **RDS PostgreSQL** | (default) | âœ… Running |
| **Route 53** | `thecombine.ai` | âœ… Configured |
| **ACM Certificate** | `thecombine.ai` + `*.thecombine.ai` | âœ… Issued |
| **Target Group** | `the-combine-tg` (IP, port 8000) | âœ… Created |
| **ALB** | - | âŒ Blocked (ticket pending) |

### Environment Variables (ECS Task Definition)
- `ADMIN_EMAILS` = `tommoseley@outlook.com` âœ… Configured

### ALB Issue
Support tickets filed for **us-east-1** and **us-east-2**. Awaiting AWS response.

### Current Workaround
Using `fixip.ps1` to update Route 53 A record after each deployment.

### Future: Production Environment
Current environment will become **staging**, new environment for **production**.

---

## Governing ADRs

| ADR | Status | Summary |
|-----|--------|---------|
| ADR-009 | Complete | Project Audit - all state changes explicit and traceable |
| ADR-010 | Complete | LLM Execution Logging - inputs, outputs, replay capability |
| ADR-011 | Accepted | Document Ownership Model - conceptual |
| ADR-011-Part-2 | Draft v0.92 | Document Ownership Implementation - ready for next session |
| ADR-012 | Accepted | Interaction Model - closed-loop execution, QA as veto |
| ADR-024 | Accepted | Clarification Question Protocol |
| ADR-027 | Accepted | Workflow Definition & Governance |

## 🚀 Next Session: ADR-011-Part-2 Implementation

**Ready to rumble.** ADR-011-Part-2 (v0.92) is finalized and ready for implementation.

**Start here:** `docs/adr/011-part-2-documentation-ownership-impl/ADR-011-Part-2-Document-Ownership-Model-Implementation-Enforcement.md`

Implementation order:
1. Schema migration (`parent_document_id` + FK + index)
2. ORM relationships (`parent`, `children`)
3. Deletion guard
4. Cycle detection
5. Scope validation
6. Tests for all five categories
7. UI traversal queries

## Open Threads

- `recycle/` folder needs review then deletion
- Docs cleanup: review duplicates vs Project Knowledge

## Run Tests

```powershell
cd "C:\Dev\The Combine"
python -m pytest tests/ -v
```

---
_Last updated: 2026-01-05_