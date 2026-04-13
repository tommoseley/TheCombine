# ADR-069 Implementation Plan: Rewind as Correction Gate

**Status:** Accepted
**ADR:** ADR-069 — Rewind as Correction Gate
**Scope:** Multi-commit (3 Work Packages, 7 Work Statements)
**Estimated complexity:** Medium

---

## Overview

Extend the rewind mechanism to serve as a correction gate: operator enters optional binding corrections at rewind time, corrections are stored as authority records (reusing ADR-064 infrastructure), consumed during regeneration via prompt template injection, and displayed in binder audit.

---

## Dependency Chain

```
WP-CORRECT-001 (Backend: authority extension + rewind wiring)
    └── WP-CORRECT-002 (Prompt injection + regeneration consumption)
            └── WP-CORRECT-003 (UI + binder audit)
```

WP-001 is foundational (authority service, rewind endpoint, pre-population API). WP-002 depends on WP-001 authority bundle shape. WP-003 depends on both (UI calls WP-001 endpoints, prompt rendering uses WP-002 template variable).

---

## WP-CORRECT-001: Backend Authority Extension

**Objective:** Extend authority service to handle `operator_correction` records, wire rewind endpoint to persist corrections, provide pre-population endpoint for UI.

### WS-CORRECT-001: Authority Service Extension

**Status:** Accepted
**Governing ADR:** ADR-069
**Verification Mode:** A

**Allowed Paths:**
- app/domain/services/authority_service.py
- app/domain/models/authority_record.py
- tests/

**Objective:**

Add stage-aware correction resolution to `AuthorityService`. The existing `get_authority_bundle(project_id)` stays project-scoped — it gains an `operator_corrections` key containing **all** current corrections for the project (unfiltered). Stage-specific filtering is the caller's responsibility via the new `get_corrections_for_stage()` method. This keeps the bundle API honest: it returns project-level authority, not a stage-contextual view.

**Preconditions:**
- 4876 tests passing
- AuthorityService exists with `record_authority()`, `get_authority_bundle()`, `get_current_authority()`
- authority_records table supports arbitrary `authority_type` values (no schema change needed)

**Scope:**

In Scope:
1. Add `get_corrections_for_stage(project_id, stage)` method to `AuthorityService` — returns ordered list of current `operator_correction` records applicable to a specific generated stage (direct match on `record.stage == stage` OR `stage` appears in `record.value.applies_to_stages`), sorted by pipeline order of origin stage then `created_at`. This is the **stage-aware** query — used by the task node and binder.
2. Extend `get_authority_bundle()` to include `operator_corrections` key — **all** current `operator_correction` records for the project, as a list of `{origin_stage, text, authority_record_id}` dicts sorted by pipeline order then `created_at`. This is the **project-scoped** view — no stage filtering applied. Callers needing stage filtering use `get_corrections_for_stage()` instead.
3. Add `get_current_correction(project_id, stage)` method — returns the single current correction record for a specific originating stage key (`correction:{stage}`), for pre-population. Returns None if absent.
4. Write tests: bundle includes all corrections (project-scoped, not filtered), `get_corrections_for_stage` filters correctly (fan-in ordering is deterministic), `get_current_correction` returns correct record, superseded corrections excluded from both

Out of Scope:
- Rewind endpoint changes (WS-CORRECT-002)
- Prompt injection (WP-CORRECT-002)
- UI (WP-CORRECT-003)

**Prohibited Actions:**
- Do not change the authority_records table schema
- Do not modify existing PGC answer behavior
- Do not change the `pgc_answers` or `pgc_questions` keys in the bundle

**Procedure:**

Phase 1: Failing Tests
1. Write test: `get_authority_bundle` returns `operator_corrections: []` when no corrections exist
2. Write test: `get_authority_bundle` returns all current corrections for project (unfiltered — includes TA and IP corrections regardless of target stage)
3. Write test: `get_corrections_for_stage(project_id, "IP")` returns TA correction (via applies_to) + IP correction, TA first (pipeline order)
4. Write test: `get_corrections_for_stage(project_id, "TA")` returns only TA correction (IP correction does not apply upstream)
5. Write test: `get_current_correction` returns current correction for originating stage, None when absent
6. Write test: superseded correction excluded from both bundle and stage query
7. Run tests, verify all fail

