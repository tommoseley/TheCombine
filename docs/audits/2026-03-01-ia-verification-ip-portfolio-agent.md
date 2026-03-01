# IA Verification -- Implementation Plan: AI Portfolio Agent

**Date:** 2026-03-01
**Artifacts Verified:** 1 (document 6007a053-3ad8-4134-8ca6-a2c2c9681542)
**Authoritative Sources:** `combine-config/schemas/implementation_plan/releases/1.0.0/schema.json`
**Codebase Branch:** main
**Trigger:** WS-IAV-001 — re-run after Phase 1.1 mechanical field-diff fix

---

## Phase 0: Conformance Map

```
artifact: document 6007a053 (implementation_plan, "AI Portfolio Agent MVP: Implementation Plan")
authorities:
  - combine-config/schemas/implementation_plan/releases/1.0.0/schema.json (shape authority)
```

---

## Phase 1: Structural Conformance

| Check | Result | Details |
|-------|--------|---------|
| 1.1 Schema Shape | **FAIL** | 7 FAILs, 4 LOWs — see findings below |
| 1.2 Registry Alignment | N/A | No registry changes in scope |
| 1.3 API Surface | N/A | No API changes in scope |
| 1.4 File Inventory | N/A | Document-only verification |
| 1.5 Test Coverage | N/A | Document-only verification |
| 1.6 Governance | N/A | Document-only verification |

**Structural Result:** FAIL — 7 issues

---

## Findings

### Finding 1: Missing required field `work_package_candidates`

**Severity:** HIGH
**Artifact:** document content (top level)
**Authority:** Schema `required[]` — `work_package_candidates` is required
**Gap:** Schema requires top-level field `work_package_candidates` (array of `work_package_candidate` items). Document does not have this field. Instead, document has `work_packages` which is not in the schema.
**Fix:** Rename `work_packages` to `work_package_candidates` in document content, or update the generation prompt/handler to emit the correct field name.

---

### Finding 2: Undeclared field `work_packages` (additionalProperties: false)

**Severity:** HIGH
**Artifact:** document content (top level)
**Authority:** Schema `properties{}` + `"additionalProperties": false`
**Gap:** Document contains top-level field `work_packages` which is not declared in schema properties. Schema has `additionalProperties: false`, making this a constraint violation.
**Fix:** This field should be `work_package_candidates` per the schema. Remove/rename.

---

### Finding 3: Undeclared field `candidate_reconciliation` (additionalProperties: false)

**Severity:** HIGH
**Artifact:** document content (top level)
**Authority:** Schema `properties{}` + `"additionalProperties": false`
**Gap:** Document contains top-level field `candidate_reconciliation` (7 items) which does not exist in the schema. Schema has `additionalProperties: false`.
**Fix:** Either add `candidate_reconciliation` to the schema if it is a legitimate field, or remove it from document generation. This field appears to contain WPC-to-WP mapping data that may belong in a separate artifact or as part of the promotion workflow.

---

### Finding 4: Wrong `meta.schema_version` value

**Severity:** HIGH
**Artifact:** `meta.schema_version` = `"1.0"`
**Authority:** Schema `meta.properties.schema_version` has `"const": "3.0"`
**Gap:** Document has `schema_version: "1.0"` but schema requires `const: "3.0"`.
**Fix:** Update the handler/prompt to emit `schema_version: "3.0"`, or update the schema if "1.0" is intentionally the current version (schema `$id` says `v3`).

---

### Finding 5: Undeclared field `meta.workflow_id` (additionalProperties: false)

**Severity:** HIGH
**Artifact:** `meta.workflow_id` = `"implementation_plan"`
**Authority:** Schema `meta` has `"additionalProperties": false` with properties: `schema_version`, `artifact_id`, `correlation_id`, `created_at`, `source`
**Gap:** `workflow_id` is not declared in the `meta` schema properties. The `meta` object has `additionalProperties: false`.
**Fix:** Either add `workflow_id` to the meta schema, or stop emitting it in the document.

---

### Finding 6: Missing required `risk_summary[].affected_candidates`; undeclared `affected_wps`

**Severity:** HIGH
**Artifact:** `risk_summary[0]` (and all risk_summary items)
**Authority:** Schema `definitions.risk_summary_item.required[]` includes `affected_candidates` (array of WPC-### strings). `additionalProperties: false`.
**Gap:** Document risk_summary items use `affected_wps` (e.g., `["data_fetching"]`) instead of the required `affected_candidates` (which expects WPC-### pattern strings). `affected_wps` is undeclared and violates `additionalProperties: false`.
**Fix:** Rename `affected_wps` to `affected_candidates` and use WPC-### IDs instead of WP IDs. This is the same naming drift as Finding 1 — the document uses promoted WP terminology instead of candidate terminology.

---

### Finding 7: All 7 `work_packages` items use wrong field names and include undeclared fields

**Severity:** HIGH
**Artifact:** `work_packages[0..6]` (all 7 items)
**Authority:** Schema `definitions.work_package_candidate` — `required: [candidate_id, title, rationale, scope_in, scope_out, dependencies, definition_of_done]`, `additionalProperties: false`
**Gap:** Every item in `work_packages` (which should be `work_package_candidates`):
- **Missing required:** `candidate_id` (uses `wp_id` instead)
- **Undeclared fields (additionalProperties: false):** `wp_id`, `governance_pins`, `source_candidate_ids`, `transformation`, `transformation_notes`
- **Missing optional:** `sequencing_hint`, `notes_for_work_binder`

The document appears to contain **promoted Work Package** fields (from the WP v1.1.0 schema) rather than **candidate** fields (from the IP schema). This suggests the IP handler or prompt is emitting post-promotion WP structure instead of pre-promotion candidate structure.
**Fix:** Update generation prompt/handler to emit `work_package_candidate` shape: use `candidate_id` (WPC-### pattern), omit `governance_pins`/`source_candidate_ids`/`transformation`/`transformation_notes`/`wp_id`.

---

### Finding 8 (LOW): Optional fields absent from `plan_summary`

**Severity:** LOW
**Artifact:** `plan_summary`
**Authority:** Schema `plan_summary.properties` — `assumptions` and `out_of_scope` are optional
**Gap:** `plan_summary.assumptions` and `plan_summary.out_of_scope` are absent. These are optional per schema (`minItems: 0`).
**Fix:** Consider prompting the LLM to include these if they add value. No schema violation.

---

### Finding 9 (LOW): Optional top-level fields absent

**Severity:** LOW
**Artifact:** document content (top level)
**Authority:** Schema `properties` — `recommendations_for_architecture` and `open_questions` are optional
**Gap:** Both fields are absent from the document. These are optional per schema.
**Fix:** Consider prompting the LLM to include these if they add value. No schema violation.

---

## Root Cause Analysis

The findings cluster around a single root cause: **the IP document was generated using post-promotion Work Package terminology and structure instead of pre-promotion candidate structure.**

| Schema expects | Document has | Nature |
|---------------|-------------|--------|
| `work_package_candidates` | `work_packages` | Field rename |
| `candidate_id` (WPC-###) | `wp_id` (snake_case) | Field rename + pattern change |
| `affected_candidates` (WPC-###) | `affected_wps` (WP IDs) | Field rename + pattern change |
| (nothing) | `governance_pins`, `source_candidate_ids`, `transformation`, `transformation_notes` | Post-promotion fields leaked into pre-promotion artifact |
| (nothing) | `candidate_reconciliation` | Entirely undeclared top-level field |
| `schema_version: "3.0"` | `schema_version: "1.0"` | Version mismatch |

This indicates the IP generation prompt/handler was either:
1. Written before the schema was finalized (prompt references an older schema shape), or
2. Emitting a hybrid structure that conflates IP candidates with promoted WPs

---

## Summary

**Verdict:** NON-COMPLIANT

**Blocking (must fix before acceptance):**
- F1: Missing required `work_package_candidates` (document uses `work_packages`)
- F2: Undeclared `work_packages` violates `additionalProperties: false`
- F3: Undeclared `candidate_reconciliation` violates `additionalProperties: false`
- F4: `meta.schema_version` is `"1.0"`, schema requires `"3.0"`
- F5: Undeclared `meta.workflow_id` violates `additionalProperties: false`
- F6: Missing required `affected_candidates` in risk_summary (uses `affected_wps`)
- F7: All 7 WP items missing `candidate_id`, include 5 undeclared fields each

**Gaps (should fix, tracked as debt):**
- None (all structural issues are blocking)

**Minor (cosmetic/consistency):**
- F8: `plan_summary.assumptions` and `plan_summary.out_of_scope` absent (optional)
- F9: `recommendations_for_architecture` and `open_questions` absent (optional)
