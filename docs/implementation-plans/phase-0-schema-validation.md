# Implementation Plan: Phase 0 - Schema & Validation

**Date:** 2026-01-02  
**Target Duration:** 1-2 days  
**Status:** Ready to begin  
**Revision:** 1.1 (incorporated feedback)

---

## Objective

Build fail-fast validation infrastructure before any execution logic exists.

**Exit Criteria:**
- Can load and validate a workflow definition
- Can reject invalid workflows with actionable errors

---

## Governing Documents

| Document | Location | Purpose |
|----------|----------|---------|
| MVP Roadmap | docs/MVP-Roadmap.md | Phase definition |
| ADR-011 | docs/adr/011-document-ownership-model/ | Ownership rules to enforce |
| ADR-027 | docs/adr/027-workflow-definition/ | Workflow structure spec |
| Implementation Model | docs/adr/027-workflow-definition/ADR-027-Implementation-Model.md | Reference code |

---

## Deliverables

| # | Deliverable | Location |
|---|-------------|----------|
| D1 | Workflow JSON Schema | seed/schemas/workflow.v1.json |
| D2 | WorkflowValidator | app/domain/workflow/validator.py |
| D3 | Scope hierarchy helper | app/domain/workflow/scope.py |
| D4 | Validation result types | app/domain/workflow/types.py |
| D5 | Unit tests | tests/domain/workflow/test_validator.py |
| D6 | Sample workflow (valid) | seed/workflows/software_product_development.v1.json |
| D7 | Test fixtures (invalid) | tests/fixtures/workflows/ |

---

## Design Decisions (from feedback)

### A. Schema Extensibility

Use `additionalProperties: true` on:
- document_types[*]
- entity_types[*]
- steps[*]

**Rationale:** v2/v3 workflows will need metadata we cannot predict. Validation enforces structure, not future semantics.

### B. Acceptance Fields as Schema Contract

`accepted_by` is only valid when `acceptance_required: true`.

Enforce via JSON Schema conditional (if/then or dependentSchemas), not semantic validation. Human gating is a declared contract, not a runtime discovery.

### C. Generic Scope Graph

Scopes are declared in the workflow, not hardcoded in the validator.

```json
"scopes": {
  "project": { "parent": null },
  "epic": { "parent": "project" },
  "story": { "parent": "epic" }
}
```

**Rationale:** Keeps ADR-011 truly generic. Prepares for organization-level scopes, cross-project references, global reference material.

### D. Prompt Reference Validation

Validate that task_prompt and role strings:
1. Conform to naming pattern (e.g., "Story Backlog v1.0")
2. Exist in seed/manifest.json (without loading contents)

**Rationale:** Catches typos early, enforces governed artifacts, avoids runtime failures.

---

## Task Breakdown

### Task 1: Create Directory Structure

**Duration:** 5 minutes

```
app/domain/workflow/
    __init__.py
    validator.py
    scope.py
    types.py

seed/workflows/

tests/domain/workflow/
    __init__.py
    test_validator.py

tests/fixtures/workflows/
```

**Acceptance:** Directories exist, __init__.py files in place.

---

### Task 2: Define Validation Result Types (D4)

**Duration:** 15 minutes  
**File:** app/domain/workflow/types.py

ValidationErrorCode enum values:
- SCHEMA_INVALID
- MISSING_REQUIRED_FIELD
- UNKNOWN_DOCUMENT_TYPE
- UNKNOWN_ENTITY_TYPE
- UNKNOWN_SCOPE
- OWNERSHIP_CYCLE
- SCOPE_MISMATCH
- INVALID_SCOPE_HIERARCHY
- INVALID_REFERENCE
- MISSING_ITERATION_SOURCE
- FORBIDDEN_SIBLING_REFERENCE
- FORBIDDEN_DESCENDANT_REFERENCE
- FORBIDDEN_CROSS_BRANCH_REFERENCE
- INVALID_PROMPT_FORMAT
- PROMPT_NOT_IN_MANIFEST

