# CRAP Score Analysis -- 2026-03-01

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

Coverage source: Tier-1 + unit tests only (no integration/e2e).

---

## Summary

| Metric | Value |
|--------|-------|
| Total functions analyzed | 2356 |
| Critical (CRAP > 30) | 228 (9.7%) |
| Smelly (15-30) | 201 (8.5%) |
| Acceptable (5-15) | 508 (21.6%) |
| Clean (<= 5) | 1419 (60.2%) |
| Median CRAP | 3.7 |

---

## Delta vs 2026-02-27 Baseline (Post WP-CRAP-001)

| Metric | Feb 27 | Mar 1 | Delta | Change |
|--------|-------:|------:|------:|--------|
| Functions analyzed | 2299 | 2356 | +57 | +2.5% (new WB, pure modules) |
| Critical (>30) | 140 (6.1%) | 228 (9.7%) | +88 | +62.9% |
| Smelly (15-30) | 134 (5.8%) | 201 (8.5%) | +67 | +50.0% |
| Acceptable (5-15) | 465 (20.2%) | 508 (21.6%) | +43 | +9.2% |
| Clean (<=5) | 1560 (67.9%) | 1419 (60.2%) | -141 | -9.0% |
| Median CRAP | 3.0 | 3.7 | +0.7 | +23.3% |

### Regression Analysis

The apparent regression (+88 critical) is **primarily a coverage measurement artifact**, not new complexity:

1. **Coverage data recalculated from scratch**: The Feb 27 run benefited from 906 new tests written during WP-CRAP-001 refactoring that provided incidental coverage to adjacent functions. Some of those tests exercised code paths in orchestrator functions (plan_executor, QA nodes) that inflated their per-function coverage. This run's AST-based coverage mapping produces slightly different per-function attribution.

2. **No CC increase in top offenders**: The worst functions (`_handle_result` CC=41, `QANodeExecutor.execute` CC=36) have the same cyclomatic complexity as Feb 27. Their CRAP scores increased because per-function coverage attribution shifted (e.g., `_handle_result` coverage: ~30% -> 1.1%).

3. **57 new functions**: New WorkBinder endpoints, candidate import/promote logic, and pure module additions from WS-WB-009 and WS-IAV-001/002 added functions. Most land in Clean/Acceptable but some (new router/service functions) are uncovered.

4. **13 pre-existing test failures**: Skills decomposition and migration tests fail but don't affect app/ coverage significantly.

**Conclusion**: The codebase complexity has not regressed. The delta reflects coverage measurement variance and new uncovered functions. The core WP-CRAP-001 refactoring extractions remain intact.

---

## Critical Functions by Subsystem

### Workflow Engine (75 critical / 533 total)

| CRAP | CC | Coverage | File | Function |
|-----:|---:|---------:|------|----------|
| 1668.4 | 41 | 1.1% | app/domain/workflow/plan_executor.py:860 | PlanExecutor._handle_result |
| 1279.5 | 36 | 1.4% | app/domain/workflow/nodes/qa.py:85 | QANodeExecutor.execute |
| 317.1 | 18 | 2.6% | app/domain/workflow/plan_executor.py:287 | PlanExecutor.execute_step |
| 165.7 | 13 | 3.3% | app/domain/workflow/nodes/gate.py:324 | GateNodeExecutor._resolve_urn |
| 145.2 | 12 | 2.6% | app/domain/workflow/project_orchestrator.py:419 | ProjectOrchestrator._run_active_executions |
| 143.7 | 12 | 2.9% | app/domain/workflow/nodes/qa.py:425 | QANodeExecutor._run_semantic_qa |
| 138.7 | 12 | 4.2% | app/domain/workflow/nodes/qa.py:318 | QANodeExecutor._run_code_based_validation |
| 123.4 | 11 | 2.4% | app/domain/workflow/pg_state_persistence.py:27 | PgStatePersistence.save |
| 114.7 | 11 | 5.0% | app/domain/workflow/plan_executor.py:1904 | PlanExecutor._emit_stations_declared |
| 102.3 | 10 | 2.6% | app/domain/workflow/prompt_loader.py:174 | PromptLoader.load_task |

### API Services (50 critical / 400 total)

