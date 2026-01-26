# QA Validation System - Complete Architecture Writeup

## Overview

The Combine's QA validation system attempts to enforce that LLM-generated documents respect user decisions captured during the Pre-Generation Clarification (PGC) phase. This document traces the complete data flow, identifies what works and what doesn't, and explains the fundamental architectural problem.

---

## Core Data Flow

### 1. PGC Question Generation → User Answers → Clarification Merge

**Files involved:**
- `app/domain/workflow/nodes/task.py` (PGC Generator node)
- `app/domain/workflow/clarification_merger.py` (merge logic)
- `app/domain/workflow/plan_executor.py` (orchestration)

**Sequence:**

```
User provides project brief
    ↓
PGC Generator (task node) produces question set
    ↓
User answers questions in UI (stored in DB)
    ↓
Plan Executor calls merge_clarifications() 
    ↓
Produces:
  - pgc_clarifications[] (all questions + answers + binding status)
  - pgc_invariants[] (subset where binding=true)
    ↓
Both stored in state.context_state
```

**Key code in clarification_merger.py:**

```python
def _derive_binding(question, answer, resolved) -> Tuple[bool, str, str]:
    """
    Rules (in precedence order):
    1. Not resolved -> binding=False
    2. constraint_kind == "exclusion" AND resolved -> binding=True
    3. constraint_kind == "requirement" AND resolved -> binding=True
    4. priority == "must" AND resolved -> binding=True
    5. Otherwise -> binding=False
    """
```

**What this produces:**

For each binding constraint, we get:
- `id`: e.g., "DEPLOYMENT_CONTEXT"
- `user_answer`: e.g., true or "Personal use"
- `user_answer_label`: e.g., "Personal use (family/home)"
- `invariant_kind`: "exclusion" or "requirement"
- `normalized_text`: e.g., "No integrations with existing systems are in scope."
- `canonical_tags`: e.g., ["family", "home", "personal"] (PROBLEMATIC - see below)

---

### 2. Document Generation with Constraint Context

**Files involved:**
- `app/domain/workflow/nodes/task.py` (Document Generator)
- `app/domain/workflow/plan_executor.py` (orchestration)

**What the LLM sees:**

The task node builds messages with this structure (from `_build_messages()`):

```
Message 1 (user role):
  ## Bound Constraints (FINAL — DO NOT REOPEN)
  These decisions are settled. Do not present alternatives or questions about them.

  - DEPLOYMENT_CONTEXT: Personal use (family/home) [requirement]
  - MATH_SCOPE: Addition, Subtraction, Basic multiplication [requirement]
  - EXISTING_SYSTEMS: No [exclusion - out of scope]
  - PROGRESS_FEATURES: Yes [requirement]

  ## Previous QA Feedback (MUST ADDRESS)  ← Only on remediation attempts
  The previous generation attempt failed QA. Fix these issues:
  1. [QA-PGC-002] unknowns[].question presents 'family' as uncertain...

  ## Extracted Context
  {JSON blob with pgc_clarifications, pgc_invariants, intake data}

Message 2 (user role):
  {Task prompt from seed/prompts/tasks/}
  {Output schema from seed/schemas/}
```

**Status:** ✅ This part works correctly. Constraints ARE prominently presented.

---

### 3. Post-Generation Processing (Pinning & Filtering)

**Files involved:**
- `app/domain/workflow/plan_executor.py`

**Sequence after LLM returns document:**

```
LLM produces document JSON
    ↓
_pin_invariants_to_known_constraints()  ← ADR-042 Fix #2
    - Builds canonical constraints from pgc_invariants
    - Removes LLM-generated duplicates (keyword matching)
    - Final list = pinned + non-duplicate LLM constraints
    ↓
_filter_excluded_topics()  ← ADR-042 mechanical filter
    - Removes recommendations mentioning exclusion tags
    - Removes early_decision_points overlapping bound topics
    ↓
Store in context_state["document_project_discovery"]
    ↓
Route to QA node
```

**Status:** ✅ Pinning works. ⚠️ Exclusion filtering is tag-based (same problem as QA-PGC-002).

---

### 4. QA Node Validation

**Files involved:**
- `app/domain/workflow/nodes/qa.py` (orchestration)
- `app/domain/workflow/validation/constraint_drift_validator.py` (ADR-042 checks)
- `app/domain/workflow/validation/promotion_validator.py` (WS-PGC-VALIDATION-001 checks)
- `app/domain/workflow/validation/rules.py` (text matching utilities)

**Validation order:**

