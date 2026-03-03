# CRAP Score Analysis -- 2026-03-03

## Methodology

CRAP (Change Risk Anti-Patterns) score combines cyclomatic complexity (CC)
and code coverage to identify functions that are both complex and under-tested.

    CRAP(m) = CC(m)^2 * (1 - cov(m)/100)^3 + CC(m)

| Tier | CRAP Range | Interpretation |
|------|-----------|----------------|
| Critical | > 30 | High risk -- complex and under-tested |
| Smelly | 15 -- 30 | Moderate risk -- needs attention |
| Acceptable | 5 -- 15 | Low risk -- adequate balance |
| Clean | <= 5 | Minimal risk |

Coverage source: Tier-1 tests only (2254 passed, 4 skipped, 0 failed).
Radon CC: all `app/` functions, no `-n C` filter.

---

## Summary

| Metric | Value |
|--------|-------|
| Total functions analyzed | 2,369 |
| Critical (CRAP > 30) | 147 (6.2%) |
| Smelly (15-30) | 170 (7.2%) |
| Acceptable (5-15) | 558 (23.6%) |
| Clean (<= 5) | 1,494 (63.1%) |
| Total CRAP debt | 12,053 |

### CC Distribution

| Grade | CC Range | Count | % |
|-------|----------|------:|--:|
| A | 1-5 | 2,002 | 84.5% |
| B | 6-10 | 282 | 11.9% |
| C | 11-20 | 75 | 3.2% |
| D | 21-30 | 6 | 0.3% |
| F | 31+ | 4 | 0.2% |

---

## Delta vs Previous Baselines

| Metric | Feb 27 (post-CRAP-001) | Mar 1 | Mar 3 (this) | Delta (Feb 27 -> Mar 3) |
|--------|-------:|------:|------:|--------|
| Functions analyzed | 2,299 | 2,356 | 2,369 | +70 (+3.0%) |
| Critical (>30) | 140 (6.1%) | 228 (9.7%) | 147 (6.2%) | +7 (+5.0%) |
| Smelly (15-30) | 134 (5.8%) | 201 (8.5%) | 170 (7.2%) | +36 (+26.9%) |
| Acceptable (5-15) | 465 (20.2%) | 508 (21.6%) | 558 (23.6%) | +93 (+20.0%) |
| Clean (<=5) | 1,560 (67.9%) | 1,419 (60.2%) | 1,494 (63.1%) | -66 (-4.2%) |
| Total CRAP debt | 11,864 | -- | 12,053 | +189 (+1.6%) |

### Analysis

The Mar 1 report showed 228 critical functions, which was flagged as a
coverage measurement artifact (per-function coverage attribution shifted
between AST-based mapping approaches). This run uses file-level coverage
as the basis for per-function CRAP estimation, which produces more stable
results across runs.

**Against the user-stated Feb 27 baseline (140 critical / 11,864 debt):**

- **+7 critical functions**: Modest increase from 70 new functions added
  during WB phase 2 work (WS-WB-009 through WS-WB-025). Most new code
  lands in Clean/Acceptable.
- **+189 CRAP debt (+1.6%)**: Negligible increase. New router/service
  functions are moderately complex but have file-level coverage > 50%.
- **Top offenders unchanged**: The same persistent worst functions remain
  (`_handle_result` CC=41, `QANodeExecutor.execute` CC=36, `check_promotion_validity` CC=41).
- **Coverage improvements**: Several files gained coverage from new Tier-1
  tests (work_binder.py: 52.5%, ws_proposal_service.py, task_execution_service.py,
  llm_response_parser.py).

**Conclusion**: The codebase complexity is stable. The WB phase 2 work
added functions without increasing the critical tier meaningfully. The
core WP-CRAP-001 refactoring extractions remain intact.

---

## Critical Functions by Subsystem

### Workflow Engine (41 critical)

| CRAP | CC | Coverage | File | Function |
|-----:|---:|---------:|------|----------|
| 967.4 | 41 | 18.0% | plan_executor.py:860 | PlanExecutor._handle_result |
| 710.1 | 35 | 18.0% | plan_executor.py:1730 | PlanExecutor._spawn_child_documents |
| 600.1 | 36 | 24.2% | nodes/qa.py:85 | QANodeExecutor.execute |
| 196.6 | 18 | 18.0% | plan_executor.py:287 | PlanExecutor.execute_step |
| 163.1 | 14 | 8.7% | nodes/task.py:172 | TaskNodeExecutor._build_messages |
| 151.2 | 18 | 25.6% | nodes/llm_executors.py:107 | LoggingLLMService.complete |
| 135.9 | 13 | 10.1% | nodes/gate.py:324 | GateNodeExecutor._resolve_urn |
| 86.1 | 10 | 8.7% | nodes/task.py:52 | TaskNodeExecutor.execute |
| 83.1 | 11 | 15.9% | pg_state_persistence.py:27 | PgStatePersistence.save |
| 77.7 | 11 | 18.0% | plan_executor.py:1904 | PlanExecutor._emit_stations_declared |

