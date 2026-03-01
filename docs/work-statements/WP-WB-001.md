# WP-WB-001: Work Binder Operations

**Status:** ACCEPTED
**Created:** 2026-03-01
**Author:** Tom Moseley + Claude (collaborative design)
**WS Count:** 8

---

## Purpose

Implement the Work Binder (WB) — the operational interface where Implementation Plan candidates become governed Work Packages and Work Statements are authored, managed, and stabilized for execution.

Without a governed operational model, the WB becomes an ad-hoc project management screen and the pipeline loses determinism. The WB is a **regulated work ledger**, not a Kanban board.

---

## Locked Architectural Decisions

These decisions are final and must be followed by all WSs in this WP.

### D1: Model A — Strong Lineage
WP candidates persist as immutable lineage anchors. They are never deleted after promotion. They encode decision lineage — what the IP actually proposed vs what was promoted. Candidates are governance provenance, not UX scaffolding.

### D2: Two-Plane Versioning
WP and WS versions are independent:
- **WP version bumps** when WP-level fields change: title, rationale, scope_in, scope_out, dependencies, definition_of_done, governance_pins, transformation, source_candidate_ids, ws_index (membership + ordering), WP state.
- **WS version bumps** when WS content changes: objective, procedure, verification_criteria, prohibited_actions, allowed_paths, WS state, scope_in, scope_out.
- **WS content changes do NOT bump WP version** unless they also change WP-level fields.
- Adding/removing a WS = WP change (ws_index membership changed).
- Reordering WSs = WP change (ws_index order_key changed).
- Editing WS content = WS change only.

### D3: Three Sub-Views Per WP
Each WP section in the binder has three views:
- **WORK** (default): Live content — section header, ordered WS list, actions.
- **HISTORY**: Edition ledger — WP revisions with system-computed change summaries.
- **GOVERNANCE**: Pins, lineage, ADR/policy refs, transformation metadata. Mostly read-only.

### D4: Terminology
- **PROPOSE** (not "Generate"): LLM creates WS artifacts in DRAFT state. User must stabilize.
- **STABILIZE** (not "Save"): Real state transition from DRAFT to READY. Not auto-save.
- **PROMOTE** (not "Create"): Move candidate to governed WP. Formal act with audit trail.

### D5: Mechanical Change Summary
`change_summary[]` on WP editions is system-computed from JSON diff of WP-level fields only. No human narration required. The system computes entries like:
- "ws_index: added WS-WB-014"
- "dependencies: added must_complete_first -> wp_registry"
- "state: PLANNED -> READY"

### D6: Persistence in Existing Document Store
WPs, WSs, and WP Candidates use the existing document store (documents table). No parallel persistence plane. WP Candidates are a new doc_type_id (`work_package_candidate`).

### D7: API Plane Separation
WS endpoints cannot mutate WP fields. WP endpoints cannot mutate WS content (except ws_index membership/ordering). This is enforced at the API layer and testable.

---

## Scope

### In Scope
- WP Candidate doc type + import from IP
- WP Candidate to Governed WP promotion workflow
- WP `ws_index` field (structured membership + ordering)
- WP/WS revision metadata + edition tracking
- WP mechanical `change_summary[]`
- WB screen (view mode, not expanded node) with vertical WP index
- Per-WP sub-views: WORK / HISTORY / GOVERNANCE
- WS CRUD with plane-separated API routes
- Audit trail for all WB mutations


### Out of Scope
- Multi-tenant isolation
- Advanced graph visualization of WP dependencies
- Automated WS execution (CC handles that externally)
- Full PM suite (estimates, assignments, timelines)
- Document library / export (separate WP)
- "Propose Work Statements" LLM-assisted DRAFT creation (future WP-WB-002)
- Authentication/authorization (pre-existing concern)

---

## Dependencies