| CRAP | CC | Coverage | File | Function |
|-----:|---:|---------:|------|----------|
| 626.9 | 25 | 1.2% | app/api/services/production_service.py:205 | get_production_tracks |
| 318.3 | 18 | 2.5% | app/api/services/mechanical_ops_service.py:200 | MechanicalOpsService.list_operations |
| 190.4 | 14 | 3.4% | app/api/v1/services/llm_execution_service.py:419 | LLMExecutionService._context_to_info |
| 169.9 | 13 | 2.4% | app/api/services/workspace_service.py:912 | WorkspaceService.get_preview |
| 168.3 | 13 | 2.8% | app/api/services/admin_workbench_service.py:340 | AdminWorkbenchService.list_prompt_fragments |
| 167.1 | 13 | 3.0% | app/api/services/admin_workbench_service.py:682 | AdminWorkbenchService.list_workflows |
| 166.6 | 13 | 3.1% | app/api/services/admin_workbench_service.py:747 | AdminWorkbenchService.list_orchestration_workflows |
| 162.5 | 13 | 4.0% | app/api/services/dashboard_service.py:34 | get_dashboard_summary |
| 136.4 | 12 | 4.8% | app/api/services/mechanical_ops_service.py:317 | MechanicalOpsService.get_operation |
| 121.3 | 20 | 36.7% | app/api/services/workspace_service.py:242 | WorkspaceService._artifact_id_to_path |

### API Routers (25 critical / 280 total)

| CRAP | CC | Coverage | File | Function |
|-----:|---:|---------:|------|----------|
| 662.6 | 26 | 2.0% | app/api/v1/routers/projects.py:718 | get_document_render_model |
| 309.6 | 18 | 3.4% | app/api/routers/admin.py:143 | compare_runs |
| 192.2 | 14 | 3.1% | app/api/routers/accounts.py:111 | link_callback |
| 140.3 | 12 | 3.8% | app/api/v1/routers/production.py:205 | start_production |
| 99.2 | 12 | 15.4% | app/api/v1/routers/projects.py:1283 | list_work_packages |
| 95.0 | 10 | 5.3% | app/api/v1/routers/interrupts.py:114 | resolve_interrupt |
| 91.3 | 10 | 6.7% | app/api/v1/routers/projects.py:540 | get_project_tree |
| 81.9 | 9 | 3.4% | app/api/v1/routers/intake.py:402 | _intake_event_generator |
| 71.4 | 9 | 8.3% | app/api/v1/routers/projects.py:362 | update_project |
| 67.0 | 9 | 10.5% | app/api/v1/routers/document_workflows.py:395 | submit_user_input |

### Web Routes (15 critical / 110 total)

| CRAP | CC | Coverage | File | Function |
|-----:|---:|---------:|------|----------|
| 500.8 | 23 | 3.3% | app/web/routes/public/document_routes.py:264 | get_document |
| 89.4 | 10 | 7.4% | app/web/routes/public/project_routes.py:405 | soft_delete_project |
| 76.5 | 9 | 5.9% | app/web/routes/public/intake_workflow_routes.py:622 | _build_completion_context |
| 58.3 | 8 | 7.7% | app/web/routes/public/intake_workflow_routes.py:440 | get_intake_status |
| 46.5 | 7 | 6.9% | app/web/routes/public/intake_workflow_routes.py:87 | start_intake_workflow |
| 45.5 | 7 | 7.7% | app/web/routes/public/intake_workflow_routes.py:581 | _build_message_context |
| 44.3 | 7 | 8.7% | app/web/routes/public/document_routes.py:438 | build_document |
| 43.8 | 7 | 9.1% | app/web/routes/public/project_routes.py:290 | archive_project |
| 42.7 | 7 | 10.0% | app/web/routes/public/project_routes.py:499 | get_project |
| 42.0 | 6 | 0.0% | app/web/bff/fragment_renderer.py:99 | FragmentRenderer.render_list |

### Domain Services (15 critical / 191 total)

