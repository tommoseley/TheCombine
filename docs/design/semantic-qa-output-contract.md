# Semantic QA Output Contract (Normative)

## Purpose

A single LLM call returns a machine-parseable compliance report that:

1. Evaluates every bound constraint exactly once (coverage)
2. Reports violations (findings)
3. Produces an overall gate decision
4. Provides evidence pointers as JSONPaths into the generated document

## Schema Location

`seed/schemas/qa_semantic_compliance_output.v1.json`

---

## Contract Rules (Normative)

These rules are enforced by the parser and must be reflected in the policy prompt.

### Rule 1: Coverage Completeness

- `coverage.expected_count` MUST equal the count of bound constraints provided in the semantic QA call
- `coverage.items` MUST contain exactly one entry per provided bound constraint id
- `summary.expected_constraints` MUST equal `coverage.expected_count`
- `summary.evaluated_constraints` MUST equal `coverage.evaluated_count`
- `coverage.evaluated_count` MUST equal the number of `coverage.items[]` where `status != "not_evaluated"`

### Rule 2: Gate Decision

| Condition | Gate |
|-----------|------|
| Any `coverage.items[].status` is `"contradicted"` | MUST be `"fail"` |
| Any `coverage.items[].status` is `"reopened"` | MUST be `"fail"` |
| Any `coverage.items[].status` is `"missing"` for a must-binding | MUST be `"fail"` |
| Any `coverage.items[].status` is `"missing"` for an exclusion | MUST be `"fail"` |
| All statuses are `"satisfied"` or `"not_evaluated"` only | MAY be `"pass"` |

### Rule 3: Findings Consistency

For every coverage item, the corresponding finding must exist:

| Coverage Status | Required Finding |
|-----------------|------------------|
| `"contradicted"` | `{ severity: "error", code: "BOUND_CONTRADICTION" }` |
| `"reopened"` | `{ severity: "error", code: "BOUND_REOPENED" }` |
| `"missing"` | `{ severity: "error" or "warning", code: "BOUND_MISSING_EXPLICIT" }` |
| `"not_evaluated"` | `{ severity: "warning", code: "TRACEABILITY_GAP" }` |
| `"satisfied"` | No finding required |

### Rule 4: Constraint ID Validity

- `findings[].constraint_id` MUST be one of the provided bound constraint ids
- No hallucinated constraint ids are permitted
- Parser MUST reject findings with unknown constraint ids

### Rule 5: Evidence Pointers Required

- Every finding MUST include at least one `evidence_pointers` entry (`minItems: 1`)
- Coverage items SHOULD include evidence pointers when available (`minItems: 0`)

### Rule 6: Summary Counts

- `summary.errors` MUST equal count of findings with `severity: "error"`
- `summary.warnings` MUST equal count of findings with `severity: "warning"`
- `summary.infos` MUST equal count of findings with `severity: "info"`

---

## Evidence Pointer Format

Evidence pointers are JSONPath strings referencing locations in the evaluated document or input payload.

### Document Paths (Preferred)

```
$.known_constraints[0].constraint
$.known_constraints[2].source
$.unknowns[1].question
$.assumptions[0].assumption
$.early_decision_points[0].decision
$.recommendations[1].recommendation
$.summary
```

### Input Payload Paths (When Needed)

```
$.pgc_questions[3].id
$.pgc_answers.PLATFORM_TARGET
$.invariants[1].normalized_text
```

---

## Coverage Status Definitions

| Status | Definition | Gate Impact |
|--------|------------|-------------|
| `satisfied` | Constraint is honored in the document | None |
| `missing` | Constraint is not explicitly stated | Fail (for must-bindings and exclusions) |
| `contradicted` | Constraint is directly violated | Always fail |
| `reopened` | Decision is questioned or challenged | Always fail |
| `not_evaluated` | Cannot confidently classify due to ambiguity | Warning only |

### When to Use `not_evaluated`

Use only when the validator cannot confidently classify the constraint:

- Constraint text is malformed or empty
- Evidence is contradictory or too vague to classify
- Document schema mismatch prevents locating required sections

`not_evaluated` does not fail the gate by itself but produces a `TRACEABILITY_GAP` warning.

---

## Finding Codes

| Code | Meaning | Typical Severity |
|------|---------|------------------|
| `BOUND_CONTRADICTION` | Constraint directly violated | error |
| `BOUND_REOPENED` | Decision questioned/challenged in unknowns or questions | error |
| `BOUND_MISSING_EXPLICIT` | Required constraint not stated in document | error |
| `PROMOTION_RULE_VIOLATION` | Should-answer promoted to known_constraint | error |
| `INVENTED_CONSTRAINT` | Constraint in document not traceable to input | warning |
| `TRACEABILITY_GAP` | Cannot evaluate constraint | warning |
| `OTHER` | Edge cases only; use sparingly | varies |

---

## Semantic Distinction: Follow-up vs. Reopening

The key semantic check that mechanical validation cannot perform:

### ALLOWED (Follow-up within decision)

Questions that accept the decision and ask for details:

- "How many family members will use the app?" (follows DEPLOYMENT_CONTEXT=family)
- "What number ranges for addition?" (follows MATH_SCOPE=addition)
- "What age groups in the family?" (follows DEPLOYMENT_CONTEXT=family)

### ERROR (Reopens the decision)