Phase 2: Implement
1. Add `get_corrections_for_stage(project_id, stage)` to `AuthorityService`:
   - Query current `operator_correction` records for project
   - Filter: `record.stage == stage` OR `stage in record.value.get("applies_to_stages", [])`
   - Sort by pipeline order of `record.stage` (use `PipelineStage` ordering), then `record.created_at`
   - Return list of `AuthorityRecordDTO`
2. Add `get_current_correction(project_id, stage)` to `AuthorityService`:
   - Query single current record: `(project_id, "operator_correction", f"correction:{stage}")`
   - Return `AuthorityRecordDTO` or None
3. Extend `get_authority_bundle()`:
   - After building `pgc_records`, query all current `operator_correction` records for the project (no stage filter)
   - Build ordered list: `[{"origin_stage": r.stage, "text": r.value.get("text", ""), "authority_record_id": r.id} for r in sorted_corrections]`
   - Add `"operator_corrections"` key to returned dict
   - **Note:** This is the project-scoped view. Stage-specific consumers (task node, binder) call `get_corrections_for_stage()` directly.

Phase 3: Verify
1. Run all new tests — pass
2. Run existing authority service tests — no regressions
3. Run `python -m pytest tests/ -x -q` — all pass

---

### WS-CORRECT-002: Rewind Endpoint Wiring

**Status:** Accepted
**Governing ADR:** ADR-069
**Verification Mode:** A

**Allowed Paths:**
- app/api/v1/routers/rewind.py
- app/domain/services/rewind_service.py
- app/domain/models/lineage_event.py
- tests/

**Objective:**

Extend the rewind API endpoint to accept an optional correction, persist it as an `operator_correction` authority record, and link it to the rewind lineage event.

**Preconditions:**
- WS-CORRECT-001 complete (authority service extended)
- `RewindRequestBody` currently has: `rewind_to_stage`, `reason`, `actor`
- Rewind endpoint at `POST /projects/{project_id}/rewind`

**Scope:**

In Scope:
1. Add optional `correction` field to `RewindRequestBody`: `{"text": str, "applies_to_stages": Optional[List[str]]}`
2. When `correction` is present and non-empty, persist as authority record after rewind executes:
   - `authority_type = "operator_correction"`
   - `stage = rewind_to_stage` (the stage being rewound to)
   - `key = f"correction:{rewind_to_stage}"`
   - `value = {"text": correction.text, "applies_to_stages": correction.applies_to_stages or [rewind_to_stage], "rewind_event_id": str(lineage_event_id)}`
   - `source_execution_id = lineage_event_id` (MVP surrogate — no execution at rewind time)
   - `lineage_path_id = lineage_event_id` (MVP surrogate)
   - `actor = "operator"`
3. Supersession: existing `(project_id, "operator_correction", key)` record is automatically superseded by `AuthorityService.record_authority()`
4. Add correction record ID to `RewindResponseBody`
5. Write tests: rewind with correction persists authority record, rewind without correction leaves no correction record, supersession on re-rewind

Out of Scope:
- Pre-population endpoint (WS-CORRECT-003)
- Prompt injection (WP-CORRECT-002)

**Prohibited Actions:**
- Do not change the rewind core logic (impact evaluation, stale marking, lineage event recording)
- Do not make correction required — it must remain optional
- Do not modify the lineage_events table schema

**Procedure:**

Phase 1: Failing Tests
1. Write test: POST rewind with correction → authority record created with correct fields
2. Write test: POST rewind without correction → no operator_correction record created
3. Write test: POST rewind with correction, then POST rewind again with updated correction → first record superseded, second is current
4. Write test: response includes `correction_record_id` when correction provided, null when not
5. Run tests, verify all fail