(+ 31 more at CRAP 30-77)

### API Services (26 critical)

| CRAP | CC | Coverage | File | Function |
|-----:|---:|---------:|------|----------|
| 461.3 | 25 | 11.3% | production_service.py:205 | get_production_tracks |
| 127.9 | 18 | 30.3% | mechanical_ops_service.py:200 | MechanicalOpsService.list_operations |
| 126.7 | 13 | 12.4% | admin_workbench_service.py:340 | AdminWorkbenchService.list_prompt_fragments |
| 126.7 | 13 | 12.4% | admin_workbench_service.py:682 | AdminWorkbenchService.list_workflows |
| 126.7 | 13 | 12.4% | admin_workbench_service.py:747 | AdminWorkbenchService.list_orchestration_workflows |
| 101.9 | 21 | 43.2% | workspace_service.py:640 | WorkspaceService._run_tier1_validation |
| 93.4 | 20 | 43.2% | workspace_service.py:242 | WorkspaceService._artifact_id_to_path |
| 87.3 | 14 | 28.0% | llm_execution_service.py:419 | LLMExecutionService._context_to_info |
| 63.5 | 9 | 12.4% | admin_workbench_service.py:438 | AdminWorkbenchService.get_prompt_fragment |
| 63.1 | 13 | 33.3% | dashboard_service.py:34 | get_dashboard_summary |

(+ 16 more at CRAP 30-61)

### API Routers (15 critical)

| CRAP | CC | Coverage | File | Function |
|-----:|---:|---------:|------|----------|
| 342.0 | 18 | 0.0% | admin.py:143 | compare_runs |
| 245.8 | 26 | 31.2% | projects.py:718 | get_document_render_model |
| 210.0 | 14 | 0.0% | accounts.py:111 | link_callback |
| 79.1 | 12 | 22.5% | production.py:205 | start_production |
| 58.8 | 12 | 31.2% | projects.py:1283 | list_work_packages |
| 56.0 | 7 | 0.0% | admin.py:474 | list_workflows |
| 43.4 | 16 | 52.5% | work_binder.py:509 | propose_work_statements |
| 42.5 | 10 | 31.2% | projects.py:540 | get_project_tree |
| 42.0 | 6 | 0.0% | admin.py:235 | replay_llm_run |
| 35.3 | 9 | 31.2% | projects.py:362 | update_project |

(+ 5 more at CRAP 30-35)

### Web Routes (10 critical)

| CRAP | CC | Coverage | File | Function |
|-----:|---:|---------:|------|----------|
| 276.3 | 23 | 21.8% | document_routes.py:264 | get_document |
| 58.6 | 10 | 21.4% | project_routes.py:405 | soft_delete_project |
| 54.6 | 9 | 17.4% | intake_workflow_routes.py:622 | _build_completion_context |
| 44.0 | 8 | 17.4% | intake_workflow_routes.py:440 | get_intake_status |
| 42.0 | 6 | 0.0% | composer_routes.py:175 | preview_render |
| 34.6 | 7 | 17.4% | intake_workflow_routes.py:87 | start_intake_workflow |
| 34.6 | 7 | 17.4% | intake_workflow_routes.py:581 | _build_message_context |
| 30.8 | 7 | 21.4% | project_routes.py:290 | archive_project |
| 30.8 | 7 | 21.4% | project_routes.py:499 | get_project |
| 30.5 | 7 | 21.8% | document_routes.py:438 | build_document |

### Domain Services (12 critical)

| CRAP | CC | Coverage | File | Function |
|-----:|---:|---------:|------|----------|
| 72.0 | 8 | 0.0% | prompt_assembler.py:90 | PromptAssembler.assemble |
| 72.0 | 8 | 0.0% | ux_config_service.py:140 | UXConfigService.get_primary_action |
| 60.5 | 11 | 25.8% | document_builder.py:419 | DocumentBuilder.build_stream |
| 56.0 | 7 | 0.0% | schema_resolver.py:210 | SchemaResolver._walk_for_refs |
| 56.0 | 7 | 0.0% | schema_resolver.py:260 | SchemaResolver._rewrite_refs |
| 42.1 | 9 | 25.8% | document_builder.py:358 | DocumentBuilder.build |
| 42.0 | 6 | 0.0% | prompt_assembler.py:165 | PromptAssembler._build_schema_bundle |
| 40.0 | 9 | 27.4% | render_model_builder.py:457 | RenderModelBuilder._compute_schema_bundle_sha256 |
| 34.2 | 8 | 25.8% | document_builder.py:280 | DocumentBuilder._complete_llm_logging |
| 32.5 | 8 | 27.4% | render_model_builder.py:310 | RenderModelBuilder.build |
| 31.9 | 7 | 20.2% | document_condenser.py:155 | DocumentCondenser._split_sections |
| 30.2 | 20 | 70.5% | base_handler.py:121 | BaseDocumentHandler.validate |

### Domain Handlers (6 critical)

