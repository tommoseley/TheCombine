# PROJECT_STATE.md

**Last Updated:** 2026-02-12
**Updated By:** Claude (WS-STATION-DATA-001 complete, internal_step events, UI polish)

## Current Focus

**COMPLETE:** ADR-047 -- Mechanical Operations (execution_state: complete)

All work statements delivered:
- **WS-ADR-047-001** (Complete): Mechanical Operations Foundation
- **WS-ADR-047-002** (Complete): Entry Operations Implementation
- **WS-ADR-047-003** (Complete): Extraction Operations
- **WS-ADR-047-004** (Complete): Handler Refactoring
- **WS-ADR-047-005** (Complete): Concierge Intake Gate Refactoring -- Gate Profile pattern with LLM/MECH/UI internals

**DRAFT:** ADR-048 -- Intake POW and Workflow Routing

Defines front-door architecture:
- `intake_and_route` POW with DCW â†’ route â†’ validate â†’ spawn steps
- Complete-and-handoff spawn model with lineage tracking
- `routing_decision.v1` schema with candidates and QA checks

**COMPLETE:** ADR-048 Mechanical Operations

| Component | Status |
|-----------|--------|
| `intake_and_route` POW definition | Complete |
| `routing_decision` schema | Complete |
| `spawn_receipt` schema | Complete |
| `route_confirmation` schema | Complete |
| `intake_route` operation + RouterHandler | Complete |
| `validate_routing_decision` operation + ValidatorHandler | Complete |
| `confirm_route` entry operation (EntryHandler) | Complete |
| `spawn_pow_instance` operation + SpawnerHandler | Complete |

**PENDING:** ADR-048 Integration

| Component | Status |
|-----------|--------|
| Wire intake_and_route POW to execute | Pending |
| Actual child POW creation in SpawnerHandler | Pending |
| UX: Collapsed receipt view for completed Intake | Pending |

---

## Admin Workbench Status

**Location:** `/admin/workbench` (SPA route)

### Features Complete
- All features from previous state
- **Gate Profile pattern** (2026-02-07): Concierge Intake uses Gate Profile with 4 internals (pass_a/LLM, extract/MECH, entry/UI, pin/MECH)
- **intake_and_route POW** (2026-02-07): Front-door POW visible in left rail under "Project Orchestration (POWs)"
- **RouterHandler** (2026-02-07): Mechanical operation handler for routing intake to follow-on POW
- **Selected item highlighting** (2026-02-07): Building Blocks tray highlights selected items

---


---

## WS-STATION-DATA-001 Status (Complete)

Event-driven station display system for production floor UI.

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | Complete | Station metadata in workflow definitions, backend derivation |
| Phase 2 | Complete | Backend event emission (stations_declared, station_changed, internal_step) |
| Phase 3 | Complete | Frontend event handling, real-time UI updates |

### Events Emitted
- `stations_declared` - Full station list on workflow start (with phases array)
- `station_changed` - Station state transitions (pending/active/complete/blocked)
- `internal_step` - Sub-step progress within stations (name, type, number/total)

### UI Features
- Station dots with even spacing (flex-1 distribution)
- Progress line: green (complete) → amber (to active) → gray (pending)
- Current step name displayed below stations
- Pulsing animation on active station needing input
## WS-047 Status (ADR-047 execution_state: complete)

| WS | Title | Status |
|---|---|---|
| WS-ADR-047-001 | Mechanical Operations Foundation | Complete |
| WS-ADR-047-002 | Entry Operations Implementation | Complete |
| WS-ADR-047-003 | Extraction Operations | Complete |
| WS-ADR-047-004 | Handler Refactoring | Complete |
| WS-ADR-047-005 | Concierge Intake Gate Refactoring | Complete |

---

## Workflow Architecture

### Document Creation Workflows (DCWs)
Graph-based workflows (ADR-039) for single document production:
- `concierge_intake` v1.4.0 -- Gate Profile with LLM classification + Entry confirmation
- `project_discovery` v1.8.0
- `technical_architecture` v1.0.0

