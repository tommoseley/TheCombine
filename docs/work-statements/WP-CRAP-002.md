# WP-CRAP-002: Testability Refactoring -- Workflow Engine Top 3

## Status: Draft

## Intent

Reduce CRAP scores for the three worst functions in the codebase by
decomposing each into focused sub-methods and extracting pure logic into
standalone testable functions. These three functions have been the
persistent top offenders across all CRAP audits (Feb 27, Mar 1, Mar 3).

## Baseline (2026-03-03 CRAP Audit)

| # | Function | CRAP | CC | Coverage | File |
|---|----------|-----:|---:|---------:|------|
| 1 | PlanExecutor._handle_result | 967.4 | 41 | 18.0% | plan_executor.py:860 |
| 2 | PlanExecutor._spawn_child_documents | 710.1 | 35 | 18.0% | plan_executor.py:1730 |
| 3 | QANodeExecutor.execute | 600.1 | 36 | 24.2% | nodes/qa.py:85 |

Combined CRAP debt: 2,277.6 (18.9% of total 12,053 debt from just 3 functions).

## Strategy

**Extract, don't rewrite.** Each WS decomposes one function into smaller
pieces using the patterns from WP-CRAP-001:

- **Pattern A (Pure Logic):** Extract pure functions into `result_handling.py`
  or a new `child_document_helpers.py`. Tier-1 tests with no mocks.
- **Pattern B (Sub-methods):** Split orchestration into focused async methods
  on the same class. Each method handles one concern. Test via constructor DI
  with mock dependencies.

No behavioral changes. Existing tests must continue to pass unchanged.

## Work Statements

| WS | Target Function | Current CC | Target CC (parent) | Extractions |
|----|-----------------|:----------:|:------------------:|:-----------:|
| WS-CRAP-008 | PlanExecutor._handle_result | 41 | <= 10 | 5 sub-methods |
| WS-CRAP-009 | PlanExecutor._spawn_child_documents | 35 | <= 8 | 3 pure + 2 sub-methods |
| WS-CRAP-010 | QANodeExecutor.execute | 36 | <= 8 | 5 sub-methods |

### Dependencies

All three WSs are independent (non-overlapping functions, non-overlapping
test files). They MAY be executed in parallel with worktree isolation.

WS-CRAP-008 and WS-CRAP-009 both modify `plan_executor.py` but touch
different methods and can be serialized within a single worktree if
parallel execution is not used.

## Acceptance Criteria

1. All three parent functions have CC <= 10 after refactoring
2. All extracted sub-methods/functions have CC <= 10
3. All target functions have CRAP < 30 after refactoring
4. All existing Tier-1 tests pass unchanged (no test modifications)
5. New Tier-1 tests cover all extracted functions (>= 80% branch coverage)
6. Tier 0 green (pytest + lint + typecheck + frontend)

## Scope Out

- Architectural redesign of the workflow engine
- Changes to function signatures in the public API
- Changes to NodeResult, DocumentWorkflowState, or WorkflowPlan
- Changes to edge routing, node execution, or state persistence logic
- Coverage improvements via integration/e2e tests (Tier-1 only)
- Refactoring any function not listed in the Work Statements

---

_End of WP-CRAP-002_
