# WS-PGC-001: Pre-Generation Clarification Gate Implementation

**Status:** Draft  
**Created:** 2026-01-22  
**ADR Reference:** ADR-012 (PGC Amendment 2026-01-22)  
**Scope:** Multi-commit  

---

## 1. Objective

Implement the Pre-Generation Clarification (PGC) gate as defined in ADR-012 Amendment. This gate ensures no document may be generated unless its clarification contract is satisfied.

**System Law:** No document may be generated unless its clarification contract is satisfied.

---

## 2. Success Criteria

1. Workflow engine recognizes and executes PGC nodes
2. Questions task prompts execute and produce `clarification_question_set.v2.json` compliant output
3. User answers questions via form UI (not chat)
4. Answers are stored in workflow context state
5. Generation tasks receive answers as hard constraints
6. Generation is blocked until required questions are answered
7. Full audit trail of questions generated, answers provided, and constraints applied

---

## 3. Scope

### In Scope

- PGC node type in workflow plans
- Questions task execution (LLM call with schema injection)
- Form-based UI for question answering
- Answer storage in context state
- Answer injection into generation task context
- Blocking logic for required/unanswered questions
- Integration with existing workflow engine

### Out of Scope

- Updating all document type Questions prompts (per SOP, done when each document workflow is implemented)
- Discovery workflow implementation (separate work)
- Technical Architecture workflow implementation (separate work)

---

## 4. Prerequisites

- [x] ADR-012 PGC Amendment accepted
- [x] `clarification_question_set.v2.json` schema exists
- [x] `Project Discovery Questions v1.0.txt` canonical prompt exists
- [ ] Workflow engine supports task node execution

---

## 4a. Design Notes

### Schema Requirements (Already Satisfied)

The v2 schema already requires:
- `why_it_matters` on every question (for UI help text)
- `priority` (must/should/could) for visual hierarchy
- Structured `choices` for enum types

### Default Values: UI Assist Only

The schema allows `default` values on questions. Implementation rules:
- Defaults pre-fill form fields as suggestions
- Defaults do NOT auto-advance or silently answer
- User must explicitly confirm any pre-filled value
- Include "Unknown" as an option where appropriate

### Prohibited Question Topics

Questions prompts must NOT ask about:
- Authority, approval, sign-off
- Funding, budget
- Motive, justification (unless required for document correctness)
- Stakeholder politics
- Timeline pressure

This prohibition is enforced in the Questions task prompt template (see `Project Discovery Questions v1.0.txt`).

---

## 5. Implementation Phases

### Phase 1: Workflow Plan Schema Extension

**Objective:** Define how PGC nodes appear in workflow plans.

**Tasks:**

1.1. Extend workflow plan schema to support `pgc` node type with fields:
- `node_id`: Unique identifier
- `type`: "pgc"
- `description`: Human-readable purpose
- `task_ref`: Reference to Questions task prompt
- `target_document`: Document type this unlocks
- `schema_ref`: Reference to output schema

1.2. Define edge semantics:
- `questions_generated` - route to user input
- `questions_answered` - route to generation
- `questions_skipped` - route to generation (if no required questions)

1.3. Update `seed/schemas/workflow-plan.v1.json` with PGC node definition

**Acceptance Criteria:**
- Workflow plan with PGC node passes schema validation
- Node type `pgc` is recognized by workflow engine loader

**Prohibited:**
- Do not modify existing node types
- Do not add PGC logic to task nodes
### Phase 2: PGC Node Executor

**Note:** This phase uses ADR-041 Prompt Template Include System. The PGC node assembles prompts from generic template + context file + schema.

**Objective:** Implement executor that runs Questions task and produces structured output.

**Tasks:**

2.1. Create `app/domain/workflow/nodes/pgc_gate.py` with PGCGateNode class that:
- Loads questions task prompt via PromptLoader
- Injects schema as context to LLM call
- Executes LLM call with correlation_id from workflow execution
- Validates output against v2 schema
- Returns questions for user answering