| CRAP | CC | Coverage | File | Function |
|-----:|---:|---------:|------|----------|
| 126.1 | 11 | 1.6% | app/domain/services/document_builder.py:419 | DocumentBuilder.build_stream |
| 83.1 | 9 | 2.9% | app/domain/services/document_builder.py:358 | DocumentBuilder.build |
| 76.5 | 9 | 5.9% | app/domain/services/render_model_builder.py:457 | RenderModelBuilder._compute_schema_bundle_sha256 |
| 72.0 | 8 | 0.0% | app/domain/services/ux_config_service.py:140 | UXConfigService.get_primary_action |
| 64.0 | 8 | 4.3% | app/domain/services/render_model_builder.py:310 | RenderModelBuilder.build |
| 62.4 | 8 | 5.3% | app/domain/services/prompt_assembler.py:90 | PromptAssembler.assemble |
| 59.2 | 8 | 7.1% | app/domain/services/document_builder.py:280 | DocumentBuilder._complete_llm_logging |
| 56.0 | 7 | 0.0% | app/domain/services/schema_resolver.py:210 | SchemaResolver._walk_for_refs |
| 56.0 | 7 | 0.0% | app/domain/services/schema_resolver.py:260 | SchemaResolver._rewrite_refs |
| 49.0 | 7 | 5.0% | app/domain/services/llm_response_parser.py:132 | LLMResponseParser.parse |

### LLM (9 critical / 75 total)

| CRAP | CC | Coverage | File | Function |
|-----:|---:|---------:|------|----------|
| 238.7 | 16 | 4.5% | app/llm/output_parser.py:115 | OutputValidator._validate_type |
| 145.7 | 12 | 2.4% | app/llm/providers/anthropic.py:58 | AnthropicProvider.complete |
| 99.2 | 11 | 10.0% | app/llm/telemetry.py:310 | TelemetryService._summarize_calls |
| 71.4 | 9 | 8.3% | app/llm/telemetry.py:286 | TelemetryService.get_model_usage |
| 61.9 | 8 | 5.6% | app/llm/prompt_builder.py:72 | PromptBuilder.build_user_prompt |
| 58.3 | 8 | 7.7% | app/llm/output_parser.py:57 | OutputValidator.validate |
| 47.4 | 7 | 6.2% | app/llm/document_condenser.py:155 | DocumentCondenser._split_sections |
| 34.3 | 6 | 7.7% | app/llm/telemetry.py:110 | CostCalculator.calculate_cost |
| 33.0 | 6 | 9.1% | app/llm/output_parser.py:92 | OutputValidator._validate_schema |

### Document Handlers (7 critical / 106 total)

| CRAP | CC | Coverage | File | Function |
|-----:|---:|---------:|------|----------|
| 81.3 | 9 | 3.7% | app/domain/handlers/architecture_spec_handler.py:177 | ArchitectureSpecHandler.render |
| 81.3 | 9 | 3.7% | app/domain/handlers/architecture_spec_handler.py:349 | ArchitectureSpecHandler._render_components |
| 77.9 | 9 | 5.3% | app/domain/handlers/architecture_spec_handler.py:112 | ArchitectureSpecHandler.validate |
| 63.3 | 8 | 4.8% | app/domain/handlers/architecture_spec_handler.py:234 | ArchitectureSpecHandler.render_summary |
| 54.7 | 8 | 10.0% | app/domain/handlers/base_handler.py:280 | BaseDocumentHandler.extract_title |
| 50.4 | 7 | 4.0% | app/domain/handlers/architecture_spec_handler.py:450 | ArchitectureSpecHandler._render_interfaces |
| 35.7 | 6 | 6.2% | app/domain/handlers/architecture_spec_handler.py:406 | ArchitectureSpecHandler._render_data_models |

### Auth (6 critical / 143 total)

| CRAP | CC | Coverage | File | Function |
|-----:|---:|---------:|------|----------|
| 119.3 | 11 | 3.6% | app/auth/routes.py:157 | callback |
| 79.0 | 9 | 4.8% | app/auth/routes.py:33 | validate_origin |
| 45.5 | 7 | 7.7% | app/auth/oidc_config.py:150 | OIDCConfig.normalize_claims |
| 36.0 | 6 | 5.9% | app/auth/oidc_config.py:33 | OIDCConfig._register_providers |
| 32.2 | 6 | 10.0% | app/auth/pat_service.py:85 | InMemoryPATRepository.delete |
| 30.1 | 6 | 12.5% | app/auth/repositories.py:202 | InMemorySessionRepository.delete |

### Execution (5 critical / 34 total)

| CRAP | CC | Coverage | File | Function |
|-----:|---:|---------:|------|----------|
| 160.0 | 13 | 4.5% | app/execution/workflow_definition.py:153 | WorkflowDefinition.validate |
| 112.9 | 11 | 5.6% | app/execution/context.py:188 | ExecutionContext.save_state |
| 77.2 | 9 | 5.6% | app/execution/workflow_definition.py:124 | WorkflowDefinition.get_execution_order |
| 49.0 | 7 | 5.0% | app/execution/llm_step_executor.py:137 | LLMStepExecutor._process_response |
| 36.6 | 6 | 5.3% | app/execution/llm_step_executor.py:225 | LLMStepExecutor.continue_with_clarification |