Phase 2: Implement
1. Add `CorrectionInput` Pydantic model: `text: str`, `applies_to_stages: Optional[List[str]] = None`
2. Add `correction: Optional[CorrectionInput] = None` to `RewindRequestBody`
3. In `rewind_pipeline` endpoint, after `service.execute_rewind(request)` succeeds:
   - If `body.correction` and `body.correction.text.strip()`:
     - Build `AuthorityService` from DB session (same pattern as PGC processor)
     - Call `record_authority()` with operator_correction fields
     - Capture returned record ID
4. Add `correction_record_id: Optional[str] = None` to `RewindResponseBody`
5. Return correction_record_id in response

Phase 3: Verify
1. Run all new tests — pass
2. Run existing rewind tests — no regressions
3. Run `python -m pytest tests/ -x -q` — all pass

---

### WS-CORRECT-003: Pre-Population Endpoint

**Status:** Accepted
**Governing ADR:** ADR-069
**Verification Mode:** A

**Allowed Paths:**
- app/api/v1/routers/rewind.py
- tests/

**Objective:**

Add an endpoint to retrieve the current correction for a (project, stage) pair, enabling the UI to pre-populate the correction field on subsequent rewinds.

**Preconditions:**
- WS-CORRECT-001 complete (`get_current_correction` method exists)

**Scope:**

In Scope:
1. Add `GET /projects/{project_id}/corrections/{stage}` endpoint
2. Returns current correction text and applies_to_stages, or 404 if no correction exists for that stage
3. Write tests: returns correction when present, 404 when absent, returns updated correction after supersession

Out of Scope:
- Listing all corrections for a project (can be added later if needed)
- UI consumption (WP-CORRECT-003)

**Prohibited Actions:**
- Do not return superseded/historical corrections — only current

**Procedure:**

Phase 1: Failing Tests
1. Write test: GET corrections for stage with existing correction → 200 with text and applies_to_stages
2. Write test: GET corrections for stage with no correction → 404
3. Write test: after supersession, GET returns the new correction, not the old one
4. Run tests, verify all fail

Phase 2: Implement
1. Add `CorrectionResponse` Pydantic model: `stage: str`, `text: str`, `applies_to_stages: List[str]`, `authority_record_id: str`, `created_at: str`
2. Add `GET /{project_id}/corrections/{stage}` endpoint in rewind router
3. Use `AuthorityService.get_current_correction(project_id, stage)` to resolve
4. Return 404 if None, 200 with CorrectionResponse otherwise

Phase 3: Verify
1. Run all new tests — pass
2. Run `python -m pytest tests/ -x -q` — all pass

---

## WP-CORRECT-002: Prompt Injection + Regeneration Consumption

**Objective:** Build correction context for prompt assembly, inject via `{{operator_corrections}}` template variable, version-bump affected prompts and workflows.

**Dependencies:** WP-CORRECT-001 complete (authority bundle includes `operator_corrections`)

### WS-CORRECT-004: Correction Context Builder + Task Node Injection

**Status:** Accepted
**Governing ADR:** ADR-069
**Verification Mode:** A

**Allowed Paths:**
- app/domain/services/
- app/domain/workflow/nodes/task.py
- tests/

**Objective:**

Create a correction context builder that renders the ordered correction list into prompt text, and wire it into the task node execution path — same pattern as `{{mockup_context}}` (ADR-068).

**Preconditions:**
- WP-CORRECT-001 complete (authority bundle returns `operator_corrections` list)
- Task node already handles `{{mockup_context}}` injection (lines 104-143 of task.py)

**Scope:**

In Scope:
1. Create `app/domain/services/correction_context_builder.py`:
   - `build_correction_text(project_id, stage, db_session) → (str, List[str])` — returns rendered text and list of authority_record_ids
   - Loads corrections via `AuthorityService.get_corrections_for_stage()` (stage-aware query, not the project-scoped bundle)
   - Renders as numbered list with provenance: `1. [From TA rewind] Cloud AI integration must be...`
   - Returns empty string and empty list if no corrections apply