2.2. Implement schema injection:
- Load `clarification_question_set.v2.json` at runtime
- Inject as structured context to LLM call
- Include correlation_id from workflow execution

2.3. Implement output validation:
- Parse LLM JSON output
- Validate against v2 schema
- Validate QA self-check block (all counts must be 0)
- Fail node if validation fails

2.4. Register node type with workflow engine

**Acceptance Criteria:**
- PGC node executes Questions task prompt
- Output validated against v2 schema
- Invalid output causes node failure with clear error
- Questions returned in NodeResult for UI rendering

**Prohibited:**
- Do not allow unvalidated output to proceed
- Do not skip QA self-check validation

---

### Phase 3: Answer Storage Model

**Objective:** Store user answers with full audit trail.

**Tasks:**

3.1. Create PGCAnswers dataclass with fields:
- workflow_execution_id: UUID
- node_id: str
- document_type: str
- questions_generated_at: datetime
- questions: List[dict] (full question set from LLM)
- answers: Dict[str, Any] (question_id to answer_value)
- answered_at: Optional[datetime]
- answered_by: Optional[str]
- all_required_answered: bool

3.2. Add to workflow execution metadata or dedicated table

3.3. Implement answer persistence:
- Store when user submits answers
- Immutable once generation starts
- Track which questions were required vs optional
- Track which optional questions were skipped

**Acceptance Criteria:**
- Answers persisted with timestamps
- Answers immutable after generation starts
- Full audit trail queryable

**Prohibited:**
- Do not allow answer modification after generation
- Do not lose answer provenance

---

### Phase 4: Form-Based UI

**Objective:** Render questions as a form, not chat.

**Tasks:**

4.1. Create question form template `app/web/templates/workflow/partials/_pgc_form.html`:
- Render each question based on `answer_type`
- Support: `free_text`, `single_choice`, `multi_choice`, `yes_no`, `number`, `date`
- Display `why_it_matters` as help text (required field in schema)
- Mark required questions visually
- Show priority indicators (must/should/could)

4.2. Implement form rendering by answer_type:
- single_choice: select dropdown with choices
- multi_choice: checkbox fieldset with choices
- yes_no: radio buttons (Yes/No)
- free_text: textarea with maxlength
- number: number input
- date: date input

4.3. Handle default values (UI assist only):
- Pre-fill form fields with `default` values when present
- Defaults are suggestions, NOT auto-answers
- User must explicitly confirm (no silent acceptance)
- Include "Unknown" option where appropriate

4.4. Handle "no required questions" case:
- If PGC returns zero required questions (only optional):
  - Show: "No required clarifications. Optional confirmations below."
  - Allow proceeding without answering optional questions
  - Still display optional questions for user consideration

4.5. Implement form submission handler:
- Validate all required questions answered
- Store answers via Phase 3 model
- Trigger workflow continuation

4.6. Add authority copy to form header:
"Before this document is generated, the following decisions must be confirmed. These choices will shape all downstream work.

If you don't know yet, choose 'Unknown' where offeredÃ¢â‚¬â€Discovery will resolve it."

**Acceptance Criteria:**
- All answer_types render correctly
- Required questions enforced on submission
- Optional-only case allows proceeding
- Defaults pre-fill but require confirmation
- No chat interface, form only
- Clear visual hierarchy (must > should > could)

**Prohibited:**
- Do not use chat/conversation UI
- Do not allow submission with unanswered required questions
- Do not auto-advance based on defaults
- Do not add AI persona or conversational elements

---

### Phase 5: Generation Constraint Injection

**Objective:** Pass answered questions as hard constraints to generation task.

**Tasks:**

5.1. Modify generation task context assembly:
- Load PGC answers from context state
- Format as explicit constraints section
- Inject into task prompt context

5.2. Define constraint injection format:
```
## Pre-Generation Clarification Answers (Binding Constraints)

The following decisions were made before generation and are BINDING.
You must not infer alternatives or question these answers.

- DEPLOYMENT_SCALE: organization_wide
- COMPLIANCE_REQUIREMENTS: gdpr, hipaa
- HOSTING_PREFERENCE: cloud_managed

These answers constrain your output. Do not deviate.
```