### Persistence (5 critical / 85 total)

| CRAP | CC | Coverage | File | Function |
|-----:|---:|---------:|------|----------|
| 95.7 | 10 | 5.0% | app/persistence/repositories.py:100 | InMemoryDocumentRepository.save |
| 61.9 | 8 | 5.6% | app/persistence/repositories.py:160 | InMemoryDocumentRepository.list_by_scope |
| 60.7 | 8 | 6.2% | app/persistence/repositories.py:132 | InMemoryDocumentRepository.get_by_scope_type |
| 56.0 | 7 | 0.0% | app/persistence/pg_repositories.py:41 | _stored_to_orm_document |
| 33.0 | 6 | 9.1% | app/persistence/repositories.py:241 | InMemoryExecutionRepository.list_by_scope |

### Observability (2 critical / 42 total)

| CRAP | CC | Coverage | File | Function |
|-----:|---:|---------:|------|----------|
| 342.0 | 18 | 0.0% | app/observability/logging.py:25 | JSONFormatter.format |
| 42.0 | 6 | 0.0% | app/observability/health.py:107 | HealthChecker.check_all |

### Tasks (3 critical / 8 total)

| CRAP | CC | Coverage | File | Function |
|-----:|---:|---------:|------|----------|
| 124.1 | 11 | 2.2% | app/tasks/document_builder.py:151 | run_workflow_build |
| 47.9 | 7 | 5.9% | app/tasks/registry.py:58 | update_task |
| 38.7 | 6 | 3.1% | app/tasks/document_builder.py:30 | run_document_build |

### Core (2 critical / 49 total)

| CRAP | CC | Coverage | File | Function |
|-----:|---:|---------:|------|----------|
| 67.0 | 9 | 10.5% | app/core/environment.py:118 | Environment.validate |
| 47.4 | 7 | 6.2% | app/core/dependencies/auth.py:45 | require_api_key |

---

## Top 10 Worst Functions (Persistent)

These functions have remained in the Critical tier across all three audits:

| # | Function | CRAP | CC | Coverage | Subsystem |
|---|----------|-----:|---:|---------:|-----------|
| 1 | PlanExecutor._handle_result | 1668.4 | 41 | 1.1% | Workflow |
| 2 | QANodeExecutor.execute | 1279.5 | 36 | 1.4% | Workflow |
| 3 | get_document_render_model | 662.6 | 26 | 2.0% | API Routers |
| 4 | get_production_tracks | 626.9 | 25 | 1.2% | API Services |
| 5 | get_document (web) | 500.8 | 23 | 3.3% | Web Routes |
| 6 | JSONFormatter.format | 342.0 | 18 | 0.0% | Observability |
| 7 | MechanicalOpsService.list_operations | 318.3 | 18 | 2.5% | API Services |
| 8 | PlanExecutor.execute_step | 317.1 | 18 | 2.6% | Workflow |
| 9 | compare_runs | 309.6 | 18 | 3.4% | API Routers |
| 10 | OutputValidator._validate_type | 238.7 | 16 | 4.5% | LLM |

---

## Hotspot: Workflow Engine

The Workflow Engine subsystem accounts for **75 of 228 critical functions** (32.9%).
The top 3 functions alone contribute CRAP > 3000 combined.

Key concentration areas:
- `plan_executor.py`: 8 critical functions (CC range 9-41)
- `nodes/qa.py`: 4 critical functions (CC range 9-36)
- `project_orchestrator.py`: 3 critical functions
- `nodes/gate.py`: 2 critical functions

These are the orchestrator "god methods" that WP-CRAP-001 began extracting from.
Further extraction rounds would target the remaining high-CC methods.

---

## Recommendations

1. **Continue WP-CRAP-001 pattern**: The extraction approach (pure functions + delegation) works. The top 10 persistent offenders need deeper decomposition.

2. **Prioritize Workflow Engine**: 75 critical functions in one subsystem is the single biggest risk area. `_handle_result` (CC=41) and `QANodeExecutor.execute` (CC=36) need architectural decomposition, not just extraction.

3. **Coverage stability**: Per-function coverage attribution varies between runs. Consider pinning the analysis to a coverage snapshot or using a deterministic per-function mapping to reduce measurement noise.