2. Wire into task node (`task.py`): after mockup context resolution, resolve `{{operator_corrections}}`:
   - If `"{{operator_corrections}}"` in `task_prompt`: call `build_correction_text()`
   - If corrections exist: replace `{{operator_corrections}}` with rendered text (the conditional Mustache-style header/footer in the prompt template handles section framing)
   - If no corrections: **strip the entire `{{operator_corrections}}` placeholder and its surrounding conditional block** — the section must be absent from the final prompt, not replaced with a negative note. This matches ADR-069 §3.5: "If no corrections exist, the section is absent (not empty)"
   - Record correction authority_record_ids in execution metadata (same pattern as `mockup_artifact_ids`)
3. Write tests: builder renders correct numbered format, ordering matches pipeline order, empty case returns empty string, task node strips placeholder entirely when no corrections

Out of Scope:
- Prompt version bumps (WS-CORRECT-005)
- Workflow version bumps (WS-CORRECT-005)
- QA gate validation of corrections (future enhancement)

**Prohibited Actions:**
- Do not modify the mockup context builder
- Do not change existing task node behavior for other template variables
- Do not hardcode corrections into prompts — only resolve when `{{operator_corrections}}` is present (governed injection per ADR-049)

**Procedure:**

Phase 1: Failing Tests
1. Write test: `build_correction_text` with one TA correction → numbered text with `[From TA rewind]` prefix
2. Write test: multi-correction fan-in (TA + IP corrections for IP stage) → two numbered items, TA first
3. Write test: no corrections → empty string, empty list
4. Write test: task node replaces `{{operator_corrections}}` with rendered text when corrections exist
5. Write test: task node strips `{{operator_corrections}}` and its surrounding conditional block entirely when no corrections — final prompt must not contain `{{operator_corrections}}`, `[No operator corrections`, or any remnant of the section
6. Run tests, verify all fail

Phase 2: Implement
1. Create `app/domain/services/correction_context_builder.py`
2. Add `{{operator_corrections}}` resolution block in `task.py` (after mockup block, before LLM completion):
   - Check if `"{{operator_corrections}}"` in task_prompt
   - If yes, call `build_correction_text()`
   - If corrections returned: replace `{{operator_corrections}}` with rendered text in messages
   - If no corrections (empty string): strip the `{{operator_corrections}}` placeholder and its conditional wrapper lines from messages (match the `{{#operator_corrections}}` ... `{{/operator_corrections}}` block and remove entirely)
   - Track `correction_authority_record_ids` alongside `mockup_artifact_ids`

Phase 3: Verify
1. Run all new tests — pass
2. Run existing task node tests — no regressions
3. Run `python -m pytest tests/ -x -q` — all pass

---

### WS-CORRECT-005: Prompt and Workflow Version Bumps

**Status:** Accepted
**Governing ADR:** ADR-069
**Verification Mode:** A

**Allowed Paths:**
- combine-config/prompts/tasks/
- combine-config/workflows/
- combine-config/_active/active_releases.json
- tests/

**Objective:**

Add `{{operator_corrections}}` conditional section to task prompts for TA, IP, and PD. Bump prompt and workflow versions. Update active_releases.json.

**Preconditions:**
- WS-CORRECT-004 complete (task node resolves `{{operator_corrections}}`)
- Current active versions: TA task v1.5.0, TA workflow v7.0.0

**Scope:**

In Scope:
1. Create TA task prompt v1.6.0 (copy from v1.5.0):
   - Add `{{operator_corrections}}` conditional section after `{{mockup_context}}` section
   - Section text per ADR-069 §3.5
2. Create IP task prompt version bump (copy current, add `{{operator_corrections}}` section)
3. Create PD task prompt version bump (copy current, add `{{operator_corrections}}` section)
4. Bump corresponding workflow definitions to reference new prompt versions
5. Update `active_releases.json` to point to new workflow versions
6. Write tests: new prompt files contain `{{operator_corrections}}` placeholder

Out of Scope:
- WS, WP task prompts (corrections not applicable to these stages in V1)
- QA prompts (future: QA validates against corrections)

**Prohibited Actions:**
- Do not modify existing prompt versions — create new version directories
- Do not change prompt content other than adding the corrections section
- Do not change workflow structure — only prompt version references

**Procedure:**

Phase 1: Identify Current Versions
1. Read current active prompt versions for TA, IP, PD from active_releases.json and workflow definitions
2. Verify current prompt files exist

Phase 2: Implement
1. Copy TA task prompt v1.5.0 → v1.6.0, add `{{operator_corrections}}` section
2. Copy IP task prompt current → next version, add `{{operator_corrections}}` section
3. Copy PD task prompt current → next version, add `{{operator_corrections}}` section
4. Create new workflow version directories for TA, IP, PD referencing new prompt versions
5. Update active_releases.json

Phase 3: Verify
1. Verify all new prompt files contain `{{operator_corrections}}`
2. Verify workflow definitions reference correct new prompt versions
3. Verify active_releases.json is valid JSON
4. Run `python -m pytest tests/ -x -q` — all pass (prompt loading tests should pick up new versions)

---

## WP-CORRECT-003: UI + Binder Audit

**Objective:** Extend RewindControl with correction textarea and stage checkboxes, pre-populate from authority store, display active corrections in binder.

**Dependencies:** WP-CORRECT-001 complete (rewind endpoint accepts corrections, pre-population endpoint exists)

### WS-CORRECT-006: RewindControl UI Extension

**Status:** Accepted
**Governing ADR:** ADR-069
**Verification Mode:** A

**Allowed Paths:**
- spa/src/components/RewindControl.jsx
- spa/src/api/client.js
- spa/src/

**Objective:**

Extend the rewind dialog with an optional binding correction textarea and stage applicability checkboxes. Pre-populate correction from authority store on subsequent rewinds.

**Preconditions:**
- WP-CORRECT-001 complete (rewind endpoint accepts correction, GET corrections endpoint exists)
- RewindControl.jsx currently: confirm dialog with reason input, calls `api.rewindPipeline()`

**Scope:**

In Scope:
1. Add `getCorrection(projectId, stage)` to API client — calls `GET /projects/{project_id}/corrections/{stage}`
2. Add `correction` parameter to `api.rewindPipeline()` call
3. Extend RewindControl.jsx:
   - When confirm dialog opens: fetch current correction for stage (may 404 → empty)
   - Add collapsible "Binding correction (optional)" section below reason input
   - Textarea for correction text, pre-populated if correction exists
   - Stage checkboxes for `applies_to_stages` (default: only the rewound-to stage checked)
   - On submit: include `correction` in rewind request (only if text is non-empty)
4. Handle loading state for correction fetch (brief spinner or skeleton)

Out of Scope:
- Binder display (WS-CORRECT-007)
- Correction history/audit viewer
- Correction editing outside of rewind flow

**Prohibited Actions:**
- Do not change existing rewind behavior when no correction is entered
- Do not make correction field required
- Do not add new npm dependencies

**Procedure:**

Phase 1: Implement
1. Add `getCorrection` and update `rewindPipeline` in API client
2. Extend RewindControl:
   - `useEffect` on dialog open: fetch current correction → pre-populate or leave empty
   - Add correction textarea (multi-line, 3-4 rows)
   - Add stage checkboxes (pipeline stages from a constant list)
   - Wire into submit handler
3. Style consistent with existing dialog (same border colors, text sizes, spacing patterns)

Phase 2: Verify
1. `cd spa && npm run build` — builds clean
2. Manual verification:
   - Open rewind dialog → correction section collapsed, no pre-populated text
   - Enter correction, submit → rewind succeeds
   - Open rewind dialog again for same stage → correction pre-populated
   - Edit correction, submit → supersession works
   - Rewind with empty correction → no correction record created

---

### WS-CORRECT-007: Binder Audit Display

**Status:** Accepted
**Governing ADR:** ADR-069
**Verification Mode:** A

**Allowed Paths:**
- app/api/v1/routers/work_binder*.py
- spa/src/components/
- tests/

**Objective:**

Display which operator corrections were in effect **at the time each document was generated**, not the current correction state. This is a historical audit view: if a correction was later superseded, the binder still shows what governed the generation that produced the document.

