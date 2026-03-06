# WS-RENDER-004: Render With Evidence Mode (Markdown)

## Status: Accepted

## Governing References

- ADR-054 -- Governed Information Architecture with HTML and PDF Targets
- ADR-010 -- LLM Execution Logging
- WS-RENDER-001 -- Single Document Render (dependency)
- WS-RENDER-002 -- Project Binder Render (dependency)
- WS-RENDER-003 -- IA Gate Before Render (dependency)

---

## Objective

Provide an auditable export mode where every rendered artifact includes provenance and verification evidence in-band in Markdown. Evidence mode embeds source hashes, IA verification status, document lineage, and generation metadata directly in the output — producing a self-contained audit artifact.

---

## Non-Goals

- PDF generation
- Persisting evidence metadata (it's derived from existing data)
- Cryptographic signing of output
- New document types or schema changes
- Modifying the standard render path (evidence is additive)

---

## Prerequisites / Dependencies

- WS-RENDER-001 complete (single document markdown renderer)
- WS-RENDER-002 complete (project binder renderer)
- WS-RENDER-003 complete (IA gate — evidence mode requires IA status)
- Document metadata includes: `created_at`, `version`, `lifecycle_state`, `execution_id`
- Document lineage is queryable (parent display_id, source candidate IDs)

---

## Implementation Tasks

### 1) Backend: Evidence header renderer

**File:** `app/domain/services/markdown_renderer.py` (extend)

Add a function that produces a YAML frontmatter evidence block for a single document:

```markdown
---
project_id: HWCA-001
display_id: TA-001
doc_type_id: technical_architecture
document_version: 7
source_hash: sha256:a1b2c3d4...
renderer_version: render-md@1.0.0
render_profile: print
generated_at: 2026-03-05T14:30:00Z
ia_verification:
  status: PASS
  report_id: IA-VERIFY-0192
  verified_at: 2026-03-05T14:30:00Z
lineage:
  parent_display_id: IP-001
  source_candidate_ids: ["WPC-001", "WPC-002"]
---
```

**Field rules:**
- Only include fields that exist (no null/empty fields)
- `source_hash`: SHA-256 of the canonical JSON content (deterministic)
- `ia_verification`: from the IA gate check (WS-RENDER-003 runs before render)
- `lineage`: from document metadata if available; omit entirely if no lineage
- `renderer_version`: hardcoded `render-md@1.0.0` (bump on renderer changes)

### 2) Backend: Evidence mode for single-document render

**File:** `app/api/v1/routers/projects.py` (modify render endpoint)

**New query param:**
- `mode` — `standard` | `evidence` (default `standard`)

**Behavior when `mode=evidence`:**
1. Run IA verification (as per WS-RENDER-003)
2. Compute `source_hash` (SHA-256 of canonical content)
3. Collect lineage metadata
4. Prepend YAML frontmatter evidence block to the rendered Markdown
5. Return as normal attachment

**Filename:** `{project_id}-{display_id}-evidence.md` (when `mode=evidence`)

### 3) Backend: Evidence mode for project binder render

**File:** `app/api/v1/routers/projects.py` (modify binder endpoint)

**New query param:**
- `mode` — `standard` | `evidence` (default `standard`)

**Behavior when `mode=evidence`:**
1. Run IA verification for all documents (per WS-RENDER-003)
2. For each document: compute evidence header
3. After cover + TOC, insert an **Evidence Index** section:

```markdown
## Evidence Index

| Display ID | Title | Version | IA Status | Source Hash |
|------------|-------|---------|-----------|-------------|
| CI-001 | Concierge Intake | 3 | PASS | sha256:a1b2... |
| PD-001 | Project Discovery | 5 | PASS | sha256:c3d4... |
| TA-001 | Technical Architecture | 7 | PASS | sha256:e5f6... |
| WP-001 | Auth System | 2 | PASS | sha256:g7h8... |
| WS-001 | JWT Implementation | 1 | PASS | sha256:i9j0... |
```

4. Each document section includes its YAML frontmatter evidence block
5. Return as attachment

**Filename:** `{project_id}-binder-evidence.md` (when `mode=evidence`)

### 4) SPA: Evidence download option

**Files:**
- `spa/src/components/FullDocumentViewer.jsx`
- `spa/src/components/Floor.jsx`

**Single document:**
- Change "Download Markdown" button to a dropdown with two options:
  - "Download Markdown"
  - "Download Markdown (With Evidence)"

**Project binder (breadcrumb bar):**
- Change binder download button to a dropdown with two options:
  - "Download Project Binder"
  - "Download Project Binder (With Evidence)"

**Implementation:** Simple dropdown menu on click, no new components needed.

---

## Tier-1 Tests

**File:** `tests/tier1/services/test_evidence_renderer.py`

- Evidence header includes project_id, display_id, doc_type_id
- Evidence header includes document_version when available
- Evidence header includes source_hash (SHA-256 of content)
- Evidence header omits lineage when no lineage exists
- Evidence header includes IA verification status
- Source hash is deterministic (same content = same hash)
- Evidence index table includes all binder documents
- Evidence index columns: display_id, title, version, IA status, source hash

**File:** `tests/tier1/api/test_render_evidence_routes.py`

- Single doc render with `mode=evidence` returns Markdown with YAML frontmatter
- Single doc render with `mode=standard` has no frontmatter (unchanged)
- Binder render with `mode=evidence` includes Evidence Index section
- Binder render with `mode=evidence` includes per-document frontmatter
- Evidence filename uses `-evidence` suffix
- Invalid mode param returns 400

---

## Acceptance Criteria

- `mode=evidence` includes YAML frontmatter provenance header per document
- Binder with `mode=evidence` includes Evidence Index after TOC
- IA verification status (PASS) appears in evidence (FAIL blocked by WS-RENDER-003)
- `source_hash` is SHA-256 of canonical content, deterministic
- `mode=standard` is unchanged (no frontmatter, no evidence index)
- SPA offers both standard and evidence download options
- Evidence filename uses `-evidence` suffix to distinguish from standard
- Tier-1 tests pass; SPA builds clean

---

## Allowed Paths

**Backend:**
- `app/domain/services/markdown_renderer.py`
- `app/domain/services/binder_renderer.py`
- `app/api/v1/routers/projects.py`
- `tests/tier1/services/test_evidence_renderer.py` (new)
- `tests/tier1/api/test_render_evidence_routes.py` (new)

**Frontend:**
- `spa/src/api/client.js`
- `spa/src/components/FullDocumentViewer.jsx`
- `spa/src/components/Floor.jsx`

---

## Prohibited Actions

- Persisting evidence metadata to the database
- Cryptographic signing (out of scope)
- Modifying standard render output (evidence is additive via `mode` param)
- Adding new document types or schema changes
- Including raw conversation transcripts in evidence (ADR-040 violation)

---

## Verification Steps

**Backend:**
- `python -m pytest tests/tier1/services/test_evidence_renderer.py -v`
- `python -m pytest tests/tier1/api/test_render_evidence_routes.py -v`

**Frontend:**
- `cd spa && npm run build`

**Integration (manual):**
- Single doc with `mode=evidence` → Markdown with YAML frontmatter
- Binder with `mode=evidence` → Markdown with Evidence Index + per-doc frontmatter
- Standard mode → unchanged output
- Source hashes are stable across repeated renders of same content

**Tier 0:**
- `ops/scripts/tier0.sh --frontend`
