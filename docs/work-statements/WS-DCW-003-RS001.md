# WS-DCW-003-RS001: Fix Missing Input Document Assembly in Project Orchestrator

**Remediates:** WS-DCW-003 (Rewrite software_product_development POW for WP/WS Ontology)
**Work Package:** WP-DCW-001
**Status:** Draft
**Scope:** Single-commit
**Allowed Paths:** `app/domain/workflow/project_orchestrator.py`, `combine-config/document_types/`, `tests/tier1/workflow/`

---

## Remediation Context

WS-DCW-003 rewrote the `software_product_development` POW definition with correct step
ordering (ADR-053) and declared `inputs[]` arrays on each step. The POW definition correctly
declares that the `implementation_plan` step requires `project_discovery` and
`implementation_plan_primary` as inputs. However, the Project Orchestrator's
`_start_document_production()` method — which is the runtime execution path for POW steps —
was not updated to resolve those declared inputs from the database. It passes an empty
`initial_context` to every DCW it starts, meaning no LLM step receives its required input
documents.

**Observed failure:** The IPF (implementation_plan) step produced a complaint message instead
of a plan:

> "the extracted context shows empty input_documents. I cannot proceed without these
> required inputs"

The IPF's package.yaml listed `primary_implementation_plan` and `technical_architecture` as
required inputs, but under ADR-053 ordering (IPP -> IPF -> TA), TA doesn't exist yet when
IPF runs. The LLM received no input documents at all — not even the ones that should have
been available.

**Secondary issue:** The package.yaml `required_inputs` declarations are out of sync with
the POW step ordering from ADR-053:

- **IPF package.yaml** lists `technical_architecture` as required, but TA runs *after* IPF.
  Must be removed from `required_inputs`.
- **TA package.yaml** lists `project_discovery` and `primary_implementation_plan` as required,
  but the POW definition says TA also receives `implementation_plan` (IPF output).
  Must be added to `required_inputs`.

## Root Cause

`app/domain/workflow/project_orchestrator.py:350` — `_start_document_production()`:

```python
state = await executor.start_execution(
    project_id=project_id,
    document_type=document_type,
    initial_context={},          # <-- BUG: always empty
)
```

Every other execution start point in the codebase correctly loads input documents:
- `app/api/v1/routers/document_workflows.py:259-280` — loads from DB, passes as `initial_context["input_documents"]`
- `app/api/v1/routers/production.py:255-280` — same pattern
- `app/domain/services/backlog_pipeline.py:478` — same pattern
- `app/domain/services/fanout_service.py:352` — same pattern

## Prohibited Actions

- Do not modify `PlanExecutor.start_execution()` signature or behavior
- Do not modify the POW definition
- Do not add input assembly logic to `PlanExecutor._build_context()` (the context builder should remain a consumer, not a loader)
- Do not change other execution start points (they already work correctly)

## Procedure

### Step 1: Write reproducing test (Bug-First Testing Rule)

**File:** `tests/tier1/workflow/test_project_orchestrator_inputs.py`

Write a failing test that proves `_start_document_production` passes empty `initial_context`
when it should contain input documents. Verify the test fails before proceeding.

Tests (all Tier-1, in-memory, no DB):

1. **test_start_document_production_loads_input_documents** — Mock DB to return input documents; verify `executor.start_execution()` is called with `initial_context["input_documents"]` containing the loaded documents.

2. **test_start_document_production_warns_on_missing_input** — Mock DB to return None for a required input; verify execution still starts (with warning), and `input_documents` dict reflects the missing entry.

3. **test_start_document_production_no_inputs_required** — For a document type with no `requires_inputs`, verify `initial_context` still has `{"input_documents": {}}`.

Use `unittest.mock.AsyncMock` for DB session and `MagicMock` for plan registry.
Mock `create_llm_executors` and `PlanExecutor` to avoid real LLM/DB calls.

Run: `python3 -m pytest tests/tier1/workflow/test_project_orchestrator_inputs.py -v`
Verify: Test 1 MUST fail (proving the bug exists).

### Step 2: Fix `_start_document_production` in project_orchestrator.py

**File:** `app/domain/workflow/project_orchestrator.py`

In `_start_document_production()` (line 316), before `executor.start_execution()`:

1. Look up the workflow plan via `get_plan_registry().get_by_document_type(document_type)`
2. If `plan.requires_inputs` is non-empty, resolve `project_id` to a UUID (reuse the pattern from `_get_stabilized_documents` at line 199-208)
3. For each required input type, query the DB for the latest document:
   ```python
   select(Document)
       .where(Document.space_type == "project")
       .where(Document.space_id == project_uuid)
       .where(Document.doc_type_id == required_type)
       .where(Document.is_latest == True)
   ```
4. Build `initial_context = {"input_documents": input_documents}`
5. Log warnings for missing inputs (don't crash — the orchestrator may be in partial production where not all inputs exist yet; the LLM will fail gracefully)

Follow the pattern from `production.py:255-280` (warning on missing inputs rather than hard error), since the orchestrator may intentionally attempt production before all inputs are ready.

### Step 3: Extract UUID resolution to a shared helper

The UUID resolution logic (try UUID parse, fall back to project_id lookup) is duplicated
in `_get_stabilized_documents`. Extract it to a private `_resolve_project_uuid()` method
and call it from both `_get_stabilized_documents` and `_start_document_production`.

### Step 4: Fix package.yaml input declarations (ADR-053 alignment)

**File:** `combine-config/document_types/implementation_plan/releases/1.0.0/package.yaml`

Remove `technical_architecture` from `required_inputs`. Under ADR-053, IPF runs before TA.
Result:
```yaml
required_inputs:
  - primary_implementation_plan
```

**File:** `combine-config/document_types/technical_architecture/releases/1.0.0/package.yaml`

Add `implementation_plan` to `required_inputs`. The POW definition (lines 140-153) declares
TA receives PD + IPP + IPF as inputs, but the package.yaml only lists PD + IPP.
Result:
```yaml
required_inputs:
  - project_discovery
  - primary_implementation_plan
  - implementation_plan
```

### Step 5: Verify

Run tests and confirm the reproducing test now passes:
```bash
ruff check app/domain/workflow/project_orchestrator.py tests/tier1/workflow/test_project_orchestrator_inputs.py
python3 -m pytest tests/tier1/workflow/test_project_orchestrator_inputs.py -v
python3 -m pytest tests/ -q --tb=short
```

## Verification Criteria

- [ ] Reproducing test written and verified to fail BEFORE fix applied
- [ ] `_start_document_production` loads required input documents from DB
- [ ] Input documents are passed in `initial_context["input_documents"]`
- [ ] Missing inputs produce a warning log, not a crash
- [ ] UUID resolution is shared between `_get_stabilized_documents` and `_start_document_production`
- [ ] IPF package.yaml `required_inputs` no longer includes `technical_architecture`
- [ ] TA package.yaml `required_inputs` includes `implementation_plan`
- [ ] All 3 new tests pass
- [ ] Full test suite passes (2347+ passed, 0 failed)
- [ ] ruff check passes on changed files
