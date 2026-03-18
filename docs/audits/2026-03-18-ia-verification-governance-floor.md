# IA Verification -- ADR-058: Governance Floor Mechanical Enforcement

**Date:** 2026-03-18
**Artifacts Verified:** 6
**Authoritative Sources:** ADR-058 (Governance Lineage), POL-ADR-EXEC-001, POL-WS-001
**Codebase Branch:** workbench/ws-7a9c71518bb3

---

## Phase 0: Conformance Map

```
artifact: app/domain/services/document_builder_pure.py (apply_post_processing)
authorities:
  - ADR-058 §4 (implementation spec)

artifact: app/domain/services/document_builder.py (3 call sites)
authorities:
  - ADR-058 §4 ("three call sites, zero bypass paths")

artifact: app/domain/services/work_statement_registration.py (ensure_governance_floor)
authorities:
  - ADR-058 §3 (governance floor registry)
  - ADR-058 §2 rule 1 (each artifact type has a floor)
  - ADR-058 §2 rule 2 (floors are artifact-type-specific)

artifact: tests/tier1/test_governance_floor.py
authorities:
  - ADR-058 §4 (test coverage)

artifact: tests/tier1/services/test_document_builder_post_processing.py
authorities:
  - ADR-058 §4 (test coverage)

artifact: app/api/v1/routers/work_binder.py (3 persistence paths)
authorities:
  - ADR-058 §5 ("every WP and WS persisted to the database is guaranteed")
```

---

## Phase 1: Structural Conformance

| Check | Result | Details |
|-------|--------|---------|
| 1.1 Schema Shape | N/A | No schema changes in this work |
| 1.2 Registry Alignment | N/A | No registry changes |
| 1.3 API Surface | N/A | No new API endpoints |
| 1.4 File Inventory | PASS | All files listed in ADR-058 §4 exist |
| 1.5 Test Coverage | PASS | 12 governance floor tests + 8 post-processing tests = 20 total |
| 1.6 Governance | **FAIL** | 3 bypass paths violate ADR-058 §5 guarantee |

**Structural Result:** FAIL -- 1 issue (governance bypass)

### 1.6 Detail: Governance Bypass Paths

ADR-058 §5 states: "Every WP and WS persisted to the database is guaranteed to have at least its floor policy in governance_pins.policy_refs"

The following persistence paths create `work_package` or `work_statement` documents **without** calling `apply_post_processing()`:

| # | File | Line | Operation | Type Created |
|---|------|------|-----------|-------------|
| 1 | app/api/v1/routers/work_binder.py | 473-488 | WPC → WP promotion | `work_package` |
| 2 | app/api/v1/routers/work_binder.py | 681-695 | LLM WS proposal | `work_statement` |
| 3 | app/api/v1/routers/work_binder.py | 795-804 | Manual WS creation | `work_statement` |

All three use direct `db.add(Document(...))` — bypassing DocumentBuilder entirely.

**Additional risk (LOW):** `app/domain/workflow/plan_executor.py:1836-1851` persists documents with variable `state.document_type`. Current workflow configs do not produce WP/WS via this path, but it is not mechanically prevented.

---

## Phase 2: Behavioral Conformance

| Check | Severity | Finding |
|-------|----------|---------|
| 2.1 Acceptance Criteria | -- | ADR-058 requirements met within DocumentBuilder scope |
| 2.2 Prohibited Actions | -- | No prohibited actions specified beyond bypass |
| 2.3 Plane Separation | -- | N/A |
| 2.4 Design System | -- | N/A |
| 2.5 Specification Drift | HIGH | ADR-058 §5 guarantee is broader than implementation scope |

**Behavioral Result:** 1 HIGH, 0 MEDIUM, 0 LOW findings

---

## Findings

### Finding 1: Governance Floor Bypass — WP Promotion

**Severity:** HIGH
**Artifact:** app/api/v1/routers/work_binder.py:473-488
**Authority:** ADR-058 §5 ("every WP and WS persisted to the database is guaranteed to have at least its floor policy")
**Gap:** WP created via candidate promotion bypasses DocumentBuilder. `wp_content` is passed directly to `Document(content=wp_content)` without `apply_post_processing()`.
**Fix:** Add `apply_post_processing(wp_content, "work_package")` before line 473. Import from `document_builder_pure`. ~2 lines.

### Finding 2: Governance Floor Bypass — WS Proposal

**Severity:** HIGH
**Artifact:** app/api/v1/routers/work_binder.py:681-695
**Authority:** ADR-058 §5
**Gap:** WS documents created by LLM proposal bypass DocumentBuilder. `ws_data` passed directly to `Document(content=ws_data)` without floor enforcement.
**Fix:** Add `apply_post_processing(ws_data, "work_statement")` before line 681. ~2 lines.

### Finding 3: Governance Floor Bypass — Manual WS Creation

**Severity:** HIGH
**Artifact:** app/api/v1/routers/work_binder.py:795-804
**Authority:** ADR-058 §5
**Gap:** Manually created WS documents bypass DocumentBuilder. `ws_data` from `build_new_ws()` passed directly without floor enforcement.
**Fix:** Add `apply_post_processing(ws_data, "work_statement")` before line 795. ~2 lines.

---

## Summary

**Verdict:** PARTIAL

**Blocking (must fix before ADR-058 guarantee holds):**
- Finding 1: WP promotion bypass (work_binder.py:488)
- Finding 2: WS proposal bypass (work_binder.py:695)
- Finding 3: Manual WS creation bypass (work_binder.py:804)

**Gaps (tracked as debt):**
- None

**Minor (cosmetic/consistency):**
- None

**Fix effort:** ~6 lines of code + 1 import. All three fixes are identical pattern: add `apply_post_processing(content, doc_type_id)` before `Document()` construction.

**Acceptance Criteria Coverage:**

| Criterion (ADR-058) | Status |
|-----------|--------|
| §2 Rule 1: Each artifact type has a floor | MET |
| §2 Rule 2: Floors are artifact-type-specific | MET |
| §2 Rule 3: Two-layer enforcement | MET (within DocumentBuilder) |
| §3: Floor registry correct | MET |
| §4: Implementation at 3 call sites | MET |
| §5: Every WP/WS guaranteed | **UNMET** — 3 bypass paths |