- Existing `work_package` doc type v1.0.0 (will be evolved to v1.1.0)
- Existing `work_statement` doc type v1.0.0 (will be evolved to v1.1.0)
- Existing document store (documents table, document handlers, registry)
- Existing Production Floor UI (PipelineRail + ContentPanel)
- ADR-051 (Work Package as Runtime Primitive)
- ADR-052 (Document Pipeline Integration for WP/WS)
- POL-WS-001 (Work Statement Standard)

---
## Work Statements

### WS-WB-001: Schema Evolution + Versioning Model

**Objective:** Evolve WP and WS schemas to v1.1.0 with ws_index, revision metadata, and change_summary. Create new work_package_candidate doc type.

**Depends on:** None (foundation for all other WSs)

**Scope:**
- Evolve `work_package` schema v1.0.0 -> v1.1.0:
  - Add `ws_index: [{ ws_id: string, order_key: string }]` (replaces `ws_child_refs` for ordering; `ws_child_refs` retained for backward compat)
  - Add `revision: { edition: integer, updated_at: string, updated_by: string }`
  - Add `change_summary: [string]` (system-populated per edition)
  - Ensure no contradictory states: if `governance_pins.ta_version_id` is "pending", then `ws_index` must be empty
- Evolve `work_statement` schema v1.0.0 -> v1.1.0:
  - Add `revision: { edition: integer, updated_at: string, updated_by: string }`
  - Add `order_key: string` (lexicographic, e.g., "a0", "a1", "b0")
  - Verify WS schema contains NO WP-level fields
- Create `work_package_candidate` doc type v1.0.0:
  - Schema: `{ wpc_id, title, rationale, scope_summary, source_ip_id, source_ip_version, frozen_at, frozen_by }`
  - `additionalProperties: false`
  - Immutable after creation
- Update `active_releases.json` for all three doc types
- Create `package.yaml` for `work_package_candidate`

**Allowed paths:**
- `combine-config/document_types/work_package/releases/1.1.0/`
- `combine-config/document_types/work_statement/releases/1.1.0/`
- `combine-config/document_types/work_package_candidate/`
- `combine-config/_active/active_releases.json`

**Verification:**
- All three schemas validate with JSON Schema draft-07
- `active_releases.json` references correct versions
- No `$id` collisions with existing schemas
- WP schema disallows ws_index entries when ta_version_id is "pending"

**Prohibited:**
- Modifying v1.0.0 schemas (they are immutable releases)
- Adding WP-level fields to WS schema
- Allowing `additionalProperties: true` on new doc type schemas (work_package_candidate). Evolved schemas (WP/WS v1.1.0) omit it for backward compat, consistent with v1.0.0.
---

### WS-WB-002: WP Candidate Handler + Persistence

**Objective:** Create the work_package_candidate handler and persistence layer using the existing document store.

**Depends on:** WS-WB-001

**Scope:**
- Create `WorkPackageCandidateHandler` in `app/domain/handlers/`
  - `doc_type_id = "work_package_candidate"`
  - Validate against schema
  - Reject updates (immutable after creation)
- Register handler in handler registry
- Create Tier-1 tests (create, validate, reject-update)

**Allowed paths:**
- `app/domain/handlers/work_package_candidate_handler.py`
- `app/domain/handlers/registry.py`
- `tests/tier1/handlers/test_work_package_candidate_handler.py`

**Verification:**
- Handler registered and returns correct doc_type_id
- Create succeeds with valid candidate data
- Update attempt raises validation error
- 10+ Tier-1 tests passing

**Prohibited:**
- Creating new database tables
- Making candidates mutable

---

### WS-WB-003: Candidate Import from IP

**Objective:** Extract WP candidates from a committed Implementation Plan and store as frozen work_package_candidate documents.

**Depends on:** WS-WB-002