### Project Orchestration Workflows (POWs)
Step-based workflows for cross-document orchestration:
- `intake_and_route` v1.0.0 -- Front-door POW (ADR-048)
- `software_product_development` v1.0.0

---

## React SPA Status

**Location:** `spa/` directory
**Served At:** `/` (root URL for all users)

### Features Complete
- All previous features
- **Building Blocks tray highlighting** (2026-02-07): Selected items show left border accent
- **Orchestration workflow display** (2026-02-07): Both POWs (intake_and_route, software_product_development) visible in left rail
- **Auto-assign workflow** (2026-02-08): Projects auto-assign `software_product_development` on creation
- **Streamlined Concierge UX** (2026-02-08): Simplified flow to Describe â†’ Confirm â†’ Done
- **Externalized intro content** (2026-02-08): Concierge intro loaded from YAML (`/content/concierge-intro.yaml`)
- **SSE interrupt fix** (2026-02-11): SSE events now emit correctly after interrupt resolution
- **Station abbreviations** (2026-02-11): Station dots use PGC/ASM/DRAFT/QA/REM/DONE labels; hidden on stabilized docs
- **State color scheme** (2026-02-11): All state colors via CSS variables; new luminance/chroma palette (steel blue â†’ amber â†’ cyan â†’ emerald)

---

## Architecture

```
combine-config/
+-- workflows/
|   +-- intake_and_route/releases/1.0.0/definition.json    # Front-door POW (ADR-048)
|   +-- software_product_development/releases/1.0.0/...    # Main delivery POW
|   +-- concierge_intake/releases/1.4.0/...                # Gate Profile DCW
|   +-- project_discovery/releases/1.8.0/...
+-- schemas/
|   +-- routing_decision/releases/1.0.0/schema.json        # ADR-048
|   +-- spawn_receipt/releases/1.0.0/schema.json           # ADR-048 lineage
|   +-- route_confirmation/releases/1.0.0/schema.json      # ADR-048 entry
|   +-- intake_classification/releases/1.0.0/...
|   +-- intake_confirmation/releases/1.0.0/...
+-- mechanical_ops/
|   +-- intake_route/releases/1.0.0/operation.yaml         # Router operation
|   +-- validate_routing_decision/releases/1.0.0/...       # Validator operation
|   +-- confirm_route/releases/1.0.0/operation.yaml        # Entry operation
|   +-- spawn_pow_instance/releases/1.0.0/operation.yaml   # Spawner operation
|   +-- intake_classification_extractor/...
|   +-- intake_invariant_pinner/...

app/api/services/mech_handlers/
+-- router.py              # RouterHandler for intake_route
+-- validator.py           # ValidatorHandler for validate_routing_decision
+-- spawner.py             # SpawnerHandler for spawn_pow_instance
+-- extractor.py
+-- entry.py               # EntryHandler (enhanced for confirm_route)
+-- invariant_pinner.py
+-- exclusion_filter.py

app/domain/workflow/nodes/
+-- intake_gate_profile.py # IntakeGateProfileExecutor for Gate Profile pattern
+-- gate.py                # Delegates to profile executor when internals present

spa/public/content/
+-- concierge-intro.yaml   # Externalized Concierge intro text (served at /content/)
```

---

## Key Technical Decisions

All previous decisions plus:

19. **Gate Profile pattern (ADR-047/WS-005)** -- Gates with internals (pass_a/LLM, extract/MECH, entry/UI, pin/MECH) replace special-case executor code
20. **Intake POW architecture (ADR-048)** -- Concierge Intake becomes its own POW that spawns follow-on workflows; complete-and-handoff model
21. **Routing as mechanical operation** -- Route selection is config-driven via RouterHandler; no LLM for routing decisions
22. **Lineage tracking** -- Spawned POW stores `spawned_from_execution_id`, `spawned_by_operation_id`; project maintains `executions[]` array
23. **Mechanical confidence (pending)** -- Derive `requires_confirmation` from ambiguous intent, multiple candidates, missing fields; no LLM self-confidence

---

## Quick Commands

```bash
# Run backend
cd ~/dev/TheCombine && source venv/bin/activate
python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

# Build SPA for production
cd spa && npm run build

# Run tests
python -m pytest tests/ -k "plan_executor" -v
```