Questions that challenge or revisit the decision itself:

- "Should we consider classroom use instead?" (reopens DEPLOYMENT_CONTEXT)
- "Which math operations should we support?" (reopens MATH_SCOPE)
- "Would the app work better for schools?" (reopens DEPLOYMENT_CONTEXT)

**Key distinction:** Follow-up questions operate within the bounds of the decision. Reopening questions challenge whether the decision was correct.

---

## Parser Validation Requirements

The parser MUST reject responses that violate:

1. Wrong `schema_version` value
2. `coverage.expected_count` != actual constraint count provided
3. Missing coverage item for any provided constraint
4. Finding with `constraint_id` not in provided constraints
5. Finding without `evidence_pointers` (empty array)
6. `gate: "pass"` when any status is `"contradicted"` or `"reopened"`
7. Inconsistency between `summary` counts and actual findings

---

## Example Valid Output

```json
{
  "schema_version": "qa_semantic_compliance_output.v1",
  "correlation_id": "exec-abc123",
  "gate": "pass",
  "summary": {
    "errors": 0,
    "warnings": 1,
    "infos": 0,
    "expected_constraints": 4,
    "evaluated_constraints": 4,
    "blocked_reasons": []
  },
  "coverage": {
    "expected_count": 4,
    "evaluated_count": 4,
    "items": [
      {
        "constraint_id": "DEPLOYMENT_CONTEXT",
        "status": "satisfied",
        "evidence_pointers": ["$.known_constraints[0].constraint"]
      },
      {
        "constraint_id": "MATH_SCOPE",
        "status": "satisfied",
        "evidence_pointers": ["$.known_constraints[1].constraint"]
      },
      {
        "constraint_id": "EXISTING_SYSTEMS",
        "status": "satisfied",
        "evidence_pointers": ["$.known_constraints[2].constraint"],
        "notes": "Exclusion correctly restated as 'No integrations required'"
      },
      {
        "constraint_id": "PROGRESS_FEATURES",
        "status": "satisfied",
        "evidence_pointers": ["$.recommendations[0].recommendation"]
      }
    ]
  },
  "findings": [
    {
      "severity": "warning",
      "code": "INVENTED_CONSTRAINT",
      "constraint_id": "PROGRESS_FEATURES",
      "message": "Document adds 'gamification' not mentioned in user answers",
      "evidence_pointers": ["$.recommendations[2].recommendation"],
      "suggested_fix": "Remove gamification or move to assumptions with low confidence"
    }
  ],
  "meta": {
    "model": "claude-sonnet-4-20250514",
    "prompt_version": "qa_semantic_compliance_v1.0",
    "policy_version": "1.0",
    "latency_ms": 1842,
    "input_tokens": 3200,
    "output_tokens": 450
  }
}
```

---

## Example Failing Output

```json
{
  "schema_version": "qa_semantic_compliance_output.v1",
  "correlation_id": "exec-def456",
  "gate": "fail",
  "summary": {
    "errors": 2,
    "warnings": 0,
    "infos": 0,
    "expected_constraints": 3,
    "evaluated_constraints": 3,
    "blocked_reasons": [
      "DEPLOYMENT_CONTEXT reopened in unknowns",
      "CURRICULUM_ALIGNMENT promoted from should to constraint"
    ]
  },
  "coverage": {
    "expected_count": 3,
    "evaluated_count": 3,
    "items": [
      {
        "constraint_id": "DEPLOYMENT_CONTEXT",
        "status": "reopened",
        "evidence_pointers": ["$.unknowns[0].question"]
      },
      {
        "constraint_id": "MATH_SCOPE",
        "status": "satisfied",
        "evidence_pointers": ["$.known_constraints[0].constraint"]
      },
      {
        "constraint_id": "CURRICULUM_ALIGNMENT",
        "status": "contradicted",
        "evidence_pointers": ["$.known_constraints[2].constraint"],
        "notes": "Was should-priority answer but appears as binding constraint"
      }
    ]
  },
  "findings": [
    {
      "severity": "error",
      "code": "BOUND_REOPENED",
      "constraint_id": "DEPLOYMENT_CONTEXT",
      "message": "Unknown question 'Should we target schools instead?' reopens family deployment decision",
      "evidence_pointers": ["$.unknowns[0].question"],
      "suggested_fix": "Remove question or rephrase as follow-up within family context"
    },
    {
      "severity": "error",
      "code": "PROMOTION_RULE_VIOLATION",
      "constraint_id": "CURRICULUM_ALIGNMENT",
      "message": "Should-priority answer promoted to known_constraints",
      "evidence_pointers": ["$.known_constraints[2].constraint"],
      "suggested_fix": "Move to assumptions with medium confidence"
    }
  ],
  "meta": {
    "model": "claude-sonnet-4-20250514",
    "prompt_version": "qa_semantic_compliance_v1.0",
    "policy_version": "1.0",
    "latency_ms": 2103,
    "input_tokens": 3400,
    "output_tokens": 520
  }
}
```

---

## Related Documents

- `docs/design/QA Validation Writeup.md` - Problem analysis and architectural rationale
- `docs/work-statements/ws-semantic-qa-001.md` - Implementation work statement
- `seed/prompts/tasks/qa_semantic_compliance_v1.0.txt` - Policy prompt (to be created)

---

_Last updated: 2026-01-26_