**Scope:**
- Create import service: `app/domain/services/candidate_import_service.py`
  - Input: IP document ID + version
  - Extracts WP candidate sections from IP content
  - Creates one `work_package_candidate` document per candidate
  - Sets `frozen_at`, `frozen_by`, `source_ip_id`, `source_ip_version`
  - Returns list of created WPC IDs
- Create API endpoint: `POST /api/v1/work-binder/import-candidates`
  - Input: `{ ip_document_id: string }`
  - Returns: `{ candidates: [{ wpc_id, title }], count: integer }`
- Idempotency: re-import of same IP version does not create duplicates
- Tier-1 tests for service + API route

**Allowed paths:**
- `app/domain/services/candidate_import_service.py`
- `app/api/v1/routers/work_binder.py`
- `app/api/v1/routers/__init__.py`
- `app/api/v1/__init__.py`
- `tests/tier1/services/test_candidate_import_service.py`
- `tests/tier1/api/test_work_binder_routes.py`

**Verification:**
- Import creates expected number of candidates
- Candidates are immutable in document store
- Re-import is idempotent
- 15+ Tier-1 tests passing

**Prohibited:**
- Modifying IP documents during import
- Creating candidates outside document store

---

### WS-WB-004: Promotion Workflow (Candidate -> Governed WP)

**Objective:** Implement formal promotion of WP candidate to governed Work Package with full audit trail.

**Depends on:** WS-WB-003

**Scope:**
- Create promotion service: `app/domain/services/wp_promotion_service.py`
  - Input: WPC ID + transformation type (kept/split/merged/added) + transformation_notes
  - Creates governed `work_package` document with lineage, state PLANNED, empty ws_index, revision edition 1
  - Returns new WP document ID
- Create API endpoint: `POST /api/v1/work-binder/promote`
  - Input: `{ wpc_id, transformation, transformation_notes, title_override?, rationale_override? }`
  - Returns: `{ wp_id, document_id }`
- Audit event on every promotion
- Tier-1 tests

**Allowed paths:**
- `app/domain/services/wp_promotion_service.py`
- `app/api/v1/routers/work_binder.py`
- `tests/tier1/services/test_wp_promotion_service.py`

**Verification:**
- Promotion creates WP with correct lineage fields
- WPC remains immutable after promotion
- Audit event recorded
- Cannot promote same WPC twice (or handles gracefully)
- 15+ Tier-1 tests passing

**Prohibited:**
- Deleting or modifying source candidate
- Creating WP without transformation metadata
- Silent promotion (must have audit trail)
---

### WS-WB-005: WP Edition Tracking + Change Summary

**Objective:** Implement two-plane versioning with mechanical change_summary generation for WP editions.

**Depends on:** WS-WB-001

**Scope:**
- Create edition service: `app/domain/services/wp_edition_service.py`
  - On WP update: compare previous vs new WP-level fields
  - Increment `revision.edition`
  - Compute `change_summary[]` from JSON diff
  - WP-level fields (exhaustive): title, rationale, scope_in, scope_out, dependencies, definition_of_done, governance_pins, ws_index, state, source_candidate_ids, transformation, transformation_notes
  - Excluded: ws_child_refs (legacy), ws_total, ws_done, mode_b_count
- History data retrieval function (service-layer only; API endpoint added in WS-WB-006)
- Tier-1 tests for diff computation + edition increment

**Allowed paths:**
- `app/domain/services/wp_edition_service.py`
- `tests/tier1/services/test_wp_edition_service.py`

**Verification:**
- Edition increments only on WP-level field changes
- WS content changes do NOT increment WP edition
- change_summary accurately reflects field diffs
- Service returns editions in reverse chronological order
- 15+ Tier-1 tests passing

**Prohibited:**
- Human-narrated change summaries
- Edition bumps on non-WP-level field changes

---

### WS-WB-006: Work Statement CRUD + Plane Separation

**Objective:** Implement WS CRUD with strict API plane separation.

**Depends on:** WS-WB-001, WS-WB-005

