# PROJECT_STATE.md

**Last Updated:** 2026-02-18
**Updated By:** Claude (ADR-050 protocol prove-out, HTMX admin removal)

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
- `implementation_plan_primary` v1.0.0 -- PGC + generation + QA; requires project_discovery
- `implementation_plan` v1.0.0 -- QA-only; requires primary_implementation_plan + technical_architecture

### Project Orchestration Workflows (POWs)
Step-based workflows for cross-document orchestration:
- `intake_and_route` v1.0.0 -- Front-door POW (ADR-048)
- `software_product_development` v1.0.0

---

## IPF Schema v2 (Implementation Plan Final)

Schema upgraded with candidate reconciliation for IPP-to-IPF traceability.

### Key Structures
- `candidate_reconciliation[]` -- Audit-friendly mapping of every IPP candidate to its outcome (kept/split/merged/dropped)
- `source_candidate_ids[]` + `transformation` on each Epic -- Reverse linkage from committed Epic to IPP candidates
- `meta` block -- Provenance metadata matching IPP/PD pattern
- EC- pattern enforcement on all candidate ID references
- `additionalProperties: false` at all levels
- `risk_summary` mechanically derived from per-epic risks in handler `transform()` (LLM no longer generates it)

### Files
- Canonical schema: `combine-config/schemas/implementation_plan/releases/1.0.0/schema.json`
- Task prompt: `combine-config/prompts/tasks/implementation_plan/releases/1.0.0/task.prompt.txt`
- Active release: `implementation_plan: "1.0.0"` in tasks section

---

## BacklogItem v1 Schema

Unified backlog item with level discriminator and level-specific details.

### Key Structures
- Base fields (compiler-owned, hash-included): `id`, `level`, `parent_id`, `depends_on[]`, `priority_score`
- Human fields (hash-excluded): `title`, `summary`
- Level-specific `details` via allOf/if/then: `EpicDetails`, `FeatureDetails`, `StoryDetails`, `TaskDetails`
- Lineage fields (hash-excluded): `created_by_run_id`, `parent_execution_id`, `source_refs`, `transformation`, `inherited_flags`
- ID pattern: `^[EFST]\d{3}$` (E=Epic, F=Feature, S=Story, T=Task)
- Parent_id pattern enforcement per level (FEATURE→Epic, STORY→Feature, TASK→Story)
- `boundary_uncertain` flag on FeatureDetails for ambiguous epic boundary placement

### Hash Boundary Invariant
`backlog_hash` computed exclusively from base fields. Editing title, summary, details, or lineage does NOT invalidate execution plan.

### Files
- Canonical schema: `combine-config/schemas/backlog_item/releases/1.0.0/schema.json`
- List schema: `combine-config/schemas/backlog_item/releases/1.0.0/list.schema.json`
- Output schema: `combine-config/document_types/backlog_item/releases/1.0.0/schemas/output.schema.json`
- Task prompt: `combine-config/prompts/tasks/backlog_generator/releases/1.0.0/task.prompt.txt`

---

## Backlog Compilation Pipeline (BCP)

### Delivered (WS-BCP-001 through WS-BCP-004)
- Graph validation: dependency, hierarchy, cycle detection
- Deterministic ordering: topological sort with priority tiebreak, wave computation
- Backlog hash: structural hash from base fields only
- Execution plan derivation
- Pipeline orchestration: load intent → generate → validate → derive → explain → persist
- Pipeline run metadata with replay hashes (intent_hash, backlog_hash, plan_hash, source_hash)

### Design: Progressive Expansion Model (v1.3)
Design doc: `docs/implementation-plans/PROJECT-BACKLOG-COMPILATION-POW-Design-v1.2.md` (content is v1.3)

Replaces v1.2 monolithic pipeline phases with discrete UI-triggered fan-out POWs:
- `EpicFeatureFanoutPOW` -- UI button per epic, sibling boundary summary as context
- `FeatureStoryFanoutPOW` -- UI button per epic or feature
- Plan compilation: operator-triggered with nudge banner
- Coverage audit: moved into IPF DCW pre-acceptance
- Staleness: `source_hash` on pipeline_run records, deterministic detection
- Reconciliation: ID-only match, UI confirmation before applying drops

### Pending (WS-BCP-005)
- EpicFeatureFanoutPOW and FeatureStoryFanoutPOW implementation
- UI buttons: Generate Features, Generate Stories, Compile Plan
- Staleness detection + expansion state badges
- Reconciliation with UI confirmation modal
- Plan compile nudge banner

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
- **Document headers** (2026-02-13): All full document views show project badge (links to admin execution), doc type, lifecycle state, version, title, generation date
- **Project Discovery visualization** (2026-02-13): stakeholder_questions, early_decision_points, and risks sections now render
- **Execution admin links** (2026-02-13): Project badge links to correct execution (3-step lookup preferring completed executions)
- **L2 document viewing** (2026-02-16): Epic nodes on production floor now show "View Document" button; opens FullDocumentViewer with instance_id disambiguation

---

## Architecture

