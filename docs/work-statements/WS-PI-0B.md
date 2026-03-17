# WS-PI-0B — LLM Replay Override and Structured Evaluation Harness

**Status:** Accepted
**Accepted:** 2026-03-17
**Parent WP:** WP-PI (Process Improvement Iteration Loop)

## Objective

Extend the existing LLM replay infrastructure with controlled override support, run selection queries, and a structured defect evaluator — enabling measured A/B comparison for station-level process improvement of WS-generation runs.

## Scope

### In Scope
- Extend `POST /api/admin/llm-runs/{run_id}/replay` with optional overrides (system_prompt, temperature, max_tokens)
- Add `GET /api/admin/llm-runs` query endpoint filtered by project_id, artifact_type, prompt_id, prompt_version, status
- Build structured WS defect evaluator with explicit check contract (pass/fail/advisory/not_evaluable)
- Add `POST /api/admin/llm-runs/{run_id}/evaluate` endpoint for defect evaluation of stored output without LLM re-execution
- Add `POST /api/admin/llm-runs/batch-replay` for replaying multiple runs with the same overrides, returning per-run evaluations + aggregate counts
- Preserve full audit trail: overrides tagged in replay metadata, original and replay runs separately auditable

### Out of Scope
- user_prompt_override (invocation boundary is assembled messages/context, not a single user prompt — defer until replay surface is better understood)
- Schema override (no clean injection point identified at prompt assembly boundary — defer to later WS)
- Evaluators for non-WS artifact types (TA, PD, etc.)
- Workflow-level replay (multi-node)
- UI for replay/comparison
- Schema changes to `llm_run` tables
- Prompt authoring or versioning changes

## Inputs
- Existing replay endpoint: `app/api/routers/admin.py:234-360`
- LLM run model: `app/api/models/llm_log.py:28-60`
- Reconstruct inputs helper: `app/api/routers/admin.py:53-85`
- Defect catalog from WS-PI-0A (prerequisite — defines check categories)

## Procedure

### Step 1: Add ReplayOverrides request model
- Add `ReplayOverridesRequest` Pydantic model:
  - `system_prompt_override: Optional[str]`
  - `temperature: Optional[float]`
  - `max_tokens: Optional[int]`
- Add to response comparison metadata: `overrides_applied` dict

### Step 2: Extend replay endpoint
- Change `replay_llm_run` to accept optional `ReplayOverridesRequest` body
- After `reconstruct_inputs`, swap `system_prompt` if override provided
- Use override temperature/max_tokens if provided, else pull from original run metadata, else current defaults
- Tag replay `metadata` with `overrides_applied: {field: "original_hash -> override_hash"}`
- Existing no-override behavior must remain unchanged — clients calling with no request body continue to function identically

### Step 3: Add run selection query endpoint
- `GET /api/admin/llm-runs` with query params: `project_id`, `artifact_type`, `prompt_id`, `prompt_version`, `status`, `limit`, `offset`
- Prompt filters apply where `prompt_id`/`prompt_version` are present in logged data; runs lacking these fields are excluded from prompt-filtered queries, included in unfiltered queries
- Return list of run summaries (id, artifact_type, prompt_id, prompt_version, status, started_at, token counts)
- Default limit 50, max 200

### Step 4: Build WS defect evaluator
- Create `app/domain/services/ws_defect_evaluator.py`
- Input: parsed JSON output from a WS-generation LLM run
- Output contract per check:
  ```
  check_id: str
  status: "pass" | "fail" | "advisory" | "not_evaluable"
  evidence: str
  notes: str
  ```
- Output summary:
  ```
  evaluation_report:
    artifact_type: "work_statement"
    evaluator_version: "1.0"
    checks: [...]
    summary:
      passed: int
      failed: int
      advisory: int
      not_evaluable: int
  ```
- Checks (aligned to 0a defect categories):
  - `governance_pins_populated` — ta_version_id present and non-empty, policy_refs present and non-empty. Status: pass/fail.
  - `required_sections_present` — objective, scope, procedure, verification_criteria, allowed_paths, prohibited_actions, governance_pins all exist. Status: pass/fail.
  - `tests_before_implementation` — scan procedure steps, verify test steps precede implementation steps. Status: pass/fail.
  - `step_grounding_heuristic` — flags steps lacking observable grounding cues in reconstructed input context. Status: **advisory**. This is a heuristic signal, not a truth detector.
  - `contradiction_disclosure_present` — checks whether explicit contradiction/conflict notes are present in the output when the output claims unresolved or conflicting inputs. Status: pass/not_evaluable. This is a disclosure check, not a truth check.

### Step 5: Add evaluate endpoint
- `POST /api/admin/llm-runs/{run_id}/evaluate` — loads stored output, parses JSON, runs defect evaluator
- Returns evaluation_report
- No LLM call, no token cost

### Step 6: Add batch replay endpoint
- `POST /api/admin/llm-runs/batch-replay` with body: `run_ids: list[UUID]`, `overrides: ReplayOverridesRequest`
- Executes replay sequentially (avoids rate limits)
- Returns:
  - Per-run: comparison result + evaluation_report
  - Aggregate: counts by check_id across all runs (passed/failed/advisory/not_evaluable)

### Step 7: Tests
- Tier-1 unit tests for `ws_defect_evaluator` with known-good and known-bad WS JSON fixtures
- Tier-1 tests for override application logic (overrides applied correctly, metadata tagged, no-override path unchanged)
- Tier-2 tests for query endpoint filtering

## Verification Criteria
- Replay with no overrides produces identical behavior to current endpoint
- Existing replay clients with no request body continue to function unchanged
- Replay with system_prompt override: input token count differs, metadata shows `overrides_applied`
- Query endpoint returns correct runs filtered by artifact_type + project_id
- Query endpoint with prompt_id filter excludes runs lacking prompt_id, includes matching runs
- Defect evaluator correctly identifies: empty governance_pins, missing sections, tests-after-implementation
- `step_grounding_heuristic` returns advisory status, not blocking fail
- `contradiction_disclosure_present` returns pass or not_evaluable, never fail
- Evaluation of a stored original run works without replay
- Replayed run can be evaluated in the same flow
- Original and replay runs remain separately auditable in the database
- Batch replay returns per-run evaluations + aggregate counts by check_id
- All existing admin endpoint tests still pass

## Allowed Paths
- `app/api/routers/admin.py`
- `app/domain/services/ws_defect_evaluator.py` (new)
- `tests/tier1/test_ws_defect_evaluator.py` (new)
- `tests/tier1/test_replay_overrides.py` (new)
- `tests/tier2/test_admin_query.py` (new)

## Prohibited Actions
- Do not modify `llm_run`, `llm_content`, or `llm_run_input_ref` table schemas
- Do not modify the LLM execution logger or logging behavior
- Do not add evaluators for non-WS artifact types
- Do not add user_prompt_override or schema_override
- Do not add UI routes or templates
- Do not modify seed prompts or schemas

## Governance Pins
- `parent_wp`: WP-PI (Process Improvement Iteration Loop)
- `policy_refs`: POL-WS-001, POL-QA-001
- `predecessor`: WS-PI-0A (Defect Catalog)
- `artifact_focus`: Station-level process improvement for WS-generation runs

## Definition of Done
- Override replay works: same inputs + different system prompt = measurable output difference
- Run selection works: can query "all WS-generation runs for project X"
- Defect evaluator works: produces structured pass/fail/advisory/not_evaluable report for any WS output
- Batch replay works: replay N runs with overrides, get per-run evaluations + aggregate improvement score
- All tests pass, Tier 0 clean