**Scope:**
- API routes (plane-separated):
  - `POST /api/v1/work-binder/wp/{wp_id}/work-statements` -> Create WS
  - `PATCH /api/v1/work-binder/work-statements/{ws_id}` -> Update WS content only
  - `PUT /api/v1/work-binder/wp/{wp_id}/ws-index` -> Reorder WSs (WP edition bump)
  - `PATCH /api/v1/work-binder/wp/{wp_id}` -> Update WP fields only
  - `GET /api/v1/work-binder/wp/{wp_id}/work-statements` -> List WSs in order
  - `GET /api/v1/work-binder/work-statements/{ws_id}` -> Get single WS
  - `GET /api/v1/work-binder/wp/{wp_id}/history` -> WP edition history (from wp_edition_service)
- WS service: `app/domain/services/ws_crud_service.py`
  - Deterministic WS ID assignment (WS-{WP_PREFIX}-{NNN})
  - Lexicographic order key assignment
  - State transitions via existing WS state machine
- Plane separation enforcement:
  - WS PATCH rejects WP-level fields in body (400)
  - WP PATCH rejects WS content fields in body (400)
- Stabilize action: `POST /api/v1/work-binder/work-statements/{ws_id}/stabilize`
  - DRAFT -> READY transition
  - Validates all required WS fields populated
- Tier-1 tests for CRUD + plane separation

**Allowed paths:**
- `app/domain/services/ws_crud_service.py`
- `app/api/v1/routers/work_binder.py`
- `tests/tier1/services/test_ws_crud_service.py`
- `tests/tier1/api/test_work_binder_routes.py`

**Verification:**
- WS creation adds to WP ws_index and bumps WP edition
- WS content update bumps WS edition only
- WS reorder bumps WP edition only
- Plane separation enforced with 400 errors
- Stabilize validates required fields
- 25+ Tier-1 tests passing

**Prohibited:**
- WS endpoints mutating WP fields
- WP endpoints mutating WS content
- Auto-save
- WS creation without parent WP
---

### WS-WB-007: Work Binder Screen + Vertical Index

**Objective:** Implement WB as dedicated screen with vertical WP index and per-WP sub-views.

**Depends on:** WS-WB-006

**Scope:**
- WB screen as view mode:
  - URL-addressable: `/floor?view=binder` or `/binder`
  - Replaces ContentPanel when active (PipelineRail remains)
- Vertical WP Index (left panel):
  - WP tabs: `[WP-001] Title` with state sliver on left edge
  - Color-coded state markers
  - Click to select WP section
- Per-WP Content Area (center):
  - Three sub-view tabs: `[ WORK ] [ HISTORY ] [ GOVERNANCE ]`
  - WORK: Section header + ordered WS list + actions
  - HISTORY: Edition ledger with change_summary, timestamps, auth
  - GOVERNANCE: governance_pins, transformation metadata, ADR/policy refs
- WP Section Header (top of center area when WP selected):
  - "Binding Block": TA Component ID binding display (or "Unbound" warning badge)
  - Provenance Stamp: monospace top-right, e.g. `SOURCE: IP-V2 | AUTH: LLM-GEN`
- WS list in WORK view:
  - Each WS as discrete "sheet" with ID, title, state, primary action
  - Metadata footer per sheet: provenance display (`AUTH: HUMAN_OPERATOR` or `AUTH: COMBINE_GEN`)
  - Ghost row: monospace-outlined `WS-NEW: [ ENTER INTENT ]`, auto-stamps next deterministic ID on input
  - Focus Mode: active sheet shifts to `--bg-node`, non-active sheets dim during editing
  - Reorder capability (drag to reposition, no binder-ring animation)
- Actions:
  - "INSERT PACKAGE" at bottom of index (opens registration form in-place, not modal)
  - "STABILIZE STATEMENT" per WS (verb-first Boring Button)