5.3. Add constraint reference to generation task prompts:
- Update prompt template to expect PGC constraints section
- Document in prompt that constraints are non-negotiable

**Acceptance Criteria:**
- Generation task receives all PGC answers
- Answers formatted as binding constraints
- LLM cannot infer around stated constraints

**Prohibited:**
- Do not make constraints optional
- Do not allow generation without constraint injection when PGC was run

---

### Phase 6: Workflow Integration

**Objective:** Wire PGC into pm_discovery workflow as reference implementation.

**Tasks:**

6.1. Update `seed/workflows/pm_discovery.v1.json`:
- Add PGC node as entry point
- Add edge from PGC to generation (on questions_answered)
- Update entry_node_ids to start with PGC

6.2. Test full flow:
- Start PM Discovery workflow
- PGC node executes, generates questions
- User answers via form
- Generation receives constraints
- Document produced respects constraints

**Acceptance Criteria:**
- PM Discovery workflow includes PGC gate
- Full flow executes without error
- Generated document reflects PGC constraints

**Prohibited:**
- Do not bypass PGC in workflow
- Do not allow generation without answered questions

---

## 6. Test Requirements

### Tier-1 (In-Memory)

- PGC node executor logic
- Answer validation
- Constraint formatting
- Required question enforcement

### Tier-2 (Spy Repositories)

- Workflow engine PGC node routing
- Answer persistence calls
- Context state updates

### Integration

- Full PM Discovery workflow with PGC
- LLM question generation (mocked)
- Form submission and answer storage

---

## 7. Files to Create/Modify

### Create

- `app/domain/workflow/nodes/pgc_gate.py` - PGC node executor
- `app/web/templates/workflow/partials/_pgc_form.html` - Form UI
- `tests/tier1/workflow/test_pgc_gate.py` - Unit tests
- `tests/tier2/workflow/test_pgc_integration.py` - Integration tests

### Modify

- `seed/schemas/workflow-plan.v1.json` - Add PGC node type
- `seed/workflows/pm_discovery.v1.json` - Add PGC node
- `app/domain/workflow/engine.py` - Register PGC node type
- `app/domain/workflow/context.py` - Add PGC answers to context state
- `app/web/routes/` - Add PGC form routes

---

## 8. Risks

| Risk | Mitigation |
|------|------------|
| LLM generates invalid question structure | Schema validation rejects; node fails explicitly |
| User abandons mid-form | Workflow state preserved; can resume |
| Constraint injection breaks generation | Clear formatting; test with real prompts |
| Form UI doesn't cover all answer_types | Implement all types in Phase 4; test each |

---

## 9. Definition of Done

- [ ] PGC node type recognized by workflow engine
- [ ] Questions task executes and produces valid output
- [ ] Form UI renders all answer types
- [ ] Required questions enforced
- [ ] Answers stored with audit trail
- [ ] Generation receives constraints
- [ ] PM Discovery workflow includes PGC gate
- [ ] All tests pass
- [ ] ADR-012 compliance verified

---

## 10. Estimated Effort

| Phase | Estimate |
|-------|----------|
| Phase 1: Schema Extension | 2 hours |
| Phase 2: Node Executor | 4 hours |
| Phase 3: Answer Storage | 2 hours |
| Phase 4: Form UI | 4 hours |
| Phase 5: Constraint Injection | 2 hours |
| Phase 6: Workflow Integration | 2 hours |
| Testing | 4 hours |
| **Total** | **20 hours** |

---

## 11. Dependencies

- Workflow engine must support custom node types (verify before Phase 2)
- LLM adapter must support schema-guided generation (verify before Phase 2)

---

## 12. References

- ADR-012 PGC Amendment (2026-01-22)
- ADR-041 Prompt Template Include System
- `seed/schemas/clarification_question_set.v2.json`
- `seed/prompts/tasks/Clarification Questions Generator v1.0.txt` (generic template)
- `seed/prompts/pgc-contexts/project_discovery.v1.txt` (context block)
- POL-WS-001 Work Statement Standard
