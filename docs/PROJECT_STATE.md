# PROJECT_STATE.md

**Last Updated:** 2026-02-15
**Updated By:** Claude (Technical Architecture Viewer enhancements)

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
- `intake_and_route` POW with DCW -> route -> validate -> spawn steps
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
- Progress line: green (complete) -> amber (to active) -> gray (pending)
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
- **Streamlined Concierge UX** (2026-02-08): Simplified flow to Describe -> Confirm -> Done
- **Externalized intro content** (2026-02-08): Concierge intro loaded from YAML (`/content/concierge-intro.yaml`)
- **SSE interrupt fix** (2026-02-11): SSE events now emit correctly after interrupt resolution
- **Station abbreviations** (2026-02-11): Station dots use PGC/ASM/DRAFT/QA/REM/DONE labels; hidden on stabilized docs
- **State color scheme** (2026-02-11): All state colors via CSS variables; new luminance/chroma palette (steel blue -> amber -> cyan -> emerald)
- **WorkflowBlockV2** (2026-02-13): React Flow graph diagrams for architecture workflows; V1 steps auto-converted to linear node chains; supports branching, gates, error paths, retry loops, parallel rails

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

### Recent Work (2026-02-15)
- **WS-WORKFLOW-STUDIO-001 Complete**: Technical Architecture viewer with tabbed interface
- **6 tabs**: Overview, Components, Workflows, Data Models, APIs, Quality Attributes
- **Workflow nodes**: Now show component/output fields (fixed V1->V2 property spread)
- **Direct document view**: "View Document" skips sidecar, goes straight to full modal
- **PGC clarifications**: Section added to Overview tab

### Active Investigation: Document Rendering Issues
The Technical Architecture viewer tabs (Data Models, APIs, Quality) may not display for all projects. Tracking:

1. **Section ID mismatches**: Docdef uses singular forms (`data_model`, `interfaces`) while LLM output may use plural (`data_models`, `api_interfaces`). Viewer now matches both variants.

2. **RenderModel generation**: Need to verify that sections are correctly extracted from document content during rendermodel generation. The tabs only appear if `renderModel.sections` contains matching section_ids.

3. **PGC field names**: The PGC context API returns clarifications with potentially different field names (`question` vs `text`, `answer` vs `user_answer`). Need to verify field mapping in PgcClarificationItem component.

**Next steps to debug:**
- Check browser Network tab for rendermodel response structure
- Verify document JSON has data_models/api_interfaces/quality_attributes at expected paths
- Check docdef source_pointer values match actual document structure

### Previous Work (2026-02-13)
- **WorkflowBlockV2**: React Flow graph diagrams for architecture workflows
- V1 steps auto-converted to linear node chains
- Supports branching, gates, error paths, retry loops

### Next Work
- Debug rendermodel generation for Technical Architecture sections
- Wire intake_and_route POW to actually execute
- UX: Collapsed receipt view for completed Intake POW

### Cleanup Tasks
- Delete unused `spa/src/components/LoginPage.jsx`
- Remove Zone.Identifier files (Windows metadata)
- **Remove deprecated HTMX admin section** (`app/web/routes/admin/`)

### Known Issues
- Technical Architecture tabs (Data Models, APIs, Quality) not appearing for some projects - under investigation