- Principles:
  - No floating elements: all creation/editing within binder container (no modals, no popups)
  - No inferred data: if binding is null, show "Unbound" explicitly
  - Follow design system (Calm Authority, Boring Buttons, Monospace IDs)

**Allowed paths:**
- `spa/src/components/WorkBinder/`
- `spa/src/components/WorkBinder.jsx` (migrate to WorkBinder/index.jsx)
- `spa/src/components/ContentPanel.jsx` (rewire imports)
- `spa/src/components/Floor.jsx`
- `app/web/routes/`
- `tests/tier1/`

**Verification:**
- WB accessible via URL
- Vertical index shows WPs with correct state indicators
- Sub-view tabs switch correctly
- WS list renders in order with correct state
- Actions trigger correct API calls
- Design system compliance
- Mode B tests for component structure

**Prohibited:**
- Modal dialogs for creation
- Animated effects
- Auto-save or hidden state
- Breaking existing Production Floor

---

### WS-WB-008: Audit Trail + Governance Invariants

**Objective:** Comprehensive audit logging for all WB mutations with mechanical governance invariant enforcement.

**Depends on:** WS-WB-004, WS-WB-005, WS-WB-006

**Scope:**
- Audit events for every mutation type:
  - Candidate import, promotion, WP updates, WS creation, WS updates, reordering, state transitions, stabilization
- Audit storage: existing document store audit mechanism or dedicated table
- Governance invariants (mechanical enforcement):
  - Cannot create WS on WP with ta_version_id = "pending"
  - Cannot promote without transformation metadata
  - Cannot stabilize WS with missing required fields
  - Cannot delete a promoted WP candidate
  - Cannot reorder WSs on a DONE WP
  - All provenance fields (created_by, updated_by) required on writes
- Tier-1 tests for all invariants

**Allowed paths:**
- `app/domain/services/wb_audit_service.py`
- `app/api/v1/routers/work_binder.py`
- `tests/tier1/services/test_wb_audit_service.py`
- `tests/tier1/test_wb_governance_invariants.py`

**Verification:**
- Every mutation produces audit event
- Events include timestamp, auth, mutation type, before/after
- All governance invariants enforced (400/409 on violation)
- 20+ Tier-1 tests covering invariant scenarios

**Prohibited:**
- Silent mutations
- Soft enforcement (must be hard errors)
- Audit that depends on caller remembering to call it (must be automatic)
---

## Execution Order

Topological order based on dependencies:

1. **WS-WB-001** (Schema Evolution) -- no deps
2. **WS-WB-002** (Candidate Handler) -- depends on WS-WB-001
3. **WS-WB-005** (Edition Tracking) -- depends on WS-WB-001
4. **WS-WB-003** (Candidate Import) -- depends on WS-WB-002
5. **WS-WB-004** (Promotion) -- depends on WS-WB-003
6. **WS-WB-006** (WS CRUD) -- depends on WS-WB-001, WS-WB-005
7. **WS-WB-008** (Audit Trail) -- depends on WS-WB-004, WS-WB-005, WS-WB-006
8. **WS-WB-007** (WB Screen) -- depends on WS-WB-006

Parallelizable: WS-WB-002 + WS-WB-005 can run in parallel after WS-WB-001.

---

## Definition of Done

- All 8 WSs executed and verified
- WP candidates importable from IP and immutable
- Promotion workflow creates governed WPs with full lineage
- WS CRUD with strict plane separation
- Two-plane versioning with mechanical change_summary
- WB screen accessible via URL with vertical index + 3 sub-views
- Audit trail for every mutation
- Governance invariants mechanically enforced
- 120+ Tier-1 tests passing
- Zero regressions on existing test suite

---

## Governance Pins

- **ta_version_id:** Current TA version (confirmed at promotion time)
- **adr_refs:** ADR-051, ADR-052
- **policy_refs:** POL-WS-001, POL-ADR-EXEC-001