# Work Statement: WS-SEMANTIC-QA-001

## Title
Implement Layer 2 LLM-based Semantic QA Validation

## Parent
ADR-042 (PGC Constraint Binding and Drift Prevention)

## Status
Draft

## Author
Tom Moseley

## Date
2026-01-26

---

## 1. Objective

Implement Layer 2 LLM-based semantic QA validation to detect constraint violations that require semantic understanding, complementing the existing mechanical (Layer 1) checks.

### Problem Statement

The current QA-PGC-002 (reopened decision detection) uses keyword/tag matching, which fundamentally cannot distinguish:
- "How many family members will use the app?" (valid follow-up question)
- "Should we target classroom use instead of family use?" (reopening the decision)

Both contain "family" from canonical_tags, but only the second is a violation. Keyword presence ≠ semantic intent.

### Solution

Add a semantic QA layer that:
1. Receives explicit policy rules (not implicit in code)
2. Evaluates each bound constraint for compliance
3. Returns structured, machine-parseable findings
4. Integrates with the existing QA feedback loop for remediation

---

## 2. Scope

### In Scope

1. **Simplify `constraint_drift_validator.py`**
   - Remove tag-based QA-PGC-002 detection (already disabled)
   - Keep only mechanical checks: schema validity, QA-PGC-001 (direct contradiction), QA-PGC-003/004 (warnings)
   - Clean up unused tag-matching code

2. **Create semantic QA output schema**
   - `seed/schemas/qa_semantic_compliance_output.v1.json`
   - Defines structured output contract for LLM responses

3. **Create semantic QA policy prompt**
   - `seed/prompts/tasks/qa_semantic_compliance_v1.0.txt`
   - Contains explicit policy rules for constraint evaluation
   - Includes output schema requirements

4. **Implement `_run_semantic_qa()` in `qa.py`**
   - Assemble 4 inputs: PGC questions, bound constraints, document, policy
   - Call LLM with structured output format
   - Parse and validate response against schema
   - Convert findings to existing feedback format

5. **Wire into QA node execution flow**
   - Run semantic QA after mechanical checks pass (warnings OK, errors block)
   - Merge semantic findings with mechanical findings
   - Feed combined feedback to remediation node

6. **Tests**
   - Tier-1 unit tests with mock LLM responses
   - Test schema validation of LLM output
   - Test finding-to-feedback conversion
   - Test gate logic (pass/fail based on errors)

### Out of Scope

- Database schema changes
- UI changes for displaying semantic QA results
- Changes to remediation node logic (uses existing feedback format)
- New LLM service infrastructure (uses existing `llm_service.complete()`)

---

## 3. Output Contract

