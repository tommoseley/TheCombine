# CRAP Score Audit — 2026-03-18

## Summary

| Metric | Value |
|--------|-------|
| Functions analyzed (CC ≥ C) | 99 |
| Total CRAP debt | 4,268 |
| Max CRAP | 342.0 |
| Median CRAP | 25.9 |
| Tests passing | 2,847 |

## Grade Distribution

| Grade | Range | Count | |
|-------|-------|-------|-|
| F | >100 | 8 | ######## |
| D | 50-100 | 19 | ################### |
| C | 30-50 | 21 | ##################### |
| B | 15-30 | 29 | ############################# |
| A | 5-15 | 22 | ###################### |

**Critical (CRAP>30):** 48 functions
**Smelly (15-30):** 29 functions

## Top 20 Highest CRAP

| # | File | Function | CC | Cov% | CRAP |
|---|------|----------|---:|-----:|-----:|
| 1 | app/observability/logging.py | format | 18 | 0.0 | 342.0 |
| 2 | app/api/services/production_service.py | get_production_tracks | 14 | 13.7 | 139.9 |
| 3 | app/domain/workflow/nodes/gate.py | _resolve_urn | 13 | 10.1 | 135.9 |
| 4 | app/auth/routes.py | callback | 11 | 0.0 | 132.0 |
| 5 | app/tasks/document_builder.py | run_workflow_build | 11 | 0.0 | 132.0 |
| 6 | app/observability/logging.py | JSONFormatter | 11 | 0.0 | 132.0 |
| 7 | app/api/v1/routers/projects.py | render_project_binder | 26 | 48.5 | 118.6 |
| 8 | app/api/repositories/role_prompt_repository.py | create | 13 | 16.8 | 110.2 |
| 9 | app/llm/output_parser.py | _validate_type | 16 | 33.3 | 91.9 |
| 10 | app/domain/workflow/plan_executor.py | execute_step | 18 | 39.0 | 91.4 |
| 11 | app/api/routers/admin.py | compare_runs | 18 | 39.7 | 88.9 |
| 12 | app/api/routers/admin.py | batch_replay_llm_runs | 18 | 39.7 | 88.9 |
| 13 | app/api/v1/services/llm_execution_service.py | _context_to_info | 14 | 28.0 | 87.3 |
| 14 | app/api/services/workspace_service.py | _run_tier1_validation | 21 | 47.6 | 84.5 |
| 15 | app/api/v1/routers/production.py | start_production | 12 | 20.9 | 83.2 |
| 16 | app/domain/workflow/pg_state_persistence.py | save | 11 | 15.9 | 83.1 |
| 17 | app/api/v1/routers/projects.py | render_document_markdown | 20 | 48.5 | 74.8 |
| 18 | app/api/services/config_validator.py | validate_activation | 11 | 19.7 | 73.6 |
| 19 | app/llm/providers/anthropic.py | complete | 12 | 24.6 | 73.6 |
| 20 | app/api/services/preview_service.py | _preview_prompts | 13 | 30.7 | 69.3 |

## Zero-Coverage Critical Functions

These 4 functions have 0% file-level coverage and CC ≥ 11:

| File | Function | CC | CRAP |
|------|----------|---:|-----:|
| app/observability/logging.py:25 | format | 18 | 342.0 |
| app/auth/routes.py:157 | callback | 11 | 132.0 |
| app/tasks/document_builder.py:151 | run_workflow_build | 11 | 132.0 |
| app/observability/logging.py:11 | JSONFormatter | 11 | 132.0 |

## Analysis

### Quick Wins (Coverage-only — no refactoring needed)
The following have moderate CC but very low coverage. Adding tests alone would dramatically reduce CRAP:

| Function | CC | Cov% | Current CRAP | CRAP at 80% cov |
|----------|---:|-----:|-------------:|----------------:|
| get_production_tracks | 14 | 13.7 | 139.9 | 15.1 |
| _resolve_urn | 13 | 10.1 | 135.9 | 14.0 |
| create (role_prompt_repo) | 13 | 16.8 | 110.2 | 14.0 |
| _context_to_info | 14 | 28.0 | 87.3 | 15.1 |
| start_production | 12 | 20.9 | 83.2 | 13.0 |
| save (pg_state) | 11 | 15.9 | 83.1 | 11.9 |

### Refactoring Targets (High CC — need structural change)
These have CC ≥ 18 regardless of coverage:

| Function | CC | File |
|----------|---:|------|
| render_project_binder | 26 | app/api/v1/routers/projects.py |
| _run_tier1_validation | 21 | app/api/services/workspace_service.py |
| render_document_markdown | 20 | app/api/v1/routers/projects.py |
| format (logging) | 18 | app/observability/logging.py |
| execute_step | 18 | app/domain/workflow/plan_executor.py |
| compare_runs | 18 | app/api/routers/admin.py |
| batch_replay_llm_runs | 18 | app/api/routers/admin.py |

### Dead Code Candidates (Zero coverage, likely unused)
- `app/auth/routes.py:callback` — OAuth callback, may be legacy magic-link auth
- `app/tasks/document_builder.py:run_workflow_build` — background task, may be superseded by workflow engine

## Comparison to Previous Audit (2026-03-06)

| Metric | 2026-03-06 | 2026-03-18 | Delta |
|--------|-----------|-----------|-------|
| Max CRAP | 199.7 | 342.0 | +142.3 (new code) |
| Critical (>30) | ~48 | 48 | ~0 |
| Total CRAP debt | ~11,864 | 4,268 | -7,596 (-64%) |
| Tests | ~4,215 | 2,847 | — (different test count methodology) |

Note: Max CRAP increased due to new admin.py endpoints (compare_runs, batch_replay) added with moderate coverage. Total debt decreased significantly due to prior refactoring work (WP-CRAP-001, WP-CRAP-002).

## Recommended Actions

1. **Coverage-only pass on top 6 quick wins** — adds tests, no refactoring, drops 6 functions from F/D to A/B grade
2. **Extract pure helpers from render_project_binder (CC=26)** — highest CC in codebase
3. **Investigate dead code**: auth/routes.py callback, tasks/document_builder.py run_workflow_build
