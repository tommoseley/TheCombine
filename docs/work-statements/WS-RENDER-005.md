# WS-RENDER-005: Include Work Statements in Binder Export

**Parent:** Rendering pipeline
**Depends on:** WS-RENDER-002 (complete — project binder assembly), WP-ID-001 (complete — display_id on all documents)
**Blocks:** Portable governed binder export (CC-executable work orders)

---

## Objective

Include Work Statements as children of their parent Work Packages in the project binder export, so that the exported binder contains the complete governed execution plan — not just the architecture and decomposition, but the work orders themselves.

---

## Context

The binder export currently assembles documents in pipeline order:

```
CI-001 — Concierge Intake
PD-001 — Project Discovery
IP-001 — Implementation Plan
TA-001 — Technical Architecture
WP-001 — Core Hello World CLI Implementation
```

Work Statements are missing from the output even though the infrastructure is partially built.

**What already works:**

- The binder render endpoint (`app/api/v1/routers/projects.py:885`) queries ALL `is_latest` documents for the project — this includes work_statements in the result set
- `binder_renderer.py` already separates WS docs from other types (line 64-71), nests WSs under WPs via `_get_ordered_ws()` (line 85-88), indents WS TOC entries (line 135-137), and renders WSs with `###` headers (line 153-154)

**What's broken — the matching logic:**

`_get_ordered_ws()` (line 173-196) matches WS docs to WPs by looking up `content.ws_id` against the WP's `ws_index[].ws_id`. This requires:

1. The WP document's `content` to have a populated `ws_index` array with `ws_id` entries
2. Each WS document's `content` to have a `ws_id` field matching the WP's `ws_index` entry

If either side is missing or the keys don't match, the renderer silently produces zero WSs. The endpoint at line 973-974 does pass `ws_index` from WP content, but the matching may fail if:

- WP content uses `work_statements` instead of `ws_index` as the key name
- WS content doesn't have a `ws_id` field, or uses a different field like `id` or `display_id`
- The `ws_index` entries use a different key than `ws_id`

**The real work is diagnosing and fixing the data path** — not building new rendering infrastructure (which already exists).

---

## Scope

**In scope:**

- Diagnose why WS documents don't appear in binder output despite being queried from DB
- Fix the WS→WP matching logic in `_get_ordered_ws()` or the endpoint's data preparation
- Add fallback: if `ws_index` matching produces no WSs but WS documents exist with `parent_document_id` matching the WP, use `parent_document_id` as the join key
- Verify WS content renders correctly via IA-driven `render_document_to_markdown()` path
- Tier-1 tests verifying WSs appear in binder output

**Out of scope:**

- Changes to single-document rendering (WS-RENDER-001)
- Changes to evidence mode (WS-RENDER-004)
- Changes to IA verification gate (WS-RENDER-003)
- Changes to WS content, schema, or generation logic
- Adding non-document artifacts (git history, session logs, ADRs) to the binder

---

## Prohibited

- Do not modify the WS document schema or content structure
- Do not change the rendering of non-WB documents (CI, PD, IP, TA)
- Do not add new API endpoints — this is a fix to the existing binder assembly path
- Do not change the single-document render endpoint behavior

---

## Steps

### Phase 1: Diagnose the data path

**Step 1.1: Inspect real data**

Query a project with WPs and WSs. Check:

1. Does the WP document's `content` have a `ws_index` field? What's its shape?
2. Does the WS document's `content` have a `ws_id` field? What value?
3. Does `parent_document_id` on WS docs point to the parent WP's `id`?

This determines whether the fix is in the matching logic, the field names, or the data population.

### Phase 2: Tests first (must fail before implementation)

**Step 2.1: Test WS inclusion in binder**

File: `tests/tier1/services/test_binder_ws_inclusion.py` (new)

Tests:

- Binder with WP-001 containing WS-001, WS-002 → output includes all three documents
- WS content appears after its parent WP content (not before, not at end)
- WSs are ordered by `ws_index`, not by `display_id` or creation time
- WP with no child WSs → WP appears normally, no error
- TOC entry for WP-001 is followed by indented entries for WS-001, WS-002
- Multiple WPs with multiple WSs → all WSs under correct parent

### Phase 3: Implementation

**Step 3.1: Fix WS→WP matching**

File: `app/domain/services/binder_renderer.py` (`_get_ordered_ws()`)

Based on Phase 1 diagnosis, fix the matching logic. Likely options:

- Fix field name mismatch (e.g., `ws_id` vs `id` vs `display_id`)
- Add `parent_document_id` fallback: if `ws_index` matching returns empty but WS docs exist with `parent_document_id == wp_doc["id"]`, use those ordered by `ws_index` or `display_id`

**Step 3.2: Fix endpoint data preparation (if needed)**

File: `app/api/v1/routers/projects.py` (render_project_binder endpoint, line 964-976)

If the endpoint isn't passing enough data for matching (e.g., WP `id` not in the dict, or WS `parent_document_id` not passed), add the missing fields to the `entry` dict.

### Phase 4: Verify

**Step 4.1:** Run all Phase 2 tests — all must pass.

**Step 4.2:** Run full Tier-1 suite — no regressions.

**Step 4.3:** Export a binder for a project with WPs containing WSs. Verify WSs appear nested under their WP in both TOC and body.

---

## Allowed Paths

```
app/domain/services/binder_renderer.py
app/api/v1/routers/projects.py          (if endpoint data prep needs fixing)
tests/tier1/services/
```

---

## Verification

- [ ] Binder export includes WS documents nested under their parent WP
- [ ] WSs are ordered by `ws_index` within each WP
- [ ] TOC shows WS entries indented under their parent WP
- [ ] WS content renders via IA-driven markdown path (not raw dict dump)
- [ ] WP with no child WSs renders normally (no error, no empty section)
- [ ] Multiple WPs with multiple WSs each → all correctly nested
- [ ] Existing binder tests pass (no regressions in CI, PD, IP, TA rendering)
- [ ] All existing Tier-1 tests pass

---

_Draft: 2026-03-06_
