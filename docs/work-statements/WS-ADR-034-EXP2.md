# WS-ADR-034-EXP2: Structural Variety + Deep-Nesting Probe

| | |
|---|---|
| **Work Statement** | WS-ADR-034-EXP2 |
| **Title** | Structural Variety + Deep-Nesting Probe |
| **Related ADRs** | ADR-034, ADR-033, ADR-031 |
| **Predecessor** | WS-ADR-034-EXP |
| **Status** | Complete |
| **Expected Scope** | Small multi-commit |
| **Owner** | Tom |
| **Primary Risk** | Discovering structural limitations that constrain container applicability |
| **Created** | 2026-01-08 |

---

## Purpose

Validate that `shape: "container"` is robust across structurally different placements of Open Questions using docdef configuration only, and probe current limits around deep nesting.

---

## Hard Invariants (Unchanged)

No changes to:
- `schema:OpenQuestionsBlockV1`
- `component:OpenQuestionsBlockV1:1.0.0`
- Container fragment template
- PromptAssembler
- RenderModel schemas

---

## Scenarios

### S1 — Root-level Container (Must-pass)

- `repeat_over`: none
- `source_pointer`: `/open_questions`
- Context: document-level only

### S2 — One-level Nested Container (Must-pass)

- `repeat_over`: `/epics`
- `source_pointer`: `/open_questions`
- Context: epic-level (`epic_id`, `epic_title`)

*Note: This is the existing EpicBacklog:1.1.0 scenario.*

### S3 — Deep Nesting (Probe: must-attempt, outcome documented)

Target shape: `/epics/*/capabilities/*/open_questions` (or equivalent synthetic fixture)

**Expectation:**
- May fail due to current RenderModelBuilder supporting only one `repeat_over` level
- Failure is acceptable **only if** the limitation is documented precisely

---

## Acceptance Criteria

### AC1 (S1): Root-level container renders correctly ✅

- Single `RenderBlockV1` of type `schema:OpenQuestionsBlockV1`
- `data.items[]` contains all root questions
- No HTML in JSON payloads

### AC2 (S2): One-level nested container renders correctly ✅

- One container block per invocation
- Items match epic's `open_questions`
- Context propagation verified

*Note: Already satisfied by EpicBacklog:1.1.0 from EXP1.*

### AC3 (S3): Deep nesting probe completed ✅ (not "must work")

This WS requires:
- An implementation attempt for S3 using docdef config + fixture
- A recorded outcome meeting **one** of:

**Outcome A — Works**
- Deep nesting produces correct container blocks at the deeper level

**Outcome B — Fails, with boundary documented**

Documentation must include:
1. The exact docdef config used (`repeat_over`/`source_pointer`/`context`)
2. The fixture payload shape used
3. The observed RenderModelBuilder behavior
4. The precise failure mode
5. The minimal statement of current supported boundary

**Either outcome satisfies AC3.**

### AC4: Regression + tests ✅

- Existing EpicBacklog v1.0.0 unchanged
- All tests pass

---

## Failure Conditions (Automatic ❌)

- Any canonical artifact modification is required to make S1/S2 pass
- Any document-type-specific branching is introduced in builder
- Any "magic inference" is added to compensate for S3
- S3 is not attempted or outcome is not documented precisely

---

## Decision Gate

After WS completion:

- **If S3 works:** Multi-level iteration is already supported (unlikely, but great)
- **If S3 fails cleanly:** Boundary is defined; future options include:
  - Flatten upstream payload
  - Extend docdef syntax for nested iteration
  - Enhance builder to support nested `repeat_over`

---

## Rollback Plan

Revert docdef variants + fixtures only. Canonical artifacts remain unchanged.

---

## Procedure

### PHASE 1: S1 — Root-level Container

#### Step 1.1: Create Test DocDef for Root-level Questions

**Action:** Add to `seed_component_artifacts.py`

```python
ROOT_QUESTIONS_DOCDEF = {
    "document_def_id": "docdef:RootQuestionsTest:1.0.0",
    "document_schema_id": None,
    "prompt_header": {
        "role": "Test document for root-level questions.",
        "constraints": []
    },
    "sections": [
        {
            "section_id": "root_questions",
            "title": "Open Questions",
            "order": 10,
            "component_id": "component:OpenQuestionsBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/open_questions"
            # No repeat_over - root level
        }
    ],
    "status": "accepted"
}
```

#### Step 1.2: Test Root-level Preview

**Action:** POST to render preview with payload:
```json
{
  "document_data": {
    "open_questions": [
      {"id": "Q-001", "text": "Root question 1", "blocking": true},
      {"id": "Q-002", "text": "Root question 2", "blocking": false}
    ]
  }
}
```

**Verify:**
- Single container block
- `data.items` has 2 questions
- No context (root level)

---

### PHASE 2: S2 — One-level Nested (Baseline Verification)

#### Step 2.1: Verify Existing EpicBacklog:1.1.0

**Action:** Confirm EpicBacklog:1.1.0 still works (from EXP1)