Also define:
- ValidationError dataclass (code, message, path)
- ValidationResult dataclass (valid, errors)

**Acceptance:** Types compile, can be imported.

---

### Task 3: Create Workflow JSON Schema (D1)

**Duration:** 45-60 minutes  
**File:** seed/schemas/workflow.v1.json

**Top-level structure:**
- schema_version (required, const: "workflow.v1")
- workflow_id (required, string)
- revision (required, string)
- effective_date (required, ISO date format)
- name (required, string)
- description (optional, string)
- scopes (required, object) -- NEW
- document_types (required, object)
- entity_types (required, object)
- steps (required, array)

**Scopes structure (NEW):**
```json
"scopes": {
  "type": "object",
  "minProperties": 1,
  "additionalProperties": {
    "type": "object",
    "properties": {
      "parent": { "type": ["string", "null"] }
    },
    "required": ["parent"]
  }
}
```

**Document type structure:**
- name (required, string)
- scope (required, string - references scopes key)
- may_own (required, array of entity type IDs)
- collection_field (optional, string)
- acceptance_required (optional, boolean, default false)
- accepted_by (optional, array of strings)
- additionalProperties: true -- EXTENSIBILITY

**Conditional: accepted_by requires acceptance_required (NEW)**
Use dependentSchemas:
```json
"dependentSchemas": {
  "accepted_by": {
    "properties": {
      "acceptance_required": { "const": true }
    },
    "required": ["acceptance_required"]
  }
}
```

**Entity type structure:**
- name (required, string)
- parent_doc_type (required, string)
- creates_scope (required, string)
- additionalProperties: true -- EXTENSIBILITY

**Step structure (production step):**
- step_id (required, string)
- role (required, string)
- task_prompt (required, string)
- produces (required, string)
- scope (required, string)
- inputs (required, array)
- additionalProperties: true -- EXTENSIBILITY

**Step structure (iteration block):**
- step_id (required, string)
- iterate_over (required, object)
- scope (required, string)
- steps (required, array - recursive)
- additionalProperties: true -- EXTENSIBILITY

Use oneOf to enforce mutual exclusion between production step and iteration block.

**Input reference structure:**
- Exactly one of: doc_type OR entity_type
- scope (required, string)
- required (optional, boolean, default true)
- context (optional, boolean, default false)

**Acceptance:** Schema validates sample workflow; rejects invalid structures.

---

### Task 4: Implement Scope Hierarchy Helper (D3)

**Duration:** 25 minutes  
**File:** app/domain/workflow/scope.py

ScopeHierarchy class with:
- Constructor taking scope_definitions (workflow["scopes"])
- from_workflow() class method
- is_valid_scope(scope) method
- get_parent(scope) method
- is_ancestor(maybe_ancestor, of_scope) method
- is_descendant(maybe_descendant, of_scope) method
- get_root_scopes() method
- _validate_no_cycles() internal method

**Key point:** Does NOT hardcode project/epic/story. Derives all relationships from workflow["scopes"].

**Acceptance:** Unit tests pass for ancestor/descendant checks, cycle detection, unknown scope handling.

---

### Task 5: Implement WorkflowValidator (D2)

**Duration:** 1.5-2 hours  
**File:** app/domain/workflow/validator.py

**Validation checks (15 total):**