```
combine-config/
+-- workflows/
|   +-- intake_and_route/releases/1.0.0/definition.json    # Front-door POW (ADR-048)
|   +-- software_product_development/releases/1.0.0/...    # Main delivery POW
|   +-- concierge_intake/releases/1.4.0/...                # Gate Profile DCW
|   +-- project_discovery/releases/1.8.0/...
|   +-- implementation_plan_primary/releases/1.0.0/...     # IPP DCW (PGC + gen + QA)
|   +-- implementation_plan/releases/1.0.0/...             # IPF DCW (QA-only)
+-- schemas/
|   +-- implementation_plan/releases/1.0.0/schema.json     # IPF v2 with reconciliation
|   +-- primary_implementation_plan/releases/1.0.0/...     # IPP with epic_candidates
|   +-- routing_decision/releases/1.0.0/schema.json        # ADR-048
|   +-- spawn_receipt/releases/1.0.0/schema.json           # ADR-048 lineage
|   +-- route_confirmation/releases/1.0.0/schema.json      # ADR-048 entry
|   +-- intake_classification/releases/1.0.0/...
|   +-- intake_confirmation/releases/1.0.0/...
+-- prompts/tasks/
|   +-- implementation_plan/releases/1.0.0/...             # IPF task prompt (governance)
|   +-- primary_implementation_plan/releases/1.0.0/...     # IPP task prompt
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
24. **IPF candidate reconciliation** -- Bidirectional traceability between IPP epic candidates and committed Epics; every candidate must be explicitly accounted for

---

## Quick Commands

```bash
# Run backend
cd ~/dev/TheCombine && source venv/bin/activate
python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

# Build SPA for production
cd spa && npm run build

# Run tests
python -m pytest tests/ -x -q
```

---

## ADR-050 Verification Status

| WS | Title | Status |
|---|---|---|
| WS-ADR-050-001 | Tier 0 Verification Harness | Complete |
| WS-ADR-050-002 | Protocol Prove-Out (HTMX admin removal) | Complete |

Tier 0 harness: `ops/scripts/tier0.sh`
Mode B debt: typecheck (mypy not installed)

---

## Handoff Notes

### Recent Work (2026-02-18)
- **WS-ADR-050-001**: Tier 0 verification harness implemented and hardened (pytest, ruff lint, mypy type check, SPA build, scope validation)
- **WS-ADR-050-002**: Full ADR-050 protocol prove-out — removed deprecated HTMX admin section (40 files deleted, 8,099 lines removed)
- **Intent-first testing**: 10 Tier 1 tests written before implementation, all pass after
- **Tier 0 hardening**: Mode B enforcement, CI guard, machine-readable JSON, frontend auto-detection, deleted file handling
- **main.py lint cleanup**: Removed unused imports (`RedirectResponse`, `Jinja2Templates`, `auth`), added `# noqa: E402` for `load_dotenv()` pattern

### Recent Work (2026-02-16, Session 2)
- **BacklogItem v1 schema**: Level-specific details, TASK level, lineage, hash boundary invariant, boundary_uncertain flag
- **Mechanical risk_summary**: IPF handler derives risk_summary from per-epic risks; LLM no longer self-aggregates
- **Progressive expansion model (v1.3)**: Monolithic pipeline phases replaced by discrete fan-out POWs
- **source_hash staleness**: Pipeline run records include source_hash for deterministic staleness detection
- **Design decisions locked**: Story dep scope, reconciliation UI, compile trigger, sibling boundary summary

### Previous Work (2026-02-16, Session 1)
- **L2 document viewing**: Epic nodes on production floor now viewable via "View Document" button
- Backend `instance_id` query param on document endpoints for multi-instance disambiguation
- SPA carries `docTypeId`/`instanceId` through transformer -> nodes -> Floor -> FullDocumentViewer -> API client

### Previous Work (2026-02-13, Session 3)
- **IPF schema v2**: Added `candidate_reconciliation[]`, `source_candidate_ids[]` + `transformation` on epics, `meta` block, EC- pattern enforcement
- **IPF task prompt rewritten**: 10 traceability rules, 5 referential consistency constraints, explicit failure conditions
- **Standalone task prompt created**: `prompt:task:implementation_plan:1.0.0` URN now resolves at runtime
- **Document headers**: All document views show project badge, doc type, lifecycle state, version, dates
- **Project Discovery gaps filled**: stakeholder_questions, early_decision_points, risks now visualized
- **Execution admin links**: Project badge links to correct execution with 3-step lookup

### Previous Work (2026-02-13, Sessions 1-2)
- **WorkflowBlockV2**: React Flow graph diagrams for architecture workflows
- **WS-WORKFLOW-STUDIO-001**: Technical Architecture viewer with 6 tabs
- **Implementation Plan Primary DCW**: Full PGC + generation + QA workflow

### Next Work
- **WS-BCP-005**: Progressive Expansion Workflows (EpicFeatureFanoutPOW, FeatureStoryFanoutPOW, UI buttons, staleness, reconciliation)
- Coverage audit pass within IPF DCW (pre-acceptance)
- Epic render_model support (currently falls back to raw JSON in FullDocumentViewer)
- SPA block renderer for `candidate_reconciliation` section
- First live IPF execution to validate prompt/schema against real LLM output
- Wire intake_and_route POW to actually execute
- UX: Collapsed receipt view for completed Intake POW

### Cleanup Tasks
- Delete unused `spa/src/components/LoginPage.jsx`
- Remove Zone.Identifier files (Windows metadata)
- ~~Remove deprecated HTMX admin section~~ (Complete — WS-ADR-050-002)
- Sync IPP task prompt field names with IPP schema field names (epic_id->candidate_id, title->name)

### Verification Debt (ADR-050 Mode B)
- **Type check (mypy)**: Not installed. Tier 0 FAILS without `--allow-missing typecheck`. Mechanization plan: install and configure mypy, remove --allow-missing flag.

### Known Issues
- Two copies of BacklogItem schema must be kept in sync (`schemas/` and `document_types/`)
- Two copies of IPF task prompt must be kept in sync (`prompts/tasks/` and `document_types/`)
- Two copies of IPF schema must be kept in sync (`schemas/` and `document_types/`)
- IPP task prompt field names don't match IPP schema (prompt says epic_id/title/description, schema uses candidate_id/name/intent)
- Design doc file named `v1.2.md` but content is v1.3 (rename on next touch)
- BacklogItem ID pattern `^[EFST]\d{3}$` limits to 999 items per level (future migration tax)
