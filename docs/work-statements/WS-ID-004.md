# WS-ID-004: Eliminate derive_wp_id + generate_ws_id (Old Format)

## Status: Accepted

## Parent: WP-ID-001
## Governing ADR: ADR-055
## Depends On: WS-ID-002
## Parallelizable With: WS-ID-003

## Objective

Replace `derive_wp_id()` and old-format `generate_ws_id()` with `mint_display_id()`. Update all Work Binder routes that create WPC, WP, and WS documents to use the new identity format.

## Scope

### In Scope

- Remove `derive_wp_id()` from `wp_promotion_service.py`
- Replace old-format `generate_ws_id()` in `ws_crud_service.py` (or remove if no longer needed)
- Update `work_binder.py` — WPC import: use minted `WPC-NNN` display_id
- Update `work_binder.py` — WP promotion: use minted `WP-NNN` display_id (no format transformation)
- Update `work_binder.py` — WS proposal: use minted `WS-NNN` display_id
- Update `work_binder.py` — WS manual creation: use minted `WS-NNN` display_id
- Update existing tests that assert old ID formats
- New tests for new ID format behavior

### Out of Scope

- Plan executor document creation (WS-ID-003)
- Project creation service (WS-ID-003)
- The `display_id_service.py` module itself (WS-ID-002)

## Implementation

### Step 1: Update WPC import

**File:** `app/api/v1/routers/work_binder.py`

In `import_candidates_from_ip()` (around line 343), the WPC `instance_id` is currently set from the IP's candidate_id field (e.g., `WPC-001`). This format already matches the new standard. Verify it calls `mint_display_id()` or that the IP-sourced WPC-NNN format is preserved correctly.

If the IP provides `candidate_id: "WPC-001"`, use that directly as the display_id (it already conforms). If the IP provides a different format, mint a new one.

### Step 2: Update WP promotion

**File:** `app/api/v1/routers/work_binder.py`

In `promote_candidate()` (around line 466):

**Before:**
```python
wp_id = derive_wp_id(request.wpc_id)  # WPC-001 → wp_wb_001
```

**After:**
```python
wp_id = await mint_display_id(db, wpc_doc.space_id, "work_package")  # → WP-001
```

Update `build_promoted_wp()` call to use the new `wp_id`.

### Step 3: Update wp_promotion_service.py

**File:** `app/domain/services/wp_promotion_service.py`

- Remove `derive_wp_id()` function and `_WPC_ID_PATTERN` regex
- Update `build_promoted_wp()` to accept the pre-minted `wp_id` without transformation
- Ensure `source_candidate_ids` correctly stores the WPC display_id for lineage

### Step 4: Update WS proposal

**File:** `app/api/v1/routers/work_binder.py`

In `propose_work_statements()` (around line 662):

**Before:**
```python
ws_id = generate_ws_id(wp_id, sequence_num)  # → WS-WB-001
```

**After:**
```python
ws_id = await mint_display_id(db, wp_doc.space_id, "work_statement")  # → WS-001
```

### Step 5: Update WS manual creation

**File:** `app/api/v1/routers/work_binder.py`

In `create_work_statement()` (around line 774), use minted display_id instead of `generate_ws_id()`.

### Step 6: Update ws_crud_service.py

**File:** `app/domain/services/ws_crud_service.py`

- Remove or replace `generate_ws_id()` — it produces `WS-PREFIX-NNN` format which is eliminated
- If any other ws_crud functions reference the old ID format, update them
- Keep other ws_crud functions (build_new_ws, validate_ws_update_fields, etc.) intact

### Step 7: Update existing tests

**Files:** `tests/tier1/services/test_wp_promotion_service.py`, `tests/tier1/services/test_ws_crud_service.py`, `tests/tier1/api/test_work_binder_routes.py`

- Remove/update `TestDeriveWpId` tests (6 tests) — function is removed
- Update `TestGenerateWsId` tests (7 tests) — function is removed or replaced
- Update any tests that assert old ID formats (`wp_wb_001`, `WS-WB-001`)
- Add new tests asserting the new format (`WP-001`, `WS-001`)

## Tier-1 Tests

- WP promotion creates WP with `WP-NNN` format display_id (not `wp_wb_NNN`)
- WS proposal creates WSs with `WS-NNN` format (not `WS-PREFIX-NNN`)
- WPC import preserves `WPC-NNN` format from IP
- `source_candidate_ids` on promoted WP correctly stores WPC display_id
- Sequential minting produces incrementing WP numbers within a project
- Sequential minting produces incrementing WS numbers within a project
- Old functions `derive_wp_id` and `generate_ws_id` no longer exist (import check)

## Allowed Paths

```
app/api/v1/routers/work_binder.py
app/domain/services/wp_promotion_service.py
app/domain/services/ws_crud_service.py
tests/tier1/services/test_wp_promotion_service.py
tests/tier1/services/test_ws_crud_service.py
tests/tier1/api/test_work_binder_routes.py
```

## Prohibited

- Do not modify plan_executor.py (WS-ID-003)
- Do not modify project_creation_service.py (WS-ID-003)
- Do not modify display_id_service.py (WS-ID-002)
- Do not delete any test files (update tests, don't remove coverage)
- Do not change WPC or WP schema definitions

## Verification

- All Work Binder operations produce `{TYPE}-{NNN}` format IDs
- No references to `derive_wp_id` or old `generate_ws_id` remain in production code
- All existing test assertions updated to new format
- All tests pass