| # | Check | Error Code | Source |
|---|-------|------------|--------|
| V1 | JSON Schema conformance | SCHEMA_INVALID | ADR-027 |
| V2 | Scope hierarchy is acyclic | INVALID_SCOPE_HIERARCHY | ADR-011 |
| V3 | All doc_type.scope reference valid scopes | UNKNOWN_SCOPE | ADR-027 |
| V4 | All entity_type.creates_scope reference valid scopes | UNKNOWN_SCOPE | ADR-027 |
| V5 | All step.produces reference valid doc types | UNKNOWN_DOCUMENT_TYPE | ADR-027 |
| V6 | All may_own reference valid entity types | UNKNOWN_ENTITY_TYPE | ADR-027 |
| V7 | Ownership graph is acyclic (DAG) | OWNERSHIP_CYCLE | ADR-011 |
| V8 | Step scope matches produced doc scope | SCOPE_MISMATCH | ADR-011 |
| V9 | Iteration sources exist and have collections | MISSING_ITERATION_SOURCE | ADR-027 |
| V10 | Input references resolve to valid docs/entities | INVALID_REFERENCE | ADR-027 |
| V11 | Reference rules: same-scope only if context | FORBIDDEN_SIBLING_REFERENCE | ADR-011 |
| V12 | Reference rules: no descendant refs | FORBIDDEN_DESCENDANT_REFERENCE | ADR-011 |
| V13 | Reference rules: no cross-branch refs | FORBIDDEN_CROSS_BRANCH_REFERENCE | ADR-011 |
| V14 | Prompt names match pattern | INVALID_PROMPT_FORMAT | Governance |
| V15 | Prompts exist in manifest | PROMPT_NOT_IN_MANIFEST | Governance |

**Prompt validation (V14, V15):**
- Pattern: ^[\w\s]+ v\d+\.\d+$ (e.g., "Story Backlog v1.0")
- Check presence in seed/manifest.json without loading prompt contents
- Include JSON path in errors (e.g., "steps[2].task_prompt")

**Implementation structure:**
- Constructor loads JSON schema and manifest paths
- validate(workflow) returns ValidationResult
- Fail fast on schema errors (V1) and scope cycles (V2)
- Collect all other semantic errors

**Acceptance:** All 15 validation checks implemented, unit tests pass.

---

### Task 6: Create Sample Valid Workflow (D6)

**Duration:** 30 minutes  
**File:** seed/workflows/software_product_development.v1.json

Based on ADR-027 Implementation Model with scopes section added:

```json
{
  "schema_version": "workflow.v1",
  "workflow_id": "software_product_development",
  "revision": "wfrev_2026_01_02_a",
  "effective_date": "2026-01-02",
  "name": "Software Product Development",
  
  "scopes": {
    "project": { "parent": null },
    "epic": { "parent": "project" },
    "story": { "parent": "epic" }
  },
  
  "document_types": { ... },
  "entity_types": { ... },
  "steps": [ ... ]
}
```

Must include:
- 5 document types
- 2 entity types
- 3 scopes
- Nested iteration blocks
- Mix of acceptance_required true/false
- Cross-scope references

**Acceptance:** Validator returns ValidationResult(valid=True).

---

### Task 7: Create Invalid Workflow Fixtures (D7)

**Duration:** 45 minutes  
**Directory:** tests/fixtures/workflows/

| Fixture | Tests Error Code |
|---------|------------------|
| invalid_schema.json | SCHEMA_INVALID |
| scope_cycle.json | INVALID_SCOPE_HIERARCHY |
| unknown_scope.json | UNKNOWN_SCOPE |
| unknown_doc_type.json | UNKNOWN_DOCUMENT_TYPE |
| unknown_entity_type.json | UNKNOWN_ENTITY_TYPE |
| ownership_cycle.json | OWNERSHIP_CYCLE |
| scope_mismatch.json | SCOPE_MISMATCH |
| missing_iteration_source.json | MISSING_ITERATION_SOURCE |
| invalid_reference.json | INVALID_REFERENCE |
| forbidden_sibling_ref.json | FORBIDDEN_SIBLING_REFERENCE |
| forbidden_descendant_ref.json | FORBIDDEN_DESCENDANT_REFERENCE |
| forbidden_cross_branch_ref.json | FORBIDDEN_CROSS_BRANCH_REFERENCE |
| invalid_prompt_format.json | INVALID_PROMPT_FORMAT |
| prompt_not_in_manifest.json | PROMPT_NOT_IN_MANIFEST |
| accepted_by_without_required.json | SCHEMA_INVALID (conditional) |