### Schema: `qa_semantic_compliance_output.v1.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://thecombine.dev/schemas/qa_semantic_compliance_output.v1.json",
  "title": "QASemanticComplianceOutputV1",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "correlation_id",
    "gate",
    "summary",
    "coverage",
    "findings"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "qa_semantic_compliance_output.v1"
    },
    "correlation_id": {
      "type": "string",
      "minLength": 1,
      "description": "Workflow correlation id for traceability."
    },
    "gate": {
      "type": "string",
      "enum": ["pass", "fail"],
      "description": "Overall semantic QA gate decision."
    },
    "summary": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "errors",
        "warnings",
        "evaluated_constraints",
        "expected_constraints",
        "blocked_reasons"
      ],
      "properties": {
        "errors": { "type": "integer", "minimum": 0 },
        "warnings": { "type": "integer", "minimum": 0 },
        "evaluated_constraints": { "type": "integer", "minimum": 0 },
        "expected_constraints": { "type": "integer", "minimum": 0 },
        "blocked_reasons": {
          "type": "array",
          "description": "Human-readable reasons gate failed (if any).",
          "items": { "type": "string", "minLength": 1 }
        }
      }
    },
    "coverage": {
      "type": "object",
      "additionalProperties": false,
      "required": ["expected_count", "evaluated_count", "items"],
      "description": "Positive confirmation that each bound constraint was evaluated.",
      "properties": {
        "expected_count": { "type": "integer", "minimum": 0 },
        "evaluated_count": { "type": "integer", "minimum": 0 },
        "items": {
          "type": "array",
          "minItems": 0,
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["constraint_id", "status"],
            "properties": {
              "constraint_id": {
                "type": "string",
                "minLength": 1,
                "description": "Stable constraint/PGC question id (e.g., PLATFORM_TARGET)."
              },
              "status": {
                "type": "string",
                "enum": [
                  "satisfied",
                  "missing",
                  "contradicted",
                  "reopened",
                  "not_evaluated"
                ]
              },
              "evidence_pointers": {
                "type": "array",
                "items": { "type": "string", "minLength": 1 },
                "minItems": 0
              },
              "notes": {
                "type": "string",
                "maxLength": 300
              }
            }
          }
        }
      }
    },
    "findings": {
      "type": "array",
      "minItems": 0,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "severity",
          "code",
          "constraint_id",
          "message",
          "evidence_pointers"
        ],
        "properties": {
          "severity": {
            "type": "string",
            "enum": ["error", "warning", "info"]
          },
          "code": {
            "type": "string",
            "enum": [
              "BOUND_CONTRADICTION",
              "BOUND_REOPENED",
              "BOUND_MISSING_EXPLICIT",
              "PROMOTION_RULE_VIOLATION",
              "INVENTED_CONSTRAINT",
              "TRACEABILITY_GAP",
              "OTHER"
            ]
          },
          "constraint_id": {
            "type": "string",
            "minLength": 1
          },
          "message": {
            "type": "string",
            "minLength": 1
          },
          "evidence_pointers": {
            "type": "array",
            "items": { "type": "string", "minLength": 1 },
            "minItems": 0
          },
          "suggested_fix": {
            "type": "string"
          }
        }
      }
    },
    "meta": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "model": { "type": "string" },
        "prompt_version": { "type": "string" },
        "policy_version": { "type": "string" },
        "run_id": { "type": "string" },
        "latency_ms": { "type": "integer", "minimum": 0 }
      }
    }
  }
}
```

### Contract Rules (Enforced in Policy Prompt)

1. `coverage.expected_count` MUST equal the number of bound constraints provided
2. `coverage.evaluated_count` MUST equal count of `coverage.items` where `status != "not_evaluated"`
3. For every bound constraint provided, there MUST be exactly one `coverage.items[]` entry
4. If any `coverage.items[].status` is `contradicted` or `reopened`:
   - `gate` MUST be `"fail"`
   - There MUST be a corresponding `findings[]` entry with `severity="error"`
5. If any `coverage.items[].status` is `not_evaluated`:
   - Emit `TRACEABILITY_GAP` finding with `severity="warning"`
6. `findings[]` MUST be derivable from `coverage[]` + policy checks (no inconsistency)

---

## 4. Policy Document Structure

The semantic QA prompt MUST include explicit policy rules. The LLM applies policy, it does not decide policy.

### Policy Sections

```markdown
## Semantic QA Policy for Project Discovery Documents

### Section 1: MUST-Priority Bindings
Constraints where: binding=true AND (priority="must" OR constraint_kind="requirement")

- MUST appear in known_constraints OR as semantically equivalent statement
- MUST NOT be contradicted anywhere in document
- MUST NOT be questioned in unknowns, early_decision_points, or stakeholder_questions

### Section 2: SHOULD-Priority Answers
Questions where: priority="should" AND binding=false

- MAY inform assumptions, recommendations, or context
- MUST NOT appear in known_constraints (this is a PROMOTION_RULE_VIOLATION)
- If treated as immutable/binding fact → ERROR

### Section 3: Exclusions
Constraints where: binding=true AND invariant_kind="exclusion" AND answer="No"

- Topic MUST NOT be recommended for investigation or implementation
- Restating exclusion as fact is ALLOWED ("No accessibility requirements apply")
- Asking questions that reopen the exclusion is ERROR