| CRAP | CC | Coverage | File | Function |
|-----:|---:|---------:|------|----------|
| 52.1 | 9 | 19.0% | architecture_spec_handler.py:48 | transform_architecture_spec |
| 52.1 | 9 | 19.0% | architecture_spec_handler.py:112 | ArchitectureSpecHandler.validate |
| 52.1 | 9 | 19.0% | architecture_spec_handler.py:177 | ArchitectureSpecHandler.render |
| 52.1 | 9 | 19.0% | architecture_spec_handler.py:349 | ArchitectureSpecHandler._render_components |
| 42.0 | 8 | 19.0% | architecture_spec_handler.py:234 | ArchitectureSpecHandler.render_summary |
| 33.1 | 7 | 19.0% | architecture_spec_handler.py:450 | ArchitectureSpecHandler._render_interfaces |

### Auth (4 critical)

| CRAP | CC | Coverage | File | Function |
|-----:|---:|---------:|------|----------|
| 132.0 | 11 | 0.0% | routes.py:157 | callback |
| 90.0 | 9 | 0.0% | routes.py:33 | validate_origin |
| 30.8 | 7 | 21.4% | oidc_config.py:150 | OIDCConfig.normalize_claims |
| 139.5 | 16 | 21.6% | secret_ingress.py:41 | SecretIngressMiddleware.dispatch |

### LLM (3 critical)

| CRAP | CC | Coverage | File | Function |
|-----:|---:|---------:|------|----------|
| 91.9 | 16 | 33.3% | output_parser.py:115 | OutputValidator._validate_type |
| 73.6 | 12 | 24.6% | anthropic.py:58 | AnthropicProvider.complete |
| 72.0 | 8 | 0.0% | health.py:66 | HealthChecker.check_health |

### Other Subsystems (30 critical)

Spread across: config_validator (4), execution (3), persistence (4),
observability (2), tasks (1), project_creation_service (2),
project_service (2), cost_service (1), git_service (2),
release_service (1), preview_service (2), registry (1), workflows (1),
interrupts (1), production_state (1).

---

## Top 10 Persistent Worst Functions

| # | Function | CRAP | CC | Coverage | Subsystem |
|---|----------|-----:|---:|---------:|-----------|
| 1 | PlanExecutor._handle_result | 967.4 | 41 | 18.0% | Workflow |
| 2 | PlanExecutor._spawn_child_documents | 710.1 | 35 | 18.0% | Workflow |
| 3 | QANodeExecutor.execute | 600.1 | 36 | 24.2% | Workflow |
| 4 | get_production_tracks | 461.3 | 25 | 11.3% | API Services |
| 5 | compare_runs | 342.0 | 18 | 0.0% | API Routers |
| 6 | JSONFormatter.format | 342.0 | 18 | 0.0% | Observability |
| 7 | get_document (web) | 276.3 | 23 | 21.8% | Web Routes |
| 8 | get_document_render_model | 245.8 | 26 | 31.2% | API Routers |
| 9 | link_callback | 210.0 | 14 | 0.0% | API Routers |
| 10 | PlanExecutor.execute_step | 196.6 | 18 | 18.0% | Workflow |

---

## Notable Changes Since Mar 1

### Improved

- `check_promotion_validity` (CC=41): CRAP dropped from ~1700 to 43.5
  due to coverage improvement (88.6% file coverage from validation rule tests).
- `BaseDocumentHandler.validate` (CC=20): CRAP = 30.2 (borderline),
  down from prior audits due to 70.5% coverage.
- `work_binder.py:propose_work_statements` (CC=16): CRAP = 43.4 with
  52.5% file coverage from new WS-WB-022/025 tests.

### New Entrants

- No new functions entered the top 20 worst.
- 13 new functions from WB work are all in Clean/Acceptable/Smelly tiers.

### Coverage Gains

| File | Coverage | Source |
|------|----------|--------|
| work_binder.py | 52.5% | WS-WB-003/006/025 tests |
| ws_proposal_service.py | (new) | WS-WB-025 tests |
| task_execution_service.py | (new) | WS-WB-022 tests |
| llm_response_parser.py | (new) | Parser bug fix tests |
| validation/rules.py | 88.6% | Promotion validator tests |

---

## Recommendations

1. **Workflow Engine remains the #1 hotspot**: 41 critical functions.
   `_handle_result` (CC=41) and `_spawn_child_documents` (CC=35) need
   architectural decomposition. These are the same persistent offenders
   from all prior audits.

2. **Zero-coverage files**: `admin.py`, `accounts.py`, `auth/routes.py`,
   `observability/logging.py`, `prompt_assembler.py`, `schema_resolver.py`,
   `ux_config_service.py` have 0% Tier-1 coverage. Adding basic unit tests
   to these files would drop ~15 functions out of critical.

3. **Coverage measurement**: This audit uses file-level coverage as the
   proxy for per-function coverage. This is more stable than AST-based
   per-function mapping but may overestimate coverage for large files
   with both tested and untested functions.
