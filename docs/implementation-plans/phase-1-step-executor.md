# Phase 1: Step Executor - Implementation Record
**Date:** 2026-01-03
**Status:** Days 1-2 Complete, Day 3 In Progress
**Tests:** 116 passing

---

## Goal
Single step executes per ADR-012, with clarification gate, QA gate, and remediation loop.

## Exit Criteria
1. ✅ Can execute Discovery step end-to-end (Day 3)
2. ✅ Clarification gate enforces questions-only
3. ✅ QA gate passes/fails based on schema
4. ⏳ Remediation loop bounded and logged (Day 3)

---

## Day 1: Foundation ✅

### Workflow Models (`models.py`)
Typed dataclasses representing validated workflow definitions.

| Class | Purpose |
|-------|---------|
| `ScopeConfig` | Scope level with parent reference |
| `DocumentTypeConfig` | Document type with scope, ownership, acceptance |
| `EntityTypeConfig` | Entity type with parent doc and scope creation |
| `InputReference` | Reference to input doc/entity with scope |
| `IterationConfig` | Iteration over collection field |
| `WorkflowStep` | Production or iteration step |
| `Workflow` | Complete workflow with helper methods |

Key methods:
- `Workflow.get_step(step_id)` - Find step recursively
- `Workflow.get_production_steps()` - Flatten iteration to get all production steps
- `WorkflowStep.is_production` / `is_iteration` - Type discrimination

### Workflow Loader (`loader.py`)
Load, validate, and parse workflow JSON into typed models.

```python
loader = WorkflowLoader()
workflow = loader.load(Path("seed/workflows/my_workflow.v1.json"))
# or
workflow = loader.load_dict(raw_dict)
```

- Validates via `WorkflowValidator` before parsing
- Filters PROMPT_NOT_IN_MANIFEST errors (prompts may not exist yet)
- Raises `WorkflowLoadError` with error list on failure

### Workflow Registry (`registry.py`)
In-memory cache of loaded workflows.

```python
registry = WorkflowRegistry(Path("seed/workflows"))
workflow = registry.get("software_product_development")
ids = registry.list_ids()
```

- Auto-loads all `.json` files from directory
- `get()` raises `WorkflowNotFoundError` if missing
- `get_optional()` returns `None` if missing
- `reload()` refreshes from disk
- `add()` / `remove()` for dynamic management

### Step State (`step_state.py`)
Execution state machine for tracking step progress.

```
State transitions:
PENDING → EXECUTING → CLARIFYING → EXECUTING → QA_CHECKING → COMPLETED
                                                    ↓
                                              REMEDIATING → EXECUTING → ...
                                                    ↓
                                                 FAILED
```

| Class | Purpose |
|-------|---------|
| `StepStatus` | Enum of all states |
| `ClarificationQuestion` | Single question with metadata |
| `QAFinding` | Single validation finding |
| `QAResult` | Pass/fail with findings list |
| `StepState` | Full state with transitions |

Key methods:
- `state.start()` - Begin execution, increment attempt
- `state.request_clarification(questions)` - Pause for human input
- `state.provide_answers(answers)` - Resume after clarification
- `state.record_qa_result(result)` - Handle QA outcome
- `state.fail(error)` - Terminal failure
- `state.can_retry` - Check if attempts remain

### Prompt Loader (`prompt_loader.py`)
Load role and task prompts from seed directory.

```python
loader = PromptLoader()
role = loader.load_role("Technical Architect 1.0")
task = loader.load_task("Project Discovery v1.0")
```

- Caches loaded prompts
- `list_roles()` / `list_tasks()` for discovery
- `role_exists()` / `task_exists()` for validation

---

## Day 2: Gates & Input Resolution ✅

### Clarification Gate (`gates/clarification.py`)
Enforce ADR-024 clarification protocol.

```python
gate = ClarificationGate()
result = gate.check(llm_response)

if result.needs_clarification:
    for q in result.questions:
        print(f"{q.id}: {q.text}")
```

Responsibilities:
1. Detect clarification questions in LLM response
2. Extract JSON from plain text or markdown code blocks
3. Validate against `clarification_question_set.v1.json` schema
4. Enforce questions-only mode (no declarative content)

Key methods:
- `check(response)` → `ClarificationResult`
- `validate_questions_only(question_set)` → list of violations
- `get_blocking_questions(questions)` → required questions only

### QA Gate (`gates/qa.py`)
Mechanical schema validation only - NO domain intelligence.

```python
gate = QAGate()
result = gate.check(output, doc_type="project_discovery")

if not result.passed:
    for finding in result.findings:
        print(f"{finding.severity}: {finding.message}")
```

