# WS-WB-040: WP-Level Stabilization (Replace Per-WS Stabilize)

## Status: Draft

## Purpose

Per-WS "Stabilize Statement" buttons fragment the governance model. A Work Package is the atomic unit of commitment — either the package is reviewed and ready for execution, or it isn't. Stabilizing WSs individually creates an inconsistent state where WP-003 has 2 stabilized and 1 draft WS, which is a governance gap.

This WS replaces the per-WS stabilize action with a single WP-level "Stabilize Package" button that atomically transitions all DRAFT WSs to READY.

**Design principle:** Promotion commits the *what* (human selects which work matters). Stabilization commits the *how* (human confirms the package's statements are reviewed and ready for execution). Both are explicit human actions, but stabilization is a commit-style action, not a per-item gate.

## Governing References

- POL-WS-001: Work Statement Standard
- ADR-009: Project Audit (all state changes explicit and traceable)
- ADR-049: No Black Boxes (mechanical ops must be explicit)
- Existing: `stabilize_work_statement()` in `app/api/v1/routers/work_binder.py` (line 1170)
- Existing: `WSDetailView.jsx` per-WS stabilize button (line 166)
- Existing: `WorkView.jsx` WP overview with WS summary cards

## Scope

### In Scope

- New backend endpoint: `POST /work-binder/wp/{wp_id}/stabilize` — atomically stabilizes all DRAFT WSs under the WP
- WP-level "Stabilize Package" button in `WorkView.jsx` (visible when WP has DRAFT statements)
- Remove per-WS "Stabilize Statement" button from `WSDetailView.jsx`
- Audit trail: single `wp_stabilized` event covering all WSs transitioned
- Validation: all WSs must pass `validate_stabilization()` before any are transitioned (all-or-nothing)

### Out of Scope

- Automatic stabilization (no-button) — keeping the review window between promotion and execution
- WP state machine changes (WP-level state is a separate concern)
- Changes to the per-WS `stabilize` endpoint (keep it for programmatic/API use, just remove the UI button)
- WS editing/authoring UI (future work)

## Preconditions

1. Work Binder Studio Layout (WS-WB-030) is complete — WP Index, WorkView, WSDetailView exist
2. Per-WS stabilize endpoint exists and works (`POST /work-binder/work-statements/{ws_id}/stabilize`)
3. `validate_stabilization()` and `validate_ws_transition()` helpers exist in `work_binder.py`

---

## Phase 1: Backend — WP-Level Stabilize Endpoint

**Objective:** Add `POST /work-binder/wp/{wp_id}/stabilize` that atomically stabilizes all DRAFT WSs.

### Step 1.1: Add endpoint to `work_binder.py`

**File:** `app/api/v1/routers/work_binder.py`

Add new endpoint after the existing per-WS stabilize endpoint (~line 1235):

```python
@router.post(
    "/wp/{wp_id}/stabilize",
    summary="Stabilize all DRAFT work statements in a Work Package",
)
async def stabilize_work_package(
    wp_id: str,
    db: AsyncSession = Depends(get_db),
    project_id: str | None = Query(None, description="Project scope"),
):
    """Atomically stabilize all DRAFT WSs under a WP.

    Validates all WSs first. If any fail validation, none are transitioned.
    Returns the list of stabilized WS IDs.
    """
```

Logic:
1. Load WP document via `_load_wp_document(db, wp_id, space_id=space_id)`
2. Load all WSs under the WP (same query as `list_work_statements`)
3. Filter to DRAFT-state WSs only
4. If no DRAFT WSs, return 400 with `"No DRAFT statements to stabilize"`
5. Run `validate_stabilization()` on each DRAFT WS — collect errors per WS
6. If any WS fails validation, return 400 with `{ error_code: "STABILIZATION_FAILED", errors: { ws_id: [errors] } }`
7. Transition all DRAFT WSs to READY (increment revision, set state)
8. Flush once (single DB round-trip)
9. Log single `wp_stabilized` audit event with list of WS IDs transitioned
10. Return `{ wp_id, stabilized: [ws_id_1, ws_id_2, ...], count: N }`

### Step 1.2: Write Tier-1 test

**File:** `tests/tier1/api/test_work_binder_stabilize_wp.py`

Test cases:
- Happy path: 3 DRAFT WSs all pass validation → all become READY
- Mixed states: 2 DRAFT + 1 READY → only the 2 DRAFT are transitioned
- Validation failure: 1 of 3 DRAFT WSs fails → none are transitioned (atomicity)
- No DRAFT WSs: all already READY → 400 error
- Empty WP: no WSs at all → 400 error

### Verification

- `pytest tests/tier1/api/test_work_binder_stabilize_wp.py -v` passes
- Manual: `curl -X POST /api/v1/work-binder/wp/WP-001/stabilize?project_id=...` transitions all DRAFT WSs

---

## Phase 2: Frontend — WP-Level Stabilize Button

**Objective:** Add "Stabilize Package" button to WorkView, remove per-WS stabilize from WSDetailView.

### Step 2.1: Add `stabilizeWorkPackage()` to `wsUtils.js`

**File:** `spa/src/components/WorkBinder/wsUtils.js`

```javascript
export async function stabilizeWorkPackage(wpId, projectId = null) {
    const qs = projectId ? `?project_id=${encodeURIComponent(projectId)}` : '';
    const res = await fetch(`/api/v1/work-binder/wp/${encodeURIComponent(wpId)}/stabilize${qs}`, {
        method: 'POST',
    });
    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail?.message || body.detail || `Stabilize failed: ${res.status}`);
    }
    return res.json();
}
```

### Step 2.2: Add "Stabilize Package" button to `WorkView.jsx`

**File:** `spa/src/components/WorkBinder/WorkView.jsx`

Add button in the WS list area, visible when:
- `statements.length > 0`
- At least one statement has `state === 'DRAFT'`

Button text: `STABILIZE PACKAGE` (or `STABILIZING...` while in progress).
Position: Below the WS summary cards, above the ghost row.

On click: call `onStabilizePackage(wpContentId)` (new prop).
On success: reload statements.
On error: show inline error.

### Step 2.3: Remove per-WS stabilize button from `WSDetailView.jsx`

**File:** `spa/src/components/WorkBinder/WSDetailView.jsx`

Remove the `STABILIZE STATEMENT` button block (lines 166-173):
```jsx
{ws.state === 'DRAFT' && (
    <button className="wb-btn wb-btn--primary wb-btn--sm" onClick={() => onStabilize(ws.ws_id)}>
        STABILIZE STATEMENT
    </button>
)}
```

Remove `onStabilize` from the component's props.

### Step 2.4: Wire up in orchestrator (`index.jsx`)

**File:** `spa/src/components/WorkBinder/index.jsx`

- Add `handleStabilizePackage` callback (calls `stabilizeWorkPackage` from wsUtils, then `loadStatements`)
- Pass `onStabilizePackage` to `WPContentArea` → `WorkView`
- Remove `onStabilize` prop from `WPContentArea` → `WSDetailView` chain (or keep but unused)

### Step 2.5: Clean up unused per-WS stabilize wiring

**Files:** `index.jsx`, `WPContentArea.jsx`

- Remove `handleStabilize` callback from `index.jsx` (or keep for API-only use)
- Remove `onStabilize` prop from `WPContentArea` and `WSDetailView`
- Keep `stabilizeWorkStatement()` in `wsUtils.js` (still useful for programmatic/test use)

### Verification

- SPA builds without errors (`cd spa && npm run build`)
- WorkView shows "STABILIZE PACKAGE" when DRAFT WSs exist
- WorkView hides button when all WSs are READY
- Clicking "STABILIZE PACKAGE" transitions all DRAFT WSs atomically
- WSDetailView no longer shows per-WS stabilize button
- WP Index WS rows update their badges after stabilization

---

## Allowed Paths

- `app/api/v1/routers/work_binder.py`
- `spa/src/components/WorkBinder/WorkView.jsx`
- `spa/src/components/WorkBinder/WSDetailView.jsx`
- `spa/src/components/WorkBinder/WPContentArea.jsx`
- `spa/src/components/WorkBinder/index.jsx`
- `spa/src/components/WorkBinder/wsUtils.js`
- `tests/tier1/api/test_work_binder_stabilize_wp.py` (new)

## Prohibited Actions

- Do not remove the per-WS `/work-statements/{ws_id}/stabilize` endpoint (keep for API use)
- Do not add automatic stabilization (no-button path) — this WS preserves the human review window
- Do not modify WP state machine or WP-level state fields
- Do not modify PipelineRail, Floor, or production floor components
- Do not add new npm dependencies
