# WS-PROMPT-PROVENANCE-001: Complete Prompt Provenance on Generated Artifacts

**Parent:** Ring 0/1 readiness
**Depends on:** None (uses existing ADR-010 LLM execution logging + `builder_metadata` JSONB field)
**Blocks:** Evidence mode enrichment (WS-RENDER-004 can consume provenance for evidence headers)

---

## Objective

Complete the prompt provenance chain: ensure every LLM-generated document's `builder_metadata` carries the full provenance needed for audit and evidence rendering. The infrastructure is 80% built — this WS closes the gaps.

---

## Context

The provenance chain has three layers, two of which already work:

1. **LLM execution log** (ADR-010, complete): `llm_runs` table stores `prompt_id`, `prompt_version`, `model`, `effective_prompt_hash` per execution. Fully operational.

2. **Document `builder_metadata`** (partial): The `Document.builder_metadata` JSONB field (`app/api/models/document.py:244`) is already populated at creation time by `document_builder.py:300`:

   ```python
   builder_metadata={"prompt_id": ctx.prompt_id, "model": ctx.model,
                      "input_tokens": ..., "output_tokens": ..., "llm_run_id": ...}
   ```

   **What's missing:**
   - `prompt_version` — hardcoded to `"1.0.0"` in the LLM log call (line 248) but not stored on the document at all
   - `effective_prompt_hash` — SHA-256 of the actual prompt text sent to the LLM (already computed in `llm_runs` but not on the artifact). Cryptographically ties the artifact to the exact prompt used, even if prompt files change without version bumps.
   - `generation_station` — the `doc_type_id` that identifies which pipeline station produced this document
   - `generated_at` — timestamp of generation (distinct from `created_at` if document is later updated)

3. **Evidence rendering** (WS-RENDER-004, complete): `evidence_renderer.py` generates YAML frontmatter. Currently uses project_id, display_id, doc_type_id, source_hash. Could include prompt provenance if available on the document.

The gap is small: add 4 fields to the `builder_metadata` dict that `_persist_document()` already writes.

---

## Scope

**In scope:**

- Add `prompt_version`, `effective_prompt_hash`, `generation_station`, `generated_at` to `builder_metadata` in `_persist_document()`
- Resolve actual `prompt_version` from prompt service instead of hardcoding `"1.0.0"` in LLM log call
- Ensure `builder_metadata` provenance updates on document regeneration (remediation rebuilds)
- Tier-1 tests verifying provenance fields are stamped
- Ensure document API responses include `builder_metadata` (verify existing serialization)

**Out of scope:**

- Changes to ADR-010 execution logging (already complete)
- Telemetry aggregation or dashboards (future work)
- Prompt A/B testing infrastructure (future work)
- Evidence header enrichment (WS-RENDER-004 can be updated separately to consume provenance)
- Changes to prompt file naming or versioning conventions

---

## Prohibited

- Do not modify the `llm_runs` table or ADR-010 logging behavior
- Do not add new database columns — `builder_metadata` is an existing JSONB field
- Do not add prompt management or versioning UI
- Do not modify existing prompt file structure

---

## Steps

### Phase 1: Tests first (must fail before implementation)

**Step 1.1: Test provenance fields in builder_metadata**

File: `tests/tier1/services/test_prompt_provenance.py` (new)

Tests:

- Document created via `_persist_document()` → `builder_metadata` contains `prompt_id`, `prompt_version`, `effective_prompt_hash`, `model`, `generation_station`, `generated_at`
- `prompt_version` is not `"1.0.0"` when the actual prompt version differs
- `generation_station` matches the `doc_type_id` of the build context
- `generated_at` is an ISO 8601 timestamp

**Step 1.2: Test prompt_version resolution**

Tests:

- `get_prompt_for_role_task()` returns version information (or the prompt_id encodes version)
- LLM log `prompt_version` matches the resolved version (not hardcoded)

**Step 1.3: Test provenance on regeneration**

Tests:

- Document regenerated (remediation) → `builder_metadata` reflects the new generation's provenance
- `generated_at` timestamp updates to the regeneration time

### Phase 2: Implementation

**Step 2.1: Resolve prompt_version from prompt service**

File: `app/domain/services/document_builder.py`

The `get_prompt_for_role_task()` method currently returns `(system_prompt, prompt_id, expected_schema)`. Either:
- Extend the return tuple to include `prompt_version`, OR
- Parse the version from the `prompt_id` if it follows the `{role}_{task}_v{version}` convention, OR
- Add `prompt_version` to the `BuildContext` dataclass

Replace the hardcoded `prompt_version="1.0.0"` at line 248 with the resolved value.

**Step 2.2: Enrich builder_metadata in _persist_document()**

File: `app/domain/services/document_builder.py` (line 300)

Change from:

```python
builder_metadata={"prompt_id": ctx.prompt_id, "model": ctx.model,
                   "input_tokens": input_tokens, "output_tokens": output_tokens,
                   "llm_run_id": str(run_id) if run_id else None}
```

To:

```python
builder_metadata={
    "prompt_id": ctx.prompt_id,
    "prompt_version": ctx.prompt_version,
    "effective_prompt_hash": effective_prompt_hash,  # SHA-256 of actual prompt text
    "model": ctx.model,
    "generation_station": ctx.doc_type_id,
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "input_tokens": input_tokens,
    "output_tokens": output_tokens,
    "llm_run_id": str(run_id) if run_id else None,
}
```

**Step 2.3: Verify API response includes builder_metadata**

File: `app/api/v1/routers/projects.py` (document resolver endpoint)

Verify that the document resolver response already serializes `builder_metadata`. If not, add it to the response model. (It likely already does since the field is on the ORM model.)

### Phase 3: Verify

**Step 3.1:** Run all Phase 1 tests — all must pass.

**Step 3.2:** Run full Tier-1 suite — no regressions.

---

## Allowed Paths

```
app/domain/services/document_builder.py
app/api/v1/routers/projects.py        (if response model needs update)
tests/tier1/services/
```

---

## Verification

- [ ] `builder_metadata` contains `prompt_id`, `prompt_version`, `effective_prompt_hash`, `model`, `generation_station`, `generated_at` on LLM-generated documents
- [ ] `prompt_version` reflects the actual prompt version (not hardcoded `"1.0.0"`)
- [ ] `generation_station` matches the doc_type_id
- [ ] `generated_at` is an ISO 8601 timestamp
- [ ] Regenerated documents have updated provenance (not stale from first generation)
- [ ] Child documents (extracted by handler) have appropriate `builder_metadata` (existing `extracted_from` pattern unchanged)
- [ ] Document resolver API response includes `builder_metadata`
- [ ] All existing Tier-1 tests pass (no regressions)

---

_Draft: 2026-03-06_