**Preconditions:**
- WP-CORRECT-001 and WP-CORRECT-002 complete
- WS-CORRECT-004 stamps `correction_authority_record_ids` in document metadata (`meta.correction_authority_record_ids`) at generation time
- Binder already displays evaluation sections (ADR-058, ADR-061)
- `AuthorityRepository.get_by_ids()` or equivalent can resolve records by ID regardless of status (including superseded)

**Scope:**

In Scope:
1. For each document in the binder, read `meta.correction_authority_record_ids` (list of UUIDs stamped at generation time by WS-CORRECT-004)
2. Resolve those authority record IDs from the authority store — include superseded records (these were current at generation time, even if superseded since)
3. Add `operator_corrections` section to binder evaluation output per document:
   - `generation_time_corrections`: list of `{origin_stage, text, authority_record_id, status}` — the corrections that governed this specific generation
   - `status` reflects whether the correction is still `"current"` or has been `"superseded"` since generation
4. If `meta.correction_authority_record_ids` is absent or empty for a document, the section is empty (document was generated without corrections)
5. SPA: render corrections section in binder viewer — shows per-document corrections with a visual indicator if a correction has since been superseded ("correction has been updated since this document was generated")
6. Write tests: binder output includes generation-time corrections resolved from meta IDs, handles missing meta gracefully, shows superseded status correctly

Out of Scope:
- QA gate validation against corrections (future enhancement — QA checks whether output satisfies correction)
- Correction edit from binder view
- Full supersession chain display (only current-vs-superseded indicator)

**Prohibited Actions:**
- Do not query current corrections as a substitute for generation-time audit — the binder must show what was active when the document was generated, not what is active now
- Do not modify binder evaluation logic for other sections
- Do not add correction editing to binder view

**Procedure:**

Phase 1: Failing Tests
1. Write test: document with `meta.correction_authority_record_ids = [id1]` → binder resolves and includes correction text and origin_stage
2. Write test: document with no `correction_authority_record_ids` in meta → binder `operator_corrections` is empty list
3. Write test: correction record that was superseded after generation → binder shows text but marks `status: "superseded"`
4. Run tests, verify fail

Phase 2: Implement
1. Add `get_by_ids(record_ids)` to `AuthorityRepository` if not already present — returns records regardless of status
2. In binder evaluation builder: for each document, read `meta.correction_authority_record_ids`, resolve via `get_by_ids()`, build correction entries with status
3. Add to evaluation output per document: `{"operator_corrections": [{"origin_stage": ..., "text": ..., "authority_record_id": ..., "status": ...}]}`
4. SPA: add `OperatorCorrectionsSection` component to binder viewer — renders per-document, shows superseded indicator

Phase 3: Verify
1. Run all new tests — pass
2. Run existing binder tests — no regressions
3. `cd spa && npm run build` — builds clean
4. Run `python -m pytest tests/ -x -q` — all pass

---

## Verification (Full)

After all WPs:

1. `python -m pytest tests/ -x -q` — all tests pass
2. `cd spa && npm run build` — SPA builds clean
3. `ops/scripts/tier0.sh --frontend` — Tier 0 passes
4. Manual smoke test:
   - Rewind TA with correction "AI must be server-side" applies_to [TA, IP]
   - Re-open rewind dialog → correction pre-populated
   - Trigger TA regeneration → verify correction appears in LLM run prompt
   - Trigger IP generation → verify TA-originated correction appears (fan-in)
   - View binder → correction displayed in evaluation section
   - Rewind TA again with edited correction → old superseded, new active

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Prompt token budget growth from corrections | Low | Medium | Corrections are short text; monitor token counts in LLM run logs |
| Vague corrections ("make it better") provide no value | Medium | Low | UX guidance text in dialog; future: validation heuristic |
| Fan-in ordering edge case (same pipeline stage, multiple corrections) | Low | Low | Supersession ensures one current correction per (project, stage); fan-in sorts by origin stage then created_at |
| Pre-population latency on rewind dialog open | Low | Low | Single authority record lookup; sub-10ms |
