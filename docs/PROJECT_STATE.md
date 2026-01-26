# PROJECT_STATE.md

**Last Updated:** 2026-01-26
**Updated By:** Claude (WS-ADR-043-001 Bug Fixes)

## Current Focus

WS-ADR-043-001 Production Line implementation. Phases 1-8 backend complete. Phase 7 UI has bug fixes in progress.

**Handoff Notes for Claude.ai UX Work:**
- Production Line route: `GET /production?project_id={uuid}`
- Template: `app/web/templates/production/line.html` (extends base, includes `_line_content.html`)
- Partial: `app/web/templates/production/_line_content.html` (returned for HTMX requests)
- Route: `app/web/routes/production.py`
- API: `app/api/v1/routers/production.py` (SSE events)
- Service: `app/api/services/production_service.py` (track building)

The UI currently shows all project-scoped documents from the master workflow:
- Project Discovery
- Epic Backlog
- Project Technical Architecture

Bug fixes made this session - restart server to test.

---

## WS-ADR-043-001 - IN PROGRESS (2026-01-26)

### Phase Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1: Terminology | Complete | Production vocabulary (assemble, stabilized, halted, etc.) |
| Phase 2: State Model | Complete | ProductionState enum in `production_state.py` |
| Phase 3: SSE Infrastructure | Complete | `/production/events` endpoint |
| Phase 4: Project Orchestrator | Complete | `run_full_line()` traverses dependency graph |
| Phase 5: Interrupt Registry | Complete | Register, resolve, get_pending |
| Phase 6: Production API | Complete | Status, start, track endpoints |
| Phase 7: UI | In Progress | Bug fixes for rendering |
| Phase 8: Escalation | Complete | Acknowledge & Continue flow |

### Bug Fixes This Session (2026-01-26)

1. **correlation_id.hex AttributeError** - Middleware stores as string, converted to UUID
2. **start_execution() parameter** - Changed `document_id` to `project_id`
3. **WorkflowExecution.state** - Model has `current_node_id` and `execution_log`, not `state`
4. **Document types** - Now reads from master workflow to show all project-scoped documents

### Key Files

**Backend:**
- `app/domain/workflow/production_state.py` - State enum, station enum
- `app/domain/workflow/project_orchestrator.py` - Full line orchestration
- `app/domain/workflow/interrupt_registry.py` - Interrupt tracking
- `app/api/services/production_service.py` - Track building from workflow
- `app/api/v1/routers/production.py` - SSE events, status endpoints
- `app/api/v1/routers/interrupts.py` - Interrupt resolution, escalation

**Frontend:**
- `app/web/routes/production.py` - Web routes
- `app/web/templates/production/line.html` - Full page
- `app/web/templates/production/_line_content.html` - HTMX partial
- `app/web/templates/production/interrupt.html` - Interrupt modal macro

**Config:**
- `seed/workflows/software_product_development.v1.json` - Master workflow (document types, dependencies)
- `seed/workflows/project_discovery.v1.json` - DIW plan for project_discovery
- `seed/workflows/concierge_intake.v1.json` - DIW plan for concierge_intake

---

## WS-ADR-042-001 - COMPLETE (2026-01-24)

### What Was Built

Constraint binding system (ADR-042) with drift enforcement:
- PGC questions/answers merged into `pgc_clarifications` with binding status
- Drift validation checks (QA-PGC-001 through QA-PGC-004)
- Bound constraints rendered in LLM context
- pgc_invariants promoted to document structure

### Key Files
- `app/domain/workflow/clarification_merger.py`
- `app/domain/workflow/validation/constraint_drift_validator.py`
- `seed/prompts/tasks/Project Discovery v1.4.txt`
- `seed/workflows/project_discovery.v1.json` (v1.8.0)

---

## WS-PGC-VALIDATION-001 - COMPLETE (2026-01-24)

### What Was Built

Code-based promotion validation + PGC answer persistence:
- Deterministic validation before LLM QA (promotion, contradiction, policy, grounding)
- `pgc_answers` table with full provenance
- API endpoint for retrieving PGC answers

### Key Files
- `app/domain/workflow/validation/` (validation rules)
- `app/api/models/pgc_answer.py`
- `app/domain/repositories/pgc_answer_repository.py`

---

## API Contract (Production Line)

### Production Line Status
```
GET /production?project_id={uuid}
```

### SSE Events
```
GET /api/v1/production/events?project_id={uuid}

Events:
- connected
- station_transition
- line_stopped
- production_complete
- interrupt_resolved
- track_started
- track_stabilized
- document_escalated
- keepalive
```

### Start Production
```
POST /api/v1/production/start?project_id={uuid}           # Full line
POST /api/v1/production/start?project_id={uuid}&document_type={type}  # Single doc
```

### Interrupts
```
GET /api/v1/projects/{id}/interrupts
POST /api/v1/interrupts/{id}/resolve
POST /api/v1/interrupts/{id}/escalate
```

---

## Technical Debt

### Production Service Reads Raw JSON
**Issue:** `get_document_type_dependencies()` parses `software_product_development.v1.json` directly.
**Risk:** If master workflow schema changes, parsing breaks silently.
**Preferred:** Load via plan registry or dedicated model.

### Old Prompt Cleanup (2026-01-24)
**Issue:** Old prompt versions still exist after migration.
**Preferred:** Move to `recycle/` after verification.

### QA-PGC-002 Stopwords Approach (2026-01-24)
**Issue:** Manually-maintained stopwords list for false positive prevention.
**Preferred:** Semantic similarity or focus on answer values.

### Circular Import in llm_execution_logger.py (2026-01-25)
**Issue:** Import chain through `app.core/__init__.py`.
**Workaround:** Lazy import of `calculate_cost`.

---

## Immediate Next Steps

### 1. Complete Production Line UI Testing
- Verify all bug fixes work end-to-end
- Test: Start Production single document
- Test: Run Full Line
- Test: Interrupt resolution
- Test: Escalation flow

### 2. UX Polish (Claude.ai)
- Review visual design of Production Line
- Verify track expansion behavior
- Test interrupt modal rendering
- Mobile/responsive considerations (desktop-first but check breakpoints)

### 3. Admin Integration
- Link Production Line from project dashboard
- Consider adding to main navigation

---

## Workflow Versions

| Workflow | Version | Notes |
|----------|---------|-------|
| project_discovery.v1.json | v1.8.0 | Constraint binding, drift enforcement |
| concierge_intake.v1.json | v1.3.0 | Single-pass intake gate |
| software_product_development.v1.json | wfrev_2026_01_02_a | Master workflow definition |

---

## Environment

- Local dev: WSL Ubuntu, Python 3.10, FastAPI
- Database: PostgreSQL
- LLM: Anthropic Claude API
- Workflow: ADR-039 Document Interaction Workflows