Each fixture should be minimal.

**Acceptance:** Each fixture triggers exactly its expected error.

---

### Task 8: Write Unit Tests (D5)

**Duration:** 1 hour  
**File:** tests/domain/workflow/test_validator.py

**Test cases:**

TestWorkflowValidator:
- test_valid_workflow_passes
- test_schema_invalid_rejected
- test_accepted_by_requires_acceptance_required
- test_scope_cycle_rejected
- test_unknown_scope_rejected
- test_unknown_doc_type_rejected
- test_unknown_entity_type_rejected
- test_ownership_cycle_rejected
- test_scope_mismatch_rejected
- test_missing_iteration_source_rejected
- test_ancestor_reference_permitted
- test_same_scope_context_permitted
- test_sibling_reference_forbidden
- test_descendant_reference_forbidden
- test_cross_branch_reference_forbidden
- test_invalid_prompt_format_rejected
- test_prompt_not_in_manifest_rejected
- test_error_includes_path
- test_multiple_errors_collected

TestScopeHierarchy:
- test_is_ancestor
- test_is_descendant
- test_cycle_detection
- test_multiple_roots_allowed
- test_unknown_scope_handling

**Acceptance:** pytest tests/domain/workflow/ -v passes.

---

### Task 9: Update Manifest

**Duration:** 5 minutes

Add to seed/manifest.json:
- seed/schemas/workflow.v1.json
- seed/workflows/software_product_development.v1.json

Include SHA-256 hashes.

**Acceptance:** Manifest includes new files with correct hashes.

---

## Execution Order

```
Task 1 (directories)
    |
    +-- Task 2 (types) -------------+
    |                               |
    +-- Task 3 (JSON schema)        |
    |                               |
    +-- Task 4 (scope helper) ------+-- Task 5 (validator)
                                    |       |
                                    |       +-- Task 6 (valid workflow)
                                    |       |
                                    |       +-- Task 7 (invalid fixtures)
                                    |               |
                                    +---------------+-- Task 8 (tests)
                                                            |
                                                        Task 9 (manifest)
```

---

## Testing Strategy

**Tier-1 only** (per project constraints):
- All tests use in-memory fixtures
- No database, no external dependencies
- Pure unit tests on validator logic

**Coverage targets:**
- Every validation check (15 total) has at least one test
- Reference rule tests cover all four cases
- Prompt validation tests cover format and manifest checks

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Schema too rigid | additionalProperties: true on extensible objects |
| Validation errors unclear | Include JSON path in every error |
| Scope hardcoding | Derive from workflow["scopes"], no hardcoded values |
| Prompt typos slip through | Validate format + manifest presence |
| Cycle detection misses cases | Test with complex graphs |

---

## Definition of Done

Phase 0 is complete when:

1. workflow.v1.json schema exists with generic scopes and extensibility
2. WorkflowValidator implements all 15 checks
3. Sample workflow validates successfully
4. Each error type has a fixture that triggers it
5. All unit tests pass (validator + scope helper)
6. Manifest updated
7. Code committed and pushed

---

## Notes for Implementation

- Do NOT implement execution logic - validation only
- Do NOT load prompt contents - just check names against manifest
- Do NOT connect to database - pure in-memory validation
- DO fail fast on schema and scope cycle errors
- DO collect all other semantic errors
- DO include actionable JSON paths in errors
- DO use workflow["scopes"] - no hardcoded scope names

---

## Changes from v1.0

| Change | Rationale |
|--------|-----------|
| Added scopes section to schema | Generic scope graph per ADR-011 |
| Added additionalProperties: true | Future extensibility without schema churn |
| Added accepted_by conditional | Human gating as declared contract |
| Added V14, V15 prompt validation | Catch typos, enforce governed artifacts |
| Expanded test cases | Cover new validation checks |

---

_Implementation plan prepared: 2026-01-02_  
_Revision 1.1: Incorporated feedback on extensibility, generic scopes, prompt validation_
