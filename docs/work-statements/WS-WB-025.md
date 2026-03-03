# WS-WB-025: IA Contract Alignment — WorkBinder Frontend-to-API

## Status: Draft

## Parent: WP-WB-002

## Governing References

- ADR-054 -- Governed Information Architecture
- WP-WB-001 -- Work Binder Work Package
- WP-WB-002 -- Work Binder Phase 2

## Verification Mode: A

## Allowed Paths

- app/api/v1/routers/work_binder.py
- spa/src/components/WorkBinder/WorkView.jsx
- spa/src/components/WorkBinder/WPContentArea.jsx
- spa/src/components/WorkBinder/WorkBinder.css
- tests/tier1/api/test_work_binder_routes.py
- tests/tier1/services/test_ws_proposal_service.py

---

## Objective

Resolve all mismatches found in the 2026-03-03 IA Verification Audit between
the JSON schemas (source of truth), the API Pydantic models/endpoints, and the
SPA frontend components for the Work Statement, Work Package, and Work Package
Candidate document types in the WorkBinder UI.

Two findings are CRITICAL (runtime failures); the remaining are HIGH/MEDIUM
drift that will compound if left unaddressed.

---

## Preconditions

- IA Verification Audit completed 2026-03-03 (10 findings, 2 CRITICAL)
- All 2247 Tier-1 tests passing
- SPA build passing
- WS rendering pipeline operational (revision normalization fix applied)

---

## Scope

### In Scope

1. **CRITICAL #1** -- Reorder endpoint contract mismatch: frontend sends
   `{ ws_ids: [...] }` but API expects `{ ws_index: [{ws_id, order_key}] }`.
   Fix the frontend to build the correct shape from the WSResponse order_key
   values already in client state.

2. **CRITICAL #2** -- Ghost row create sends `{ intent: "..." }` but
   `CreateWSRequest` has no `intent` field (Pydantic silently drops it,
   creating blank WSs). Fix the frontend to send `{ title: intent }` so
   the WS gets a visible title.

3. **HIGH #3** -- WS state enum drift: frontend has `STABILIZED` and
   `COMPLETE` (not in schema); missing `ACCEPTED` and `REJECTED` (in schema).
   Align frontend STATE_BADGE map to schema enum:
   `DRAFT, READY, IN_PROGRESS, ACCEPTED, REJECTED, BLOCKED`.

4. **MEDIUM #5** -- `WPCDetail` model missing schema-required fields
   `source_ip_version` and `frozen_by`. Add both to the Pydantic model
   and populate from document content in the GET /candidates endpoint.

5. **MEDIUM #8** -- `BindingBlock` in WPContentArea reads
   `wp.ta_component_id` / `wp.binding?.component_id` which don't exist
   in the schema. Replace with `wp.governance_pins?.ta_version_id` which
   is an actual schema field and already in the WP detail response.

6. **MEDIUM #7** -- `ProvenanceStamp` reads `wp.provenance?.source` and
   `wp.provenance?.authorization` which are not in the WP schema. Replace
   with `wp.transformation` and `wp.source_candidate_ids` which are actual
   schema fields available in the WP detail response.

7. **LOW #9** -- `formatWsId` fallbacks to non-existent `ws.code` and
   `ws.sequence`. Remove dead fallback paths; use `ws.ws_id` only.

### Out of Scope

- #4 (WP list model `Optional` vs required) -- lives in `projects.py`,
  not a WorkBinder file. Requires separate WS.
- #6 (WSResponse missing `_lineage`) -- `_lineage` is internal metadata;
  exposing it requires an architectural decision on what to surface.
- #10 (revision/order_key not rendered in frontend) -- not a bug; data is
  available if needed. No action required.
- Changes to any JSON schema files
- Changes to the promote, import, or propose endpoints
- Backend reorder logic (only frontend payload shape changes)

---

## Tier 1 Verification Criteria

All new Tier-1 tests must fail before implementation and pass after.

1. **Reorder payload shape**: Test that `ReorderWSRequest` accepts the
   `ws_index` format with `{ws_id, order_key}` dicts (existing). Add a
   test that Pydantic rejects a payload with `ws_ids` (string array)
   to confirm the contract.