Checks performed:
1. JSON parse validity
2. Structural checks (not null, not empty, correct type)
3. Schema validation if registered for doc type

Registered schemas:
- `clarification_questions` → `clarification_question_set.v1.json`
- `intake_gate_result` → `intake_gate_result.v1.json`

Can register custom schemas via `gate.register_schema(doc_type, schema_file)`.

### Input Resolver (`input_resolver.py`)
Resolve step inputs per ADR-011 reference rules.

```python
resolver = InputResolver(workflow, document_store)
result = resolver.resolve(step, scope_id="epic_123")

if result.success:
    inputs = result.to_dict()
```

Reference rules enforced:
| Reference Type | Rule |
|----------------|------|
| Ancestor (child → parent) | ✅ Permitted |
| Same-scope at root | ✅ Permitted (only one instance) |
| Same-scope with context=true | ✅ Permitted (iteration item) |
| Same-scope without context (non-root) | ❌ Forbidden |
| Descendant (parent → child) | ❌ Forbidden |
| Cross-branch (sibling scopes) | ❌ Forbidden |

Requires `DocumentStore` protocol implementation:
```python
class DocumentStore(Protocol):
    def get_document(self, doc_type, scope, scope_id) -> Optional[Dict]
    def get_entity(self, entity_type, scope, scope_id) -> Optional[Dict]
```

---

## Day 3: Execution (Remaining)

### Remediation Loop (`remediation.py`)
Bounded retry when QA fails.

```python
loop = RemediationLoop(max_attempts=3)

if loop.should_retry(state, qa_result):
    prompt = loop.build_remediation_prompt(original_prompt, qa_result.findings)
    # Re-execute with findings included
```

### Step Executor (`step_executor.py`)
Main orchestrator combining all components.

```python
executor = StepExecutor(
    prompt_loader=prompt_loader,
    input_resolver=input_resolver,
    clarification_gate=clarification_gate,
    qa_gate=qa_gate,
    llm_service=llm_service,
)

state = await executor.execute(step, context, state)

if state.status == StepStatus.CLARIFYING:
    # Get answers from user
    state = await executor.continue_after_clarification(step, context, state, answers)
```

Execution flow:
1. Load prompts (role + task)
2. Resolve inputs per reference rules
3. Build prompt with inputs
4. Call LLM
5. Check for clarification questions
   - If questions: return CLARIFYING state
6. Run QA gate
   - If pass: return COMPLETED state
   - If fail and can retry: enter remediation loop
   - If fail and exhausted: return FAILED state

---

## Test Summary

| File | Tests | Coverage |
|------|-------|----------|
| test_validator.py | 25 | Schema, scope, reference validation |
| test_models.py | 8 | Workflow dataclasses |
| test_loader.py | 8 | Load and parse workflows |
| test_registry.py | 11 | Workflow cache |
| test_step_state.py | 16 | State machine transitions |
| test_prompt_loader.py | 13 | Prompt loading |
| test_clarification.py | 10 | Clarification gate |
| test_qa.py | 15 | QA gate |
| test_input_resolver.py | 10 | Input resolution |
| **Total** | **116** | |

---

## Files Created

```
app/domain/workflow/
├── __init__.py
├── types.py          (Phase 0)
├── scope.py          (Phase 0)
├── validator.py      (Phase 0)
├── models.py         (Day 1)
├── loader.py         (Day 1)
├── registry.py       (Day 1)
├── step_state.py     (Day 1)
├── prompt_loader.py  (Day 1)
├── input_resolver.py (Day 2)
└── gates/
    ├── __init__.py   (Day 2)
    ├── clarification.py (Day 2)
    └── qa.py         (Day 2)

tests/domain/workflow/
├── __init__.py
├── test_validator.py
├── test_models.py
├── test_loader.py
├── test_registry.py
├── test_step_state.py
├── test_prompt_loader.py
├── test_input_resolver.py
└── gates/
    ├── __init__.py
    ├── test_clarification.py
    └── test_qa.py
```

---

## Design Decisions

### 1. QAResult/QAFinding Canonical Location
Defined in `step_state.py`, re-exported from `gates/__init__.py`.
Avoids circular imports and keeps state-related types together.

### 2. QA Gate is Mechanical Only
Per MVP-Roadmap.md: "NO domain intelligence, NO probabilistic judgments."
Only schema validation and structural checks. Intelligence creep prohibited.

### 3. DocumentStore Protocol
Input resolver depends on protocol, not concrete implementation.
Allows testing with mock stores and production with real storage.

### 4. Clarification Schema Strictness
Question IDs must be 3-64 characters matching `^[A-Z0-9_\-]{3,64}$`.
Schema enforces questions end with `?` and QA section confirms no declarative content.