### Section 4: Decision Reopening (Semantic Evaluation Required)

ALLOWED (follow-up within decision):
- "How many users?" → follows up on DEPLOYMENT_CONTEXT=family
- "What number ranges for addition?" → follows up on MATH_SCOPE=addition

ERROR (reopens the decision):
- "Should we consider classroom use?" → reopens DEPLOYMENT_CONTEXT
- "Which math operations should we support?" → reopens MATH_SCOPE

Key distinction: Follow-up questions accept the decision and ask for details.
Reopening questions challenge or revisit the decision itself.

### Section 5: Output Requirements

- Output ONLY valid JSON matching qa_semantic_compliance_output.v1 schema
- Do NOT invent finding codes outside the enum
- Every finding MUST include at least one evidence_pointer
- Keep messages concise (<200 chars) and actionable
```

---

## 5. Implementation Steps

### Step 1: Create Output Schema
**File:** `seed/schemas/qa_semantic_compliance_output.v1.json`

Copy the schema from Section 3 above.

### Step 2: Create Policy Prompt
**File:** `seed/prompts/tasks/qa_semantic_compliance_v1.0.txt`

Structure:
```
[Role context - you are a QA validator]

[Policy rules - Section 4 content above]

[Input format description]
- PGC Questions with priorities and answers
- Bound constraints with normalized text
- Generated document JSON

[Output requirements]
- Schema definition (inline or reference)
- Contract rules
- Examples of valid output

[Final instruction]
Evaluate the document against all bound constraints.
Output ONLY the JSON report. No preamble, no explanation.
```

### Step 3: Implement Semantic QA Method
**File:** `app/domain/workflow/nodes/qa.py`

```python
async def _run_semantic_qa(
    self,
    node_id: str,
    document: Dict[str, Any],
    context: DocumentWorkflowContext,
) -> Optional[Dict[str, Any]]:
    """Run Layer 2 semantic QA validation.
    
    Args:
        node_id: QA node identifier
        document: Generated document to validate
        context: Workflow context with PGC data
        
    Returns:
        Parsed semantic QA report or None if skipped
    """
    # 1. Check if we have invariants to validate
    invariants = context.context_state.get("pgc_invariants", [])
    if not invariants:
        return None
    
    # 2. Assemble inputs
    pgc_questions = context.context_state.get("pgc_questions", [])
    pgc_answers = context.context_state.get("pgc_answers", {})
    
    # 3. Load policy prompt
    policy_prompt = self.prompt_loader.load_task_prompt(
        "qa_semantic_compliance_v1.0"
    )
    
    # 4. Build message with all context
    message_content = self._build_semantic_qa_context(
        policy_prompt=policy_prompt,
        pgc_questions=pgc_questions,
        pgc_answers=pgc_answers,
        invariants=invariants,
        document=document,
        correlation_id=context.extra.get("correlation_id", ""),
    )
    
    # 5. Call LLM
    response = await self.llm_service.complete(
        messages=[{"role": "user", "content": message_content}],
        role="QA Semantic Validator",
        ...
    )
    
    # 6. Parse and validate response
    report = self._parse_semantic_qa_response(response, len(invariants))
    
    return report
```

### Step 4: Build Context Assembly Method
**File:** `app/domain/workflow/nodes/qa.py`

```python
def _build_semantic_qa_context(
    self,
    policy_prompt: str,
    pgc_questions: List[Dict],
    pgc_answers: Dict[str, Any],
    invariants: List[Dict],
    document: Dict[str, Any],
    correlation_id: str,
) -> str:
    """Assemble the 4 inputs for semantic QA."""
    
    parts = [policy_prompt]
    
    # PGC Questions with answers
    parts.append("\n\n## PGC Questions and Answers\n")
    for q in pgc_questions:
        qid = q.get("id")
        answer = pgc_answers.get(qid)
        priority = q.get("priority", "could")
        parts.append(f"- {qid} (priority={priority}): {answer}")
    
    # Bound constraints
    parts.append("\n\n## Bound Constraints (MUST evaluate each)\n")
    for inv in invariants:
        cid = inv.get("id")
        kind = inv.get("invariant_kind", "requirement")
        text = inv.get("normalized_text") or inv.get("user_answer_label")
        parts.append(f"- {cid} [{kind}]: {text}")
    
    # Document
    parts.append("\n\n## Generated Document\n```json\n")
    parts.append(json.dumps(document, indent=2))
    parts.append("\n```")
    
    # Correlation ID for output
    parts.append(f"\n\ncorrelation_id for output: {correlation_id}")
    
    return "".join(parts)