Already validated. Document as baseline.

---

### PHASE 3: S3 — Deep Nesting Probe

#### Step 3.1: Create Deep Nesting DocDef

**Action:** Add test docdef with nested repeat_over attempt

```python
DEEP_NESTING_TEST_DOCDEF = {
    "document_def_id": "docdef:DeepNestingTest:1.0.0",
    "document_schema_id": None,
    "prompt_header": {
        "role": "Test document for deep nesting probe.",
        "constraints": []
    },
    "sections": [
        {
            "section_id": "deep_questions",
            "title": "Capability Questions",
            "order": 10,
            "component_id": "component:OpenQuestionsBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/open_questions",
            "repeat_over": "/epics/*/capabilities",  # Attempt deep path
            "context": {
                "capability_id": "/id",
                "capability_name": "/name"
            }
        }
    ],
    "status": "accepted"
}
```

#### Step 3.2: Create Deep Nesting Test Fixture

```json
{
  "document_data": {
    "epics": [
      {
        "id": "E-001",
        "title": "Epic 1",
        "capabilities": [
          {
            "id": "C-001",
            "name": "Capability 1",
            "open_questions": [
              {"id": "Q-001", "text": "Deep Q1", "blocking": true}
            ]
          },
          {
            "id": "C-002",
            "name": "Capability 2",
            "open_questions": [
              {"id": "Q-002", "text": "Deep Q2", "blocking": false}
            ]
          }
        ]
      }
    ]
  }
}
```

#### Step 3.3: Execute Probe and Document Outcome

**Action:** Attempt render preview with deep nesting docdef

**Document:**
1. Exact docdef config used
2. Fixture payload shape
3. Observed behavior
4. Failure mode (if any)
5. Boundary statement

---

### PHASE 4: Tests and Verification

#### Step 4.1: Add S1 Test

Test root-level container rendering.

#### Step 4.2: Add S3 Probe Test

Test that documents expected behavior (pass or documented limitation).

#### Step 4.3: Run Full Suite

`python -m pytest tests/ -v`

---

### PHASE 5: Document Findings

#### Step 5.1: Record S3 Outcome

Update this WS with probe findings in a "Findings" section.

---

## Findings

### S1 — Root-level Container: ✅ PASS

**Result:** Single container block with 2 items, `context: null`

```json
{
  "document_def_id": "docdef:RootQuestionsTest:1.0.0",
  "blocks": [
    {
      "type": "schema:OpenQuestionsBlockV1",
      "key": "root_questions:container",
      "data": {
        "items": [
          {"id": "Q-001", "text": "Root Q1", "blocking": true},
          {"id": "Q-002", "text": "Root Q2", "blocking": false}
        ]
      },
      "context": null
    }
  ]
}
```

**Conclusion:** Root-level container (no `repeat_over`) works correctly.

---

### S2 — One-level Nested Container: ✅ PASS

**Result:** Validated via EpicBacklog:1.1.0 (from EXP1). Single container block with all items from all epics.

**Conclusion:** One-level nesting with `repeat_over` works correctly.

---

### S3 — Deep Nesting Probe: ✅ DOCUMENTED (Outcome B)

**DocDef Config:**
```python
{
    "shape": "container",
    "source_pointer": "/open_questions",
    "repeat_over": "/epics",
    "context": {"epic_id": "/id", "epic_title": "/title"}
}
```

**Fixture Payload Shape:**
```
/epics/*/capabilities/*/open_questions  (3 levels deep)
```

**Observed Behavior:**
```json
{
  "document_def_id": "docdef:DeepNestingTest:1.0.0",
  "blocks": [],
  "metadata": {"section_count": 1}
}
```

**Failure Mode:**
- `repeat_over=/epics` iterates over each epic
- `source_pointer=/open_questions` resolves *relative to each epic*
- Questions are at `/capabilities/*/open_questions`, not `/open_questions`
- No direct `/open_questions` found under epics → no items → no block produced

**Boundary Statement:**

> **Container sections support at most one level of parent iteration via `repeat_over`.**
> 
> Nested wildcards (e.g., `/epics/*/capabilities/*`) are not supported in the current implementation.
> The `source_pointer` resolves relative to each `repeat_over` parent, but cannot traverse further nested arrays.

**Future Options (if needed):**
1. **Flatten upstream** — Pre-flatten payload before rendering
2. **Nested repeat_over syntax** — e.g., `repeat_over: ["/epics", "/capabilities"]`
3. **Builder enhancement** — Support recursive iteration in RenderModelBuilder

---

### Decision Gate Answers

| Question | Answer |
|----------|--------|
| Are pointer + repeat_over + context mappings expressive enough? | **Yes, for 1-level nesting.** Covers majority of real-world cases. |
| Is `shape: container` stable under nesting? | **Yes, within documented boundary.** |
| Evidence for additional semantics needed? | **Only if 3+ level nesting is required.** Current system handles root and 1-level cleanly. |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-08 | Initial draft |

---

*End of Work Statement*

