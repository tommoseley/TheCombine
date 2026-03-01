# WP-CRAP-001: Testability Refactoring

## Status: Draft

## Objective

Systematically reduce CRAP (Change Risk Anti-Patterns) scores across The Combine codebase
by extracting pure logic from complex functions, adding Tier-1 test coverage, and reducing
cyclomatic complexity below the critical threshold (CRAP < 30).

## Motivation

A CRAP analysis on 2026-02-26 identified 262 critical functions (CRAP > 30) out of 2,175
total functions (12.0%). The worst function has a CRAP score of 2,532.9. Six subsystems
have 5+ critical functions with worst-case CRAP > 100, representing the highest-risk
areas of the codebase.

See: docs/audits/2026-02-26-crap-scores.md

## Scope

This Work Package covers Batch 1 (worst 5-10 functions) for each of the six highest-risk
subsystems. The Workflow Engine is split into two WSs of 5 functions each because its
top functions require class-level decomposition, not simple extraction. Subsequent batches
will be scoped as additional Work Packages once Batch 1 results are assessed.

## Work Statements

| WS ID | Subsystem | Critical Count | Worst CRAP | Target Functions |
|-------|-----------|---------------|------------|------------------|
| WS-CRAP-001 | Workflow Engine Batch 1 (PlanExecutor + QANodeExecutor core) | 79 total | 2190.4 | Top 5 |
| WS-CRAP-002 | API v1 Routers | 21 total | 2532.9 | Top 10 |
| WS-CRAP-003 | API Services | 35 total | 1020.7 | Top 10 |
| WS-CRAP-004 | Document Handlers | 31 total | 506.0 | Top 10 |
| WS-CRAP-005 | Domain Services | 23 total | 229.8 | Top 10 |
| WS-CRAP-006 | Web Routes | 19 total | 333.0 | Top 10 |
| WS-CRAP-007 | Workflow Engine Batch 2 (supporting classes) | 79 total | 312.5 | Next 5 |

## Dependency Chain

WS-CRAP-001 through WS-CRAP-006 are independent and may be executed in parallel (each
targets non-overlapping source directories, except WS-CRAP-007 which shares workflow paths).

**WS-CRAP-007 depends on WS-CRAP-001.** Both touch `app/domain/workflow/` — WS-CRAP-001
restructures PlanExecutor and QANodeExecutor at the class level, and WS-CRAP-007's
extractions in those same classes should happen after that restructuring is stable.

## Success Metrics

After all 7 WSs are complete:
- 55 functions brought below CRAP < 30
- Estimated CRAP debt reduction: ~13,500 points (from ~31,000 total)
- All new tests are Tier-1 (in-memory, no DB, no I/O)
- Tier-0 green after each WS

## Subsystems Not Yet Covered

The following subsystems have critical functions but are deferred to future batches:

| Subsystem | Critical Count | Worst CRAP | Reason Deferred |
|-----------|---------------|------------|-----------------|
| Other (mixed) | 25 | 309.6 | Functions span many modules; needs grouping |
| LLM Layer | 9 | 238.7 | Fewer than 10 critical; can fit in one batch |
| Execution | 5 | 160.0 | Small count; combine with future batch |
| Auth | 6 | 119.3 | Worst < 120; lower priority |
| Persistence | 5 | 95.7 | Worst < 100; lower priority |
| Core/Observability | 4 | 342.0 | Only 4 functions; combine with future batch |

## Refactoring Principles

1. **Extract, don't rewrite.** Pull pure logic out of complex methods into standalone
   functions. The original method becomes a thin orchestrator.
2. **Test the extracted functions.** New tests target the extracted pure functions,
   not the orchestration shells.
3. **No behavioral changes.** Existing tests must continue to pass unchanged.
4. **Tier-1 only.** All new tests must be in-memory, no DB, no I/O.
5. **Measure after.** Re-run CRAP analysis after each WS to verify improvement.