---

## Handoff Notes

### Recent Fixes (2026-02-12)
- **WS-STATION-DATA-001 complete**: Event-driven station display with stations_declared, station_changed, internal_step events
- Added internal_step event emission for PGC phases (pass_a/entry/merge) from workflow definition internals
- Fixed station progress line colors (green → amber → gray)
- Fixed scroll behavior in all sidecars/panels (onWheel stopPropagation)
- Added spinner to Concierge confirmation button during submission
- Fixed "Answer Questions" button persisting after PGC completion (only check active stations)
- Removed hardcoded phase emissions in favor of data-driven events from workflow internals

### Previous Fixes (2026-02-11)
- Fixed SSE event emission after interrupt resolution (`get_interrupt()` moved before `resolve()`)
- Station dots now abbreviation-only; hidden on stabilized documents
- All state colors moved to CSS variables with new luminance/chroma palette
- Added missing `--state-blocked-*` and `--state-ready-*` CSS variables
- Fixed blueprint theme stabilized color (was white, now emerald)

### Previous Fixes (2026-02-09)
- Migrated workflow loading from `seed/workflows/` to `combine-config/workflows/` (commit `19ad038`)
- WorkflowRegistry now supports versioned structure (`{id}/releases/{version}/definition.json`)
- Extended `workflow.v1.json` schema to allow v2 fields (pow_class, derived_from, source_version, tags)
- Fixed naming inconsistency in software_product_development (`implementation_plan_primary`)
- Updated 16 files (8 production, 8 test) to use combine-config paths and snake_case IDs
- All 1955 tests pass (from 25 failures)

### Previous Fixes (2026-02-08)
- Fixed conversation message ordering (messages now build top-to-bottom, not bottom-to-top)
- Fixed `/start` endpoint to return full `IntakeStateResponse` for consistent UI rendering
- Added duplicate prevention when `pending_prompt` matches last assistant message
- Added `require_auth` dependency to all intake endpoints
- Fixed user fields on project creation (`created_by`, `owner_id`, `organization_id` now populated)
- Auto-assign `software_product_development` workflow on project creation
- Streamlined Concierge phases: Describe â†’ Confirm â†’ Done (removed Review/Generate)
- Renamed "Project Type" to "Intent Classification" in confirmation form
- Added "Confirmation requested" notice to entry form
- Externalized Concierge intro content to `/content/concierge-intro.yaml`
- Fixed `useConciergeIntake` hook to use `updateFromState` on start

### Earlier Fixes (2026-02-07)
- Fixed prompt ref parsing (`prompt:task:intake_gate:1.0.0` now resolves correctly)
- Fixed LLM service call signature in Gate Profile executor
- Fixed `db_session` not passed to PlanExecutor (document persistence now works)
- Fixed `intake_gate_phase` not copied to context_state on qualified outcome (UI now advances)
- Added ConciergeEntryForm rendering in ConciergeIntakeSidecar for operator confirmation
- ADR-010 instrumentation verified: prompts, messages, and JSON envelopes all logged

### Next Work
- Wire intake_and_route POW to actually execute (currently definition only)
- Integrate SpawnerHandler with ExecutionService to create actual child POW executions
- Add lineage fields to WorkflowExecution model (spawned_from_execution_id, spawned_by_operation_id)
- UX: Collapsed receipt view for completed Intake POW

### Cleanup Tasks
- Delete unused `spa/src/components/LoginPage.jsx`
- Remove Zone.Identifier files (Windows metadata)
- Consider removing `seed/workflows/` after verifying PromptAssemblyService migration
- **Remove deprecated HTMX admin section** (`app/web/routes/admin/`) -- Old admin pages (admin_routes.py, composer_routes.py, dashboard.py, documents.py, pages.py, partials.py) are superseded by React SPA AdminWorkbench; remove after confirming no active usage

### Known Issues
- None (seed/workflows sync issue resolved 2026-02-09)

### Design Decisions Deferred
- **Optional template tokens** (YAGNI): Allow `$$TOKEN?` syntax for optional tokens