2. **Create WS with title**: Test that `CreateWSRequest(title="My Title")`
   produces a model with `title == "My Title"`. Test that a payload with
   only `intent` field results in empty title (documents the pre-fix
   behavior as a regression test).

3. **State badge coverage**: Test (in-frontend or unit) that every schema
   enum value (`DRAFT`, `READY`, `IN_PROGRESS`, `ACCEPTED`, `REJECTED`,
   `BLOCKED`) has a corresponding STATE_BADGE entry.

4. **WPCDetail includes source_ip_version and frozen_by**: Test that
   `WPCDetail` model accepts and exposes both fields.

5. **Reorder sends correct shape from frontend**: After fix, the
   `reorderWorkStatements()` function must send
   `{ ws_index: [{ws_id, order_key}, ...] }`.

6. **Ghost row sends title**: After fix, `createWorkStatement()` must
   send `{ title: intent }` not `{ intent }`.

7. **BindingBlock renders governance_pins.ta_version_id**: After fix,
   binding block shows the TA version ID from governance_pins.

8. **ProvenanceStamp renders transformation + lineage**: After fix,
   provenance stamp shows transformation type and source candidate IDs.

9. **formatWsId uses only ws_id**: After fix, function returns
   `ws.ws_id` with no fallback to non-existent fields.

---

## Procedure

### Phase 1: Write Failing Tests

Write tests for criteria 1-4 (backend testable). Verify all fail.

**1a.** In `test_work_binder_routes.py`, add `TestReorderWSRequestValidation`:
- Test that `ReorderWSRequest(ws_index=[{"ws_id": "WS-1", "order_key": "a0"}])`
  succeeds.
- Test that constructing `ReorderWSRequest` with `{"ws_ids": ["WS-1"]}`
  raises `ValidationError` (no `ws_index` field).

**1b.** In `test_work_binder_routes.py`, add `TestCreateWSIntentRegression`:
- Test that `CreateWSRequest(title="Build logger")` has `title == "Build logger"`.
- Test that `CreateWSRequest(**{"intent": "Build logger"})` has `title == ""`
  (Pydantic ignores unknown field).

**1c.** In `test_work_binder_routes.py`, add `TestWPCDetailSchemaFields`:
- Test that `WPCDetail(wpc_id="WPC-001", title="T", source_ip_version="1.0.0", frozen_by="system")`
  succeeds and both new fields are accessible.

