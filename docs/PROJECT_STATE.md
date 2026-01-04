# PROJECT_STATE.md
> Single source of truth for session continuity

## AI Collaboration Notes
Execution constraints for AI collaborators are defined in AI.MD and are considered binding.

## Current Status
**Phase 2 Complete** - Ready for Phase 3 (HTTP API)

## Test Summary
- **Total Tests:** 207 passing
- **Phase 0 (Validator):** 25 tests
- **Phase 1 (Step Executor):** 109 tests  
- **Phase 2 (Workflow Executor):** 73 tests

## Completed Phases

### Phase 0: Validation ✅
- Workflow schema validation
- Scope hierarchy validation
- Reference rule enforcement

### Phase 1: Step Executor ✅
- Single-step execution with LLM
- Clarification gate (ADR-024)
- QA gate (mechanical validation)
- Input resolution (ADR-011)
- Bounded remediation (max 3 attempts)

### Phase 2: Workflow Executor ✅
- Multi-step orchestration
- Iteration handling (iterate_over)
- Acceptance gates (human approval)
- State persistence (file-based)
- Scope-aware document storage

## Architecture Overview

```
WorkflowExecutor
    ├── StepExecutor
    │   ├── PromptLoader
    │   ├── InputResolver
    │   ├── LLMService (protocol)
    │   ├── ClarificationGate
    │   ├── QAGate
    │   └── RemediationLoop
    ├── WorkflowContext
    ├── IterationHandler
    ├── AcceptanceGate
    └── StatePersistence
```

## File Structure

```
app/domain/workflow/
├── __init__.py
├── types.py
├── scope.py
├── validator.py
├── models.py
├── loader.py
├── registry.py
├── step_state.py
├── prompt_loader.py
├── input_resolver.py
├── remediation.py
├── step_executor.py
├── context.py
├── iteration.py
├── workflow_state.py
├── workflow_executor.py
├── persistence.py
└── gates/
    ├── __init__.py
    ├── clarification.py
    ├── qa.py
    └── acceptance.py
```

## Run Tests

```powershell
cd "C:\Dev\The Combine"
python -m pytest tests/domain/workflow/ -v
```

## Next: Phase 3 - HTTP API

Components to build:
- FastAPI router for workflow endpoints
- WebSocket for real-time updates
- Request/response models
- Authentication middleware
- Error handling

## Documentation

- `docs/implementation-plans/phase-1-summary.md` - Step Executor details
- `docs/implementation-plans/phase-2-summary.md` - Workflow Executor details
- `docs/implementation-plans/phase-2-workflow-executor.md` - Original plan
