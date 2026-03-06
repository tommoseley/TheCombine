# WS-RENDER-003: IA Gate Before Render

## Status: Accepted

## Governing References

- ADR-054 -- Governed Information Architecture with HTML and PDF Targets
- WS-RENDER-001 -- Single Document Render (dependency)
- WS-RENDER-002 -- Project Binder Render (dependency)

---

## Objective

Prevent exporting "official-looking" rendered output when a document fails IA compliance against its authoritative schema. IA verification must pass before rendering is permitted. This applies to both single-document render and project binder render.

---

## Non-Goals

- Evidence/provenance mode (WS-RENDER-004)
- Modifying IA verification logic itself
- Changing document content or schema
- Auto-remediation of IA failures

---

## Prerequisites / Dependencies

- WS-RENDER-001 complete (single document render endpoint exists)
- WS-RENDER-002 complete (project binder render endpoint exists)
- IA verification service exists and can validate a document against its package.yaml IA definitions
- IA verification produces a structured report (report_id, summary, pass/fail)

---

## Implementation Tasks

### 1) Backend: IA gate in single-document render

**File:** `app/api/v1/routers/projects.py` (modify render endpoint from WS-RENDER-001)

**Gate logic (inserted before rendering):**

1. Load IA definitions for the document's `doc_type_id`
2. Run IA verification against the document content
3. If verification **passes**: proceed with rendering as before
4. If verification **fails**: return `409 Conflict` with IA failure payload (do NOT render)

**Failure response (409):**
```json
{
    "status": "ia_violation",
    "message": "Rendering blocked: IA verification failed for {display_id}.",
    "failures": [
        {
            "display_id": "TA-001",
            "report_id": "IA-VERIFY-0192",
            "summary": "Missing required section: constraints"
        }
    ]
}
```

**Design note:** 409 Conflict is used because the resource state (IA non-compliance) prevents the requested action (rendering). The request itself is valid.

### 2) Backend: IA gate in project binder render

**File:** `app/api/v1/routers/projects.py` (modify binder endpoint from WS-RENDER-002)

**Gate logic (inserted before assembly):**

1. For each document that will be included in the binder:
   - Run IA verification
   - Collect failures
2. If **all documents pass**: proceed with binder assembly
3. If **any document fails**: return `409 Conflict` with all failures listed (do NOT render any part of the binder)

**Failure response (409):**
```json
{
    "status": "ia_violation",
    "message": "Binder rendering blocked: IA verification failed for 2 document(s).",
    "failures": [
        {
            "display_id": "TA-001",
            "report_id": "IA-VERIFY-0192",
            "summary": "Missing required section: constraints"
        },
        {
            "display_id": "IP-001",
            "report_id": "IA-VERIFY-0193",
            "summary": "Field 'candidates' has no render_as declaration"
        }
    ]
}
```

**Design note:** The binder is all-or-nothing. A partial binder with some documents missing would be misleading. The operator must fix IA compliance before exporting.

### 3) Backend: IA gate bypass for documents without IA definitions

Some document types may not yet have IA definitions (Level 0 coverage). For these:
- IA gate is **skipped** (not failed) — the document renders via fallback path
- This prevents the gate from blocking entire binders due to document types that legitimately have no IA yet
- Log a warning: `"IA gate skipped for {doc_type_id}: no IA definitions found"`

### 4) SPA: Handle IA violation response

**Files:**
- `spa/src/components/FullDocumentViewer.jsx`
- `spa/src/components/Floor.jsx`

**Behavior:**
- If render endpoint returns `ia_violation` (409):
  - Show a toast/modal: "Render blocked: IA verification failed."
  - List the failing document(s) with display_id and summary
  - If IA report viewer exists, link to it
- Do NOT trigger browser download on 409

---

## Tier-1 Tests

**File:** `tests/tier1/api/test_render_ia_gate.py`

**Single document render:**
- IA passes → 200, returns Markdown (unchanged behavior)
- IA fails → 409, returns `ia_violation` JSON, no Markdown body
- Document type with no IA definitions → 200, renders via fallback (gate skipped)
- Failure response includes `display_id`, `report_id`, `summary`

**Project binder render:**
- All documents pass IA → 200, returns Markdown binder
- One document fails IA → 409, returns `ia_violation` JSON listing the failure
- Multiple documents fail IA → 409, all failures listed
- Mix of IA-covered and non-IA documents → gate only checks IA-covered ones
- Failure response includes all failing display_ids

---

## Acceptance Criteria

- Single-document render returns 409 when IA verification fails
- Project binder render returns 409 when any included document fails IA
- Failure responses include enough detail to locate the problem (display_id + summary)
- Passing IA permits rendering as before (no behavioral change for compliant documents)
- Documents without IA definitions are rendered via fallback (gate skipped, not failed)
- SPA shows IA failure details on 409 instead of triggering download
- Tier-1 tests pass; SPA builds clean

---

## Allowed Paths

**Backend:**
- `app/api/v1/routers/projects.py`
- `app/domain/services/markdown_renderer.py` (if gate logic is factored into renderer)
- `app/domain/services/binder_renderer.py` (if gate logic is factored into binder)
- `tests/tier1/api/test_render_ia_gate.py` (new)

**Frontend:**
- `spa/src/components/FullDocumentViewer.jsx`
- `spa/src/components/Floor.jsx`

---

## Prohibited Actions

- Modifying IA verification logic or definitions
- Rendering partial binders (all-or-nothing)
- Persisting IA verification results as part of rendering
- Silently skipping documents that fail IA (must report)
- Changing the render response format for successful renders

---

## Verification Steps

**Backend:**
- `python -m pytest tests/tier1/api/test_render_ia_gate.py -v`

**Frontend:**
- `cd spa && npm run build`

**Integration (manual):**
- Render a document with valid IA → downloads normally
- Render a document with broken IA → 409 with failure details
- Render a binder where one document fails IA → 409 listing the failure

**Tier 0:**
- `ops/scripts/tier0.sh --frontend`