```
Document arrives at QA node
    ↓
1. Constraint Drift Validation (ADR-042) - FAILS FAST
   └─ QA-PGC-001: Contradiction check (mechanical regex)
   └─ QA-PGC-002: Reopened decision check (DISABLED - was keyword-based)
   └─ QA-PGC-003: Constraint stated (WARNING only)
   └─ QA-PGC-004: Traceability in known_constraints (WARNING only)
    ↓
2. Promotion Validation (WS-PGC-VALIDATION-001)
   └─ check_promotion_validity(): should/could → constraint (WARNING)
   └─ check_internal_contradictions(): same text in constraints + assumptions (ERROR)
   └─ check_policy_conformance(): prohibited terms in unknowns (WARNING)
   └─ check_grounding(): guardrails traceable to input (WARNING)
    ↓
3. Schema Validation (if configured)
    ↓
4. LLM-based Semantic QA (if configured)
    ↓
Return NodeResult with outcome: "success" or "failed"
```

---

## What Works

### 1. Constraint Pinning (ADR-042 Fix #2)
**File:** `plan_executor.py::_pin_invariants_to_known_constraints()`

Binding constraints are mechanically inserted into `known_constraints[]` with consistent formatting:
```python
{
    "text": "Personal use (family/home)",  # or normalized_text
    "source": "user_clarification",
}
```

Duplicate detection removes LLM-generated constraints that overlap (2+ keyword matches).

**Log output:**
```
ADR-042: Pinned 4 binding invariants, removed 3 duplicates, kept 2 LLM constraints (total: 6)
```

### 2. QA-PGC-001: Contradiction Detection
**File:** `constraint_drift_validator.py::_check_contradiction()`

Detects direct contradictions via regex patterns:
- For exclusions: Checks if excluded value appears with "recommend", "use", etc.
- For selections: Checks if a non-selected choice is stated as THE selection

**Status:** Works but limited - only catches explicit contradictions, not semantic ones.

### 3. QA-PGC-004: Traceability Warnings
**File:** `constraint_drift_validator.py::_check_traceability()`

Issues WARNING (not error) if bound constraint isn't in `known_constraints[]`.

**Status:** Useful but not blocking - pinning usually handles this.

### 4. Internal Contradiction Detection (ERROR)
**File:** `rules.py::check_internal_contradictions()`

Uses Jaccard similarity > 0.5 to detect when same concept appears in both `known_constraints` AND `assumptions`.

**Status:** Works mechanically but can miss semantic contradictions.

### 5. QA Feedback Loop
**Files:** `plan_executor.py::_extract_qa_feedback()`, `task.py::_render_qa_feedback()`

On QA failure:
1. Extract structured issues from NodeResult metadata
2. Store in `context_state["qa_feedback"]`
3. On remediation, render as prominent "## Previous QA Feedback (MUST ADDRESS)"
4. Clear on success

**Status:** ✅ Works - remediation LLM now sees specific failures.

---

## What Doesn't Work

### 1. QA-PGC-002: Reopened Decision Detection (DISABLED)
**File:** `constraint_drift_validator.py::_check_reopened_decision()` (currently commented out)

**The fundamental problem:**

Keyword matching CANNOT distinguish:
- "How many family members will use the app?" → Valid follow-up question
- "Should we target classroom use instead of family use?" → Reopening the decision

Both contain the word "family" from `canonical_tags`, but only the second is a violation.

**Why tag derivation fails:**

```python
# From clarification_merger.py::_derive_canonical_tags()
# For DEPLOYMENT_CONTEXT with answer "Personal use (family/home)":
canonical_tags = ["personal", "family", "home"]  # Words from answer

# Any unknown question mentioning "family" triggers false positive
```

**Failed fix attempts:**
1. **Finality patterns:** Added patterns like "selected", "decided", "out of scope" to allow restated facts
2. **Open framing patterns:** Added patterns like "should we", "do we need" to detect reopening
3. **Answer-derived tags:** Changed from ID-derived to answer-derived tags
4. **Uncertainty patterns:** Added patterns like "what.*{topic}", "unclear", "tbd"

**All fail because:** Keyword presence ≠ semantic intent. The LLM naturally asks follow-up questions that mention decided topics without questioning the decision.

### 2. Exclusion Topic Filtering (Limited)
**File:** `plan_executor.py::_filter_excluded_topics()`

Same tag-matching problem. Filters items mentioning exclusion tags, but:
- "Investigate accessibility standards" → Should be filtered (excluded)
- "The app operates without complex accessibility requirements" → Should NOT be filtered (restating exclusion)

Both contain "accessibility" tag.

### 3. Promotion Validation Accuracy
**File:** `rules.py::check_promotion_validity()`

Uses keyword overlap to detect if constraint came from `should/could` answer rather than `must`.

**Problem:** Keyword matching is too crude:
- High false positive rate (unrelated constraints share keywords)
- High false negative rate (semantic similarity without keyword overlap)

---

## The Architectural Problem

### Layer 1 (Mechanical) Can Only Do:

| Check | What It Does | Accuracy |
|-------|--------------|----------|
| Schema validation | JSON structure | ✅ 100% |
| Pinning constraints | Insert into known_constraints | ✅ 100% |
| Duplicate removal | Keyword-based dedup | ⚠️ 80% |
| Direct contradiction | Regex patterns | ⚠️ 50% |
| Traceability | Is answer_label in text? | ⚠️ 70% |

### What Requires Semantic Understanding:

| Check | Why Mechanical Fails |
|-------|---------------------|
| Reopened decision | Can't distinguish follow-up vs. questioning |
| Exclusion compliance | Can't distinguish restatement vs. recommendation |
| Promotion detection | Keyword overlap ≠ semantic derivation |
| Intent preservation | "What user wanted" can't be regex-matched |

---

## Current State Summary

### Enabled Checks:
- ✅ QA-PGC-001: Contradiction (regex-based, limited)
- ❌ QA-PGC-002: Reopened decision (DISABLED - too many false positives)
- ⚠️ QA-PGC-003: Constraint stated (WARNING only)
- ⚠️ QA-PGC-004: Traceability (WARNING only)
- ⚠️ Promotion validity (WARNING only, keyword-based)
- ✅ Internal contradiction (ERROR, Jaccard-based)
- ⚠️ Policy conformance (WARNING, keyword-based)
- ⚠️ Grounding (WARNING, keyword-based)

### Net Effect:
Documents can pass QA while:
- Presenting bound decisions as open questions
- Recommending excluded topics (as long as exact keywords aren't matched)
- Treating `should` answers as if they were `must`

---

## Proposed Solution: Layer 2 (LLM as Semantic Referee)

### Inputs to QA LLM:
1. PGC question set (with priority + answers)
2. Bound constraints rendered (normalized_text + binding_source)
3. Generated document JSON
4. **Explicit policy text** (rules, not implicit in code)

### Policy Text Example:
```
## QA Policy for Project Discovery Documents

### MUST-priority bindings:
- MUST appear in known_constraints or equivalent statement
- MUST NOT be contradicted anywhere
- MUST NOT appear as open question in unknowns or early_decision_points

### SHOULD-priority answers:
- MAY inform the document but NOT be treated as immutable constraint
- If in known_constraints, severity = ERROR (promotion violation)
- If in assumptions with medium/low confidence, OK

### Exclusions (answer = "No"):
- Topic MUST NOT be recommended or investigated
- Restating exclusion as fact is allowed ("No accessibility requirements apply")
- Asking clarifying questions about exclusion is ERROR

### Unknowns section:
- MAY ask follow-up questions WITHIN a bound decision
- MUST NOT question the decision itself
```

### Output Format:
```json
{
  "pass": false,
  "violations": [
    {
      "code": "SHOULD_PROMOTED",
      "severity": "error",
      "location": "known_constraints[3]",
      "explanation": "CURRICULUM_ALIGNMENT was 'should' priority but appears as binding constraint",
      "suggested_fix": "Move to assumptions with medium confidence"
    }
  ],
  "coverage": [
    {"binding_id": "PLATFORM_TARGET", "status": "satisfied", "evidence": "known_constraints[0]"},
    {"binding_id": "DEPLOYMENT_CONTEXT", "status": "satisfied", "evidence": "summary paragraph 2"}
  ]
}
```

### Key Principle:
**Don't ask the LLM to decide policy — ask it to apply policy.**

The LLM receives explicit rules and evaluates compliance. It doesn't invent rules or make judgment calls.

---

## Files Reference

| File | Purpose |
|------|---------|
| `app/domain/workflow/clarification_merger.py` | Merge PGC questions + answers → clarifications + invariants |
| `app/domain/workflow/plan_executor.py` | Orchestrate workflow, pin constraints, filter exclusions, extract QA feedback |
| `app/domain/workflow/nodes/task.py` | Build LLM messages with constraint context |
| `app/domain/workflow/nodes/qa.py` | Run validation sequence, return pass/fail |
| `app/domain/workflow/validation/constraint_drift_validator.py` | ADR-042 checks (QA-PGC-001 through 004) |
| `app/domain/workflow/validation/promotion_validator.py` | WS-PGC-VALIDATION-001 checks |
| `app/domain/workflow/validation/rules.py` | Keyword extraction, Jaccard similarity, text matching |
| `app/domain/workflow/validation/validation_result.py` | Data classes for validation results |

---

## Conclusion

The current system correctly:
1. Captures user decisions in PGC
2. Derives binding status mechanically
3. Presents constraints prominently to generation LLM
4. Pins constraints into output documents
5. Feeds back QA failures to remediation

The current system CANNOT:
1. Detect when a question reopens a bound decision (semantic)
2. Distinguish restatement from recommendation (semantic)
3. Accurately detect promotion from should → constraint (semantic)

**The only path forward is Layer 2: LLM-based semantic QA with explicit policy.**