Run tests. Criteria 1a and 1b should pass (documenting current behavior).
Criterion 1c should FAIL (fields don't exist yet on the model).

### Phase 2: Implement

**Step 1 -- Fix reorder payload (CRITICAL #1)**

In `WorkView.jsx`, change `reorderWorkStatements()`:

Before:
```javascript
body: JSON.stringify({ ws_ids: wsIds })
```

After:
```javascript
body: JSON.stringify({
    ws_index: wsIds.map(id => {
        const ws = statements.find(s => s.ws_id === id);
        return { ws_id: id, order_key: ws?.order_key || '' };
    })
})
```

This requires passing `statements` into the reorder function or restructuring
`handleMove` to build the correct shape from existing state.

**Step 2 -- Fix ghost row create (CRITICAL #2)**

In `WorkView.jsx`, change `createWorkStatement()`:

Before:
```javascript
body: JSON.stringify({ intent })
```

After:
```javascript
body: JSON.stringify({ title: intent })
```

**Step 3 -- Align WS state enum (HIGH #3)**

In `WorkView.jsx`, replace `STATE_BADGE` map:

```javascript
const STATE_BADGE = {
    DRAFT:       { label: 'DRAFT',       cssVar: '--state-ready-bg' },
    READY:       { label: 'READY',       cssVar: '--state-stabilized-bg' },
    IN_PROGRESS: { label: 'IN PROGRESS', cssVar: '--state-active-bg' },
    ACCEPTED:    { label: 'ACCEPTED',    cssVar: '--state-stabilized-bg' },
    REJECTED:    { label: 'REJECTED',    cssVar: '--state-blocked-bg' },
    BLOCKED:     { label: 'BLOCKED',     cssVar: '--state-blocked-bg' },
};
```

Remove `STABILIZED` and `COMPLETE` (not in schema enum).
Add `ACCEPTED` and `REJECTED` (in schema enum).

Also update the stabilize button guard to check schema states:

Before:
```javascript
ws.state !== 'READY' && ws.state !== 'STABILIZED' && ws.state !== 'COMPLETE'
```

After:
```javascript
ws.state === 'DRAFT'
```

(Only DRAFT WSs can be stabilized.)

**Step 4 -- Add missing WPCDetail fields (MEDIUM #5)**

In `work_binder.py`, update `WPCDetail`:

```python
class WPCDetail(BaseModel):
    wpc_id: str
    title: str
    rationale: str = ""
    scope_summary: list[str] = Field(default_factory=list)
    source_ip_id: str = ""
    source_ip_version: str = ""
    frozen_at: str = ""
    frozen_by: str = ""
    promoted: bool = False
```

In the GET /candidates endpoint, populate both fields from `content`.

**Step 5 -- Fix BindingBlock (MEDIUM #8)**

In `WPContentArea.jsx`, replace `BindingBlock`:

Before:
```javascript
const componentId = wp.ta_component_id || wp.binding?.component_id || null;
```

After:
```javascript
const taVersionId = wp.governance_pins?.ta_version_id || null;
```

Render `taVersionId` instead of `componentId`.

**Step 6 -- Fix ProvenanceStamp (MEDIUM #7)**

In `WPContentArea.jsx`, replace `ProvenanceStamp`:

Before:
```javascript
const source = wp.provenance?.source || wp.source || 'UNKNOWN';
const auth = wp.provenance?.authorization || wp.authorization || 'UNKNOWN';
```

After:
```javascript
const transformation = wp.transformation || null;
const sourceIds = wp.source_candidate_ids || [];
```

Display transformation type and source candidate IDs (actual schema fields).

**Step 7 -- Clean up formatWsId (LOW #9)**

In `WorkView.jsx`, simplify:

Before:
```javascript
return ws.ws_id || ws.code || `WS-${String(ws.sequence || '???').padStart(3, '0')}`;
```

After:
```javascript
return ws.ws_id || 'WS-???';
```

### Phase 3: Verify

1. All Tier-1 tests pass (existing + new)
2. SPA build passes (`cd spa && npm run build`)
3. No new lint warnings

---

## Prohibited Actions

- Do not modify any JSON schema files in `combine-config/`
- Do not modify the backend reorder endpoint logic (`reorder_work_statements()`)
- Do not modify the promote, import, or propose endpoint implementations
- Do not modify `projects.py` (WP list endpoint lives there -- separate WS)
- Do not add new npm dependencies
- Do not remove the `ReorderWSRequest` model or change its field name
  (the API contract is correct; the frontend must conform to it)

---

## Verification Checklist

- [ ] All new Tier-1 tests fail before implementation
- [ ] Reorder sends `{ ws_index: [{ws_id, order_key}] }` (CRITICAL #1 fixed)
- [ ] Ghost row sends `{ title: intent }` (CRITICAL #2 fixed)
- [ ] STATE_BADGE matches schema enum exactly (HIGH #3 fixed)
- [ ] STABILIZED and COMPLETE removed from STATE_BADGE
- [ ] ACCEPTED and REJECTED added to STATE_BADGE
- [ ] WPCDetail has source_ip_version and frozen_by fields (MEDIUM #5 fixed)
- [ ] BindingBlock reads governance_pins.ta_version_id (MEDIUM #8 fixed)
- [ ] ProvenanceStamp reads transformation + source_candidate_ids (MEDIUM #7 fixed)
- [ ] formatWsId uses ws_id only, no dead fallbacks (LOW #9 fixed)
- [ ] All new Tier-1 tests pass after implementation
- [ ] All existing Tier-1 tests pass (no regressions)
- [ ] SPA build passes

---

_End of WS-WB-025_