```

### Step 5: Parse and Validate Response
**File:** `app/domain/workflow/nodes/qa.py`

```python
def _parse_semantic_qa_response(
    self,
    response: str,
    expected_constraint_count: int,
) -> Dict[str, Any]:
    """Parse LLM response and validate against schema."""
    
    # Extract JSON from response
    report = self._extract_json(response)
    
    # Validate against schema
    # (use jsonschema library)
    
    # Verify contract rules
    coverage = report.get("coverage", {})
    if coverage.get("expected_count") != expected_constraint_count:
        logger.warning("Semantic QA coverage count mismatch")
    
    return report
```

### Step 6: Convert to Feedback Format
**File:** `app/domain/workflow/nodes/qa.py`

```python
def _convert_semantic_findings_to_feedback(
    self,
    report: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Convert semantic QA findings to existing feedback format."""
    
    feedback_issues = []
    
    for finding in report.get("findings", []):
        feedback_issues.append({
            "type": "semantic_qa",
            "check_id": finding.get("code"),
            "severity": finding.get("severity"),
            "message": finding.get("message"),
            "constraint_id": finding.get("constraint_id"),
            "evidence_pointers": finding.get("evidence_pointers", []),
            "remediation": finding.get("suggested_fix"),
        })
    
    return feedback_issues
```

### Step 7: Wire into QA Execution Flow
**File:** `app/domain/workflow/nodes/qa.py`

Modify `execute()` method:

```python
async def execute(...) -> NodeResult:
    # ... existing code ...
    
    # 1. Run constraint drift validation (Layer 1 mechanical)
    drift_result = self._run_drift_validation(document, context)
    if drift_result and not drift_result.passed:
        # Mechanical errors - fail fast, skip semantic
        return NodeResult(outcome="failed", ...)
    
    # 2. Run promotion validation (Layer 1 mechanical)
    code_result = self._run_code_based_validation(document, context)
    if code_result and not code_result.passed:
        return NodeResult(outcome="failed", ...)
    
    # 3. Run semantic QA (Layer 2) - only if mechanical passed
    semantic_report = await self._run_semantic_qa(node_id, document, context)
    
    if semantic_report:
        if semantic_report.get("gate") == "fail":
            # Convert findings to feedback format
            semantic_feedback = self._convert_semantic_findings_to_feedback(
                semantic_report
            )
            return NodeResult(
                outcome="failed",
                metadata={
                    "node_id": node_id,
                    "semantic_qa_report": semantic_report,
                    "errors": [f["message"] for f in semantic_feedback 
                              if f["severity"] == "error"],
                    "validation_source": "semantic_qa",
                },
            )
    
    # 4. All checks passed
    return NodeResult.success(...)
```

### Step 8: Update Feedback Extraction
**File:** `app/domain/workflow/plan_executor.py`

Modify `_extract_qa_feedback()` to handle semantic QA source:

```python
def _extract_qa_feedback(self, result: NodeResult) -> Optional[Dict[str, Any]]:
    # ... existing code ...
    
    # Extract semantic QA findings
    semantic_report = result.metadata.get("semantic_qa_report")
    if semantic_report:
        for finding in semantic_report.get("findings", []):
            if finding.get("severity") == "error":
                feedback["issues"].append({
                    "type": "semantic_qa",
                    "check_id": finding.get("code"),
                    "constraint_id": finding.get("constraint_id"),
                    "message": finding.get("message"),
                    "remediation": finding.get("suggested_fix"),
                    "evidence": finding.get("evidence_pointers", []),
                })
    
    return feedback
```

### Step 9: Write Tests
**File:** `tests/tier1/workflow/nodes/test_qa_semantic.py`

```python
class TestSemanticQA:
    """Tests for Layer 2 semantic QA validation."""
    
    def test_parse_valid_report(self):
        """Valid JSON report parses correctly."""
        
    def test_parse_invalid_schema_raises(self):
        """Invalid schema raises validation error."""
        
    def test_gate_fail_on_contradiction(self):
        """Report with contradicted status fails gate."""
        
    def test_gate_pass_all_satisfied(self):
        """Report with all satisfied passes gate."""
        
    def test_coverage_count_validation(self):
        """Coverage counts must match constraint count."""
        
    def test_findings_to_feedback_conversion(self):
        """Semantic findings convert to feedback format."""
        
    def test_skip_when_no_invariants(self):
        """Semantic QA skipped when no bound constraints."""
```

---

## 6. Acceptance Criteria

1. **Schema exists and validates**
   - `seed/schemas/qa_semantic_compliance_output.v1.json` created
   - Schema validates known-good and rejects known-bad examples

2. **Policy prompt created**
   - `seed/prompts/tasks/qa_semantic_compliance_v1.0.txt` created
   - Contains all policy sections from Section 4
   - Includes output schema requirements

3. **Semantic QA executes**
   - `_run_semantic_qa()` assembles correct context
   - LLM called with policy + 4 inputs
   - Response parsed and validated

4. **Integration with QA flow**
   - Mechanical checks run first
   - Semantic QA runs only if mechanical passes (or only warnings)
   - Semantic failures return proper NodeResult

5. **Feedback loop works**
   - Semantic findings extracted by `_extract_qa_feedback()`
   - Remediation node receives semantic issues
   - Issues rendered in remediation context

6. **Tests pass**
   - All tier-1 tests for semantic QA pass
   - Existing QA tests still pass

---

## 7. Prohibited Actions

- Do NOT modify database schema
- Do NOT change the existing feedback format structure (extend only)
- Do NOT remove mechanical checks (Layer 1 remains)
- Do NOT hardcode policy rules in Python (must be in prompt)
- Do NOT skip schema validation of LLM response

---

## 8. Files to Create/Modify

### Create
| File | Purpose |
|------|---------|
| `seed/schemas/qa_semantic_compliance_output.v1.json` | Output contract schema |
| `seed/prompts/tasks/qa_semantic_compliance_v1.0.txt` | Policy + prompt |
| `tests/tier1/workflow/nodes/test_qa_semantic.py` | Unit tests |

### Modify
| File | Changes |
|------|---------|
| `app/domain/workflow/nodes/qa.py` | Add `_run_semantic_qa()`, wire into `execute()` |
| `app/domain/workflow/plan_executor.py` | Update `_extract_qa_feedback()` for semantic source |
| `app/domain/workflow/validation/constraint_drift_validator.py` | Remove dead QA-PGC-002 code |

---

## 9. Dependencies

- Existing `llm_service.complete()` for LLM calls
- Existing `prompt_loader` for loading prompts
- `jsonschema` library for response validation (already in dependencies)

---

## 10. Estimated Effort

- Schema + prompt creation: 1-2 hours
- `_run_semantic_qa()` implementation: 2-3 hours
- Integration + wiring: 1-2 hours
- Tests: 2-3 hours
- **Total: 6-10 hours**

---

## 11. Rollback Plan

If semantic QA causes issues in production:
1. Set `SEMANTIC_QA_ENABLED=false` environment variable
2. Add early return in `_run_semantic_qa()` checking this flag
3. System falls back to mechanical-only validation

---

## 12. Success Metrics

After implementation:
1. QA-PGC-002 style violations detected without false positives
2. Coverage report confirms all constraints evaluated
3. Remediation receives actionable semantic feedback
4. No regression in existing mechanical checks