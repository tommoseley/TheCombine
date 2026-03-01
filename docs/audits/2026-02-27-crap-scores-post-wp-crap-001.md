# CRAP Score Analysis -- 2026-02-27 (Post WP-CRAP-001)

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

---

## Summary

| Metric | Value |
|--------|-------|
| Total functions analyzed | 2299 |
| Critical (CRAP > 30) | 140 (6.1%) |
| Smelly (15-30) | 134 (5.8%) |
| Acceptable (5-15) | 465 (20.2%) |
| Clean (<= 5) | 1560 (67.9%) |
| Median CRAP | 3.0 |

---

## Delta vs 2026-02-26 Baseline

| Metric | Before (Feb 26) | After (Feb 27) | Delta | Change |
|--------|---------------:|---------------:|------:|--------|
| Functions analyzed | 2175 | 2299 | +124 | +5.7% (new pure modules) |
| Critical (>30) | 262 (12.0%) | 140 (6.1%) | -122 | -46.6% |
| Smelly (15-30) | 205 (9.4%) | 134 (5.8%) | -71 | -34.6% |
| Acceptable (5-15) | 420 (19.3%) | 465 (20.2%) | +45 | +10.7% |
| Clean (<=5) | 1288 (59.2%) | 1560 (67.9%) | +272 | +21.1% |
| Median CRAP | 3.7 | 3.0 | -0.7 | -18.9% |

### Functions Eliminated from Critical Tier

122 functions dropped out of the Critical tier. The causes:

1. **Extracted to pure modules (WS-CRAP-001 through 007)**: 57 target functions
   were thinned, reducing their CC. The extracted pure functions are new, small,
   and high-coverage -- they land in Clean or Acceptable tiers.

2. **Coverage improvement from 906 new tests**: Even functions that were not
   direct refactoring targets benefit from incidental coverage gained by importing
   and exercising their modules in the new test files.

3. **CC reduction via delegation**: Thinned orchestrator methods that now delegate
   to pure functions have lower cyclomatic complexity, pushing many from Critical
   into Smelly or Acceptable.

### Key Score Movements (WP-CRAP-001 Targets)

| Function | Before | After | Delta | WS |
|----------|-------:|------:|------:|-----|
| PlanExecutor._handle_result() | 2190.4 | 231.4 | -1959.0 | WS-CRAP-001 |
| QANodeExecutor.execute() | 1580.7 | 145.2 | -1435.5 | WS-CRAP-001 |
| get_production_tracks() | 1020.7 | 626.9 | -393.8 | WS-CRAP-003 |
| QANodeExecutor._parse_qa_response() | 714.0 | -- | eliminated | WS-CRAP-001 |
| PlanExecutor._filter_excluded_topics() | 720.7 | -- | eliminated | WS-CRAP-001 |
| AdminWorkbenchService.list_prompt_fragments() | 660.6 | 168.7 | -491.9 | WS-CRAP-003 |
| PlanExecutor.execute_step() | 528.0 | 37.9 | -490.1 | WS-CRAP-001 |
| InvariantPinnerHandler.execute() | 506.0 | 36.6 | -469.4 | WS-CRAP-004 |
| _repair_truncated_json() | 429.7 | 21.2 | -408.5 | WS-CRAP-002 |
| _resolve_answer_label() | 288.1 | 18.0 | -270.1 | WS-CRAP-002 |
| _build_pgc_from_context_state() | 260.5 | -- | eliminated | WS-CRAP-002 |
| _build_completion_context() | 333.0 | -- | eliminated | WS-CRAP-006 |
| _build_template_context() | 218.9 | -- | eliminated | WS-CRAP-006 |
| _render_workflow_state() | 143.3 | -- | eliminated | WS-CRAP-006 |
| get_document() (document_routes) | 237.9 | 500.8 | +262.9 | WS-CRAP-006 (see note) |
| PgStatePersistence._row_to_state() | 312.5 | -- | eliminated | WS-CRAP-007 |
| PlanExecutor._pin_invariants() | 256.3 | -- | eliminated | WS-CRAP-007 |
| PlanExecutor._persist_produced_documents() | 228.6 | 71.4 | -157.2 | WS-CRAP-007 |
| QANodeExecutor._run_semantic_qa() | 193.2 | 62.6 | -130.6 | WS-CRAP-007 |
| GateNodeExecutor._execute_pgc_gate() | 171.0 | 39.0 | -132.0 | WS-CRAP-007 |
| PlanExecutor._extract_qa_feedback() | 165.1 | -- | eliminated | WS-CRAP-001 |
| RenderModelBuilder._process_derived_section() | 140.6 | -- | eliminated | WS-CRAP-005 |
| PromptAssembler.assemble() | 167.5 | -- | eliminated | WS-CRAP-005 |
| DocumentBuilder.build_stream() | 229.8 | 126.1 | -103.7 | WS-CRAP-005 |
| ExclusionFilterHandler.execute() | 272.0 | 36.6 | -235.4 | WS-CRAP-004 |
| ProjectDiscoveryHandler.render() | 356.5 | 19.0 | -337.5 | WS-CRAP-004 |

> **Note on get_document()**: CRAP increased because the refactoring reduced CC
> (from 16 to 23 -- radon re-measured after code changes shifted line numbers and
> the function absorbed context from removed helpers). This function remains a
> future refactoring target.

### Subsystem Risk Comparison

| Subsystem | Before Crit | After Crit | Delta | Before Debt | After Debt | Debt Delta |
|-----------|------------:|-----------:|------:|------------:|-----------:|-----------:|
| Workflow Engine | 79 | 44 | -35 | 11357.9 | 2939.8 | -8418.1 |
| API Services | 35 | 29 | -6 | 5473.0 | 3097.3 | -2375.7 |
| API v1 Routers | 21 | 10 | -11 | 4815.8 | 1380.3 | -3435.5 |
| Document Handlers | 31 | 18 | -13 | 3573.4 | 1127.5 | -2445.9 |
| Other | 25 | 16 | -9 | 1928.2 | 1286.7 | -641.5 |
| Domain Services | 23 | 4 | -19 | 1781.1 | 315.8 | -1465.3 |
| Web Routes | 19 | 10 | -9 | 1658.4 | 916.9 | -741.5 |
| LLM Layer | 9 | 1 | -8 | 789.9 | 145.7 | -644.2 |
| Core/Observability | 4 | 1 | -3 | 498.4 | 47.4 | -451.0 |
| Execution | 5 | 0 | -5 | 435.7 | 0.0 | -435.7 |
| Auth | 6 | 3 | -3 | 342.1 | 243.8 | -98.3 |
| Persistence | 5 | 0 | -5 | 307.3 | 0.0 | -307.3 |

**Total CRAP debt reduction: 32,960.3 to 11,863.9 (-64.0%)**

---

## Critical Functions by Subsystem

| Subsystem | Critical Count | Worst CRAP | Worst Function |
|-----------|---------------|------------|----------------|
| API Services | 29 | 626.9 | get_production_tracks() |
| Workflow Engine | 29 | 231.4 | PlanExecutor._handle_result() |
| Other | 16 | 309.6 | compare_runs() |
| Workflow Nodes | 15 | 165.7 | GateNodeExecutor._resolve_urn() |
| Mech Handlers | 11 | 100.9 | RouterHandler.execute() |
| API v1 Routers | 10 | 662.6 | get_document_render_model() |
| Web Routes | 10 | 500.8 | get_document() |
| Document Handlers | 7 | 81.3 | ArchitectureSpecHandler.render() |
| Domain Services | 4 | 126.1 | DocumentBuilder.build_stream() |
| API v1 Services | 4 | 190.4 | LLMExecutionService._context_to_info() |
| Auth | 3 | 119.3 | callback() |
| LLM Layer | 1 | 145.7 | AnthropicProvider.complete() |
| Core/Observability | 1 | 47.4 | require_api_key() |

---

### Workflow Engine (29 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 231.4 | 41 | 51.6% | app/domain/workflow/plan_executor.py:860 | PlanExecutor._handle_result() |
| 145.2 | 12 | 2.6% | app/domain/workflow/project_orchestrator.py:419 | ProjectOrchestrator._run_active_executions() |
| 123.4 | 11 | 2.4% | app/domain/workflow/pg_state_persistence.py:27 | PgStatePersistence.save() |
| 81.0 | 9 | 3.8% | app/domain/workflow/workflow_executor.py:130 | WorkflowExecutor.process_clarification() |
| 78.4 | 9 | 5.0% | app/domain/workflow/project_orchestrator.py:547 | ProjectOrchestrator._calculate_final_status() |
| 75.7 | 9 | 6.2% | app/domain/workflow/plan_executor.py:1562 | PlanExecutor._build_invariant_statement() |
| 71.4 | 9 | 8.3% | app/domain/workflow/plan_executor.py:1601 | PlanExecutor._persist_produced_documents() |
| 69.9 | 9 | 9.1% | app/domain/workflow/plan_executor.py:1120 | PlanExecutor._find_generating_node() |
| 66.7 | 8 | 2.9% | app/domain/workflow/plan_executor.py:731 | PlanExecutor._load_pgc_answers_for_qa() |
| 65.9 | 10 | 17.6% | app/domain/workflow/plan_executor.py:1157 | PlanExecutor._persist_conversation() |
| 65.9 | 9 | 11.1% | app/domain/workflow/project_orchestrator.py:528 | ProjectOrchestrator._update_blocked_states() |
| 64.9 | 8 | 3.8% | app/domain/workflow/project_orchestrator.py:89 | ProjectOrchestrator.run_full_line() |
| 64.6 | 8 | 4.0% | app/domain/workflow/step_executor.py:269 | StepExecutor._build_user_prompt_with_answers() |
| 61.9 | 8 | 5.6% | app/domain/workflow/project_orchestrator.py:494 | ProjectOrchestrator._wait_for_completions() |
| 56.1 | 8 | 9.1% | app/domain/workflow/project_orchestrator.py:278 | ProjectOrchestrator._find_ready_documents() |
| 52.5 | 11 | 30.0% | app/domain/workflow/plan_executor.py:1904 | PlanExecutor._emit_stations_declared() |
| 50.4 | 7 | 4.0% | app/domain/workflow/outcome_recorder.py:49 | OutcomeRecorder.record_outcome() |
| 49.9 | 7 | 4.3% | app/domain/workflow/plan_executor.py:1420 | PlanExecutor._promote_pgc_invariants_to_document() |
| 48.3 | 7 | 5.6% | app/domain/workflow/plan_executor.py:691 | PlanExecutor._get_pgc_questions_for_merge() |
| 47.4 | 7 | 6.2% | app/domain/workflow/outcome_recorder.py:188 | OutcomeRecorder._build_routing_rationale() |
| 46.2 | 7 | 7.1% | app/domain/workflow/interrupt_registry.py:126 | _build_interrupt_payload() |
| 44.7 | 7 | 8.3% | app/domain/workflow/interrupt_registry.py:94 | _determine_interrupt_type() |
| 42.5 | 41 | 90.4% | app/domain/workflow/validation/rules.py:103 | check_promotion_validity() |
| 38.4 | 6 | 3.4% | app/domain/workflow/plan_executor.py:389 | PlanExecutor._handle_pgc_user_answers() |
| 37.9 | 18 | 60.5% | app/domain/workflow/plan_executor.py:287 | PlanExecutor.execute_step() |
| 37.1 | 35 | 88.0% | app/domain/workflow/plan_executor.py:1730 | PlanExecutor._spawn_child_documents() |
| 36.3 | 6 | 5.6% | app/domain/workflow/project_orchestrator.py:233 | ProjectOrchestrator._run_orchestration_loop() |
| 34.3 | 6 | 7.7% | app/domain/workflow/plan_executor.py:1490 | PlanExecutor._embed_pgc_clarifications() |
| 31.8 | 6 | 10.5% | app/domain/workflow/step_state.py:227 | StepState.from_dict() |

### Workflow Nodes (15 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 165.7 | 13 | 3.3% | app/domain/workflow/nodes/gate.py:324 | GateNodeExecutor._resolve_urn() |
| 145.2 | 36 | 56.2% | app/domain/workflow/nodes/qa.py:85 | QANodeExecutor.execute() |
| 98.5 | 10 | 4.0% | app/domain/workflow/nodes/intake_gate_profile.py:316 | IntakeGateProfileExecutor._extract_classification_fallback() |
| 81.0 | 9 | 3.8% | app/domain/workflow/nodes/task.py:363 | TaskNodeExecutor._format_pgc_questions() |
| 80.3 | 9 | 4.2% | app/domain/workflow/nodes/intake_gate_profile.py:191 | IntakeGateProfileExecutor._execute_confirmation_phase() |
| 64.6 | 8 | 4.0% | app/domain/workflow/nodes/task.py:313 | TaskNodeExecutor._render_qa_feedback() |
| 62.6 | 12 | 29.4% | app/domain/workflow/nodes/qa.py:425 | QANodeExecutor._run_semantic_qa() |
| 61.9 | 8 | 5.6% | app/domain/workflow/nodes/mock_executors.py:135 | MockGateExecutor.execute() |
| 46.8 | 7 | 6.7% | app/domain/workflow/nodes/gate.py:214 | GateNodeExecutor._execute_gate_profile() |
| 39.0 | 6 | 2.9% | app/domain/workflow/nodes/gate.py:377 | GateNodeExecutor._execute_pgc_gate() |
| 36.1 | 14 | 51.7% | app/domain/workflow/nodes/task.py:172 | TaskNodeExecutor._build_messages() |
| 35.4 | 10 | 36.7% | app/domain/workflow/nodes/intake_gate_profile.py:92 | IntakeGateProfileExecutor._execute_initial_phase() |
| 34.9 | 12 | 45.8% | app/domain/workflow/nodes/qa.py:318 | QANodeExecutor._run_code_based_validation() |
| 34.8 | 6 | 7.1% | app/domain/workflow/nodes/intake_gate_profile.py:371 | IntakeGateProfileExecutor._execute_extraction() |
| 32.9 | 18 | 64.2% | app/domain/workflow/nodes/llm_executors.py:107 | LoggingLLMService.complete() |

### API Services (29 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 626.9 | 25 | 1.2% | app/api/services/production_service.py:205 | get_production_tracks() |
| 318.3 | 18 | 2.5% | app/api/services/mechanical_ops_service.py:200 | MechanicalOpsService.list_operations() |
| 169.9 | 13 | 2.4% | app/api/services/workspace_service.py:912 | WorkspaceService.get_preview() |
| 168.7 | 13 | 2.7% | app/api/services/admin_workbench_service.py:352 | AdminWorkbenchService.list_prompt_fragments() |
| 167.1 | 13 | 3.0% | app/api/services/admin_workbench_service.py:695 | AdminWorkbenchService.list_workflows() |
| 166.6 | 13 | 3.1% | app/api/services/admin_workbench_service.py:760 | AdminWorkbenchService.list_orchestration_workflows() |
| 162.5 | 13 | 4.0% | app/api/services/dashboard_service.py:34 | get_dashboard_summary() |
| 136.4 | 12 | 4.8% | app/api/services/mechanical_ops_service.py:317 | MechanicalOpsService.get_operation() |
| 121.3 | 20 | 36.7% | app/api/services/workspace_service.py:242 | WorkspaceService._artifact_id_to_path() |
| 107.9 | 11 | 7.1% | app/api/services/preview_service.py:442 | PreviewService._diff_prompts() |
| 98.5 | 10 | 4.0% | app/api/services/workspace_service.py:849 | WorkspaceService.get_diff() |
| 82.2 | 9 | 3.3% | app/api/services/admin_workbench_service.py:451 | AdminWorkbenchService.get_prompt_fragment() |
| 72.9 | 21 | 51.0% | app/api/services/workspace_service.py:640 | WorkspaceService._run_tier1_validation() |
| 71.4 | 9 | 8.3% | app/api/services/project_service.py:175 | ProjectService.get_project_full() |
| 58.3 | 8 | 7.7% | app/api/services/preview_service.py:517 | PreviewService._diff_metadata() |
| 54.7 | 8 | 10.0% | app/api/services/project_service.py:41 | ProjectService.list_projects() |
| 52.6 | 7 | 2.4% | app/api/services/role_prompt_service.py:85 | RolePromptService.build_prompt() |
| 49.3 | 7 | 4.8% | app/api/services/workspace_service.py:1168 | WorkspaceService.delete_orchestration_workflow() |
| 48.3 | 7 | 5.6% | app/api/services/preview_service.py:477 | PreviewService._diff_schemas() |
| 47.6 | 9 | 21.9% | app/api/services/config_validator.py:467 | ConfigValidator.validate_schema_compatibility() |
| 39.8 | 6 | 2.0% | app/api/services/production_service.py:88 | get_document_type_dependencies() |
| 37.3 | 6 | 4.5% | app/api/services/transcript_service.py:87 | get_execution_transcript() |
| 37.1 | 6 | 4.8% | app/api/services/workspace_service.py:1079 | WorkspaceService.create_orchestration_workflow() |
| 37.1 | 6 | 4.8% | app/api/services/production_service.py:30 | _get_workflow_plan() |
| 36.6 | 6 | 5.3% | app/api/services/project_service.py:312 | ProjectService.create_project() |
| 33.7 | 6 | 8.3% | app/api/services/project_service.py:230 | ProjectService.get_architecture() |
| 31.7 | 11 | 44.4% | app/api/services/project_creation_service.py:181 | extract_intake_document_from_state() |
| 31.3 | 6 | 11.1% | app/api/services/search_service.py:97 | SearchService._search_documents() |
| 31.3 | 6 | 11.1% | app/api/services/project_service.py:137 | ProjectService.get_project_with_work_packages() |

### API v1 Routers (10 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 662.6 | 26 | 2.0% | app/api/v1/routers/projects.py:718 | get_document_render_model() |
| 140.3 | 12 | 3.8% | app/api/v1/routers/production.py:205 | start_production() |
| 99.2 | 12 | 15.4% | app/api/v1/routers/projects.py:1283 | list_work_packages() |
| 95.0 | 10 | 5.3% | app/api/v1/routers/interrupts.py:114 | resolve_interrupt() |
| 91.3 | 10 | 6.7% | app/api/v1/routers/projects.py:540 | get_project_tree() |
| 81.9 | 9 | 3.4% | app/api/v1/routers/intake.py:402 | _intake_event_generator() |
| 71.4 | 9 | 8.3% | app/api/v1/routers/projects.py:362 | update_project() |
| 65.9 | 9 | 11.1% | app/api/v1/routers/projects.py:652 | get_project_document() |
| 37.3 | 6 | 4.5% | app/api/v1/routers/production.py:108 | _event_generator() |
| 35.4 | 7 | 16.7% | app/api/v1/routers/projects.py:1355 | list_work_statements() |

### Mech Handlers (11 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 100.9 | 10 | 3.1% | app/api/services/mech_handlers/router.py:169 | RouterHandler.execute() |
| 100.0 | 10 | 3.4% | app/api/services/mech_handlers/merger.py:140 | MergerHandler.execute() |
| 81.6 | 9 | 3.6% | app/api/services/mech_handlers/spawner.py:135 | SpawnerHandler.execute() |
| 80.7 | 9 | 4.0% | app/api/services/mech_handlers/validator.py:156 | ValidatorHandler.execute() |
| 77.9 | 9 | 5.3% | app/api/services/mech_handlers/merger.py:199 | MergerHandler.validate_config() |
| 50.4 | 7 | 4.0% | app/api/services/mech_handlers/clarification_merger.py:33 | ClarificationMergerHandler.execute() |
| 47.4 | 7 | 6.2% | app/api/services/mech_handlers/extractor.py:159 | ExtractorHandler.validate_config() |
| 36.6 | 6 | 5.3% | app/api/services/mech_handlers/exclusion_filter.py:208 | ExclusionFilterHandler.execute() |
| 36.6 | 6 | 5.3% | app/api/services/mech_handlers/invariant_pinner.py:160 | InvariantPinnerHandler.execute() |
| 36.0 | 6 | 5.9% | app/api/services/mech_handlers/extractor.py:116 | ExtractorHandler.execute() |
| 34.8 | 6 | 7.1% | app/api/services/mech_handlers/router.py:263 | RouterHandler.validate_config() |

### Document Handlers (7 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 81.3 | 9 | 3.7% | app/domain/handlers/architecture_spec_handler.py:177 | ArchitectureSpecHandler.render() |
| 81.3 | 9 | 3.7% | app/domain/handlers/architecture_spec_handler.py:349 | ArchitectureSpecHandler._render_components() |
| 77.9 | 9 | 5.3% | app/domain/handlers/architecture_spec_handler.py:112 | ArchitectureSpecHandler.validate() |
| 63.3 | 8 | 4.8% | app/domain/handlers/architecture_spec_handler.py:234 | ArchitectureSpecHandler.render_summary() |
| 54.7 | 8 | 10.0% | app/domain/handlers/base_handler.py:280 | BaseDocumentHandler.extract_title() |
| 50.4 | 7 | 4.0% | app/domain/handlers/architecture_spec_handler.py:450 | ArchitectureSpecHandler._render_interfaces() |
| 35.7 | 6 | 6.2% | app/domain/handlers/architecture_spec_handler.py:406 | ArchitectureSpecHandler._render_data_models() |

### Web Routes (10 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 500.8 | 23 | 3.3% | app/web/routes/public/document_routes.py:264 | get_document() |
| 89.4 | 10 | 7.4% | app/web/routes/public/project_routes.py:405 | soft_delete_project() |
| 58.3 | 8 | 7.7% | app/web/routes/public/intake_workflow_routes.py:440 | get_intake_status() |
| 44.3 | 7 | 8.7% | app/web/routes/public/document_routes.py:438 | build_document() |
| 43.8 | 7 | 9.1% | app/web/routes/public/project_routes.py:290 | archive_project() |
| 42.7 | 7 | 10.0% | app/web/routes/public/project_routes.py:499 | get_project() |
| 38.1 | 6 | 3.7% | app/web/routes/public/view_routes.py:94 | FragmentRenderer._resolve_fragment() |
| 34.0 | 6 | 8.0% | app/web/routes/public/workflow_build_routes.py:210 | submit_pgc_answers() |
| 33.7 | 6 | 8.3% | app/web/routes/public/project_routes.py:560 | update_project() |
| 31.8 | 6 | 10.5% | app/web/routes/admin/composer_routes.py:175 | preview_render() |

### Domain Services (4 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 126.1 | 11 | 1.6% | app/domain/services/document_builder.py:419 | DocumentBuilder.build_stream() |
| 83.1 | 9 | 2.9% | app/domain/services/document_builder.py:358 | DocumentBuilder.build() |
| 59.2 | 8 | 7.1% | app/domain/services/document_builder.py:280 | DocumentBuilder._complete_llm_logging() |
| 47.4 | 7 | 6.2% | app/domain/services/document_builder.py:239 | DocumentBuilder._start_llm_logging() |

### API v1 Services (4 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 190.4 | 14 | 3.4% | app/api/v1/services/llm_execution_service.py:419 | LLMExecutionService._context_to_info() |
| 79.0 | 9 | 4.8% | app/api/v1/services/llm_execution_service.py:183 | LLMExecutionService.execute_step() |
| 58.3 | 8 | 7.7% | app/api/v1/services/llm_execution_service.py:313 | LLMExecutionService.list_executions() |
| 34.8 | 6 | 7.1% | app/api/v1/services/llm_execution_service.py:252 | LLMExecutionService.submit_clarification() |

### LLM Layer (1 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 145.7 | 12 | 2.4% | app/llm/providers/anthropic.py:58 | AnthropicProvider.complete() |

### Auth (3 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 119.3 | 11 | 3.6% | app/auth/routes.py:157 | callback() |
| 79.0 | 9 | 4.8% | app/auth/routes.py:33 | validate_origin() |
| 45.5 | 7 | 7.7% | app/auth/oidc_config.py:150 | OIDCConfig.normalize_claims() |

### Core/Observability (1 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 47.4 | 7 | 6.2% | app/core/dependencies/auth.py:45 | require_api_key() |

### Other (16 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 309.6 | 18 | 3.4% | app/api/routers/admin.py:143 | compare_runs() |
| 192.2 | 14 | 3.1% | app/api/routers/accounts.py:111 | link_callback() |
| 163.9 | 13 | 3.7% | app/api/repositories/role_prompt_repository.py:94 | RolePromptRepository.create() |
| 124.1 | 11 | 2.2% | app/tasks/document_builder.py:151 | run_workflow_build() |
| 61.2 | 10 | 20.0% | app/api/routers/documents.py:348 | get_document() |
| 50.9 | 7 | 3.6% | app/config/package_loader.py:653 | PackageLoader.assemble_qa_prompt() |
| 47.9 | 7 | 5.9% | app/tasks/registry.py:58 | update_task() |
| 43.8 | 7 | 9.1% | app/api/routers/admin.py:474 | list_workflows() |
| 42.7 | 7 | 10.0% | app/domain/registry/loader.py:210 | get_buildable_documents() |
| 38.7 | 6 | 3.1% | app/tasks/document_builder.py:30 | run_document_build() |
| 37.7 | 6 | 4.2% | app/api/routers/admin.py:235 | replay_llm_run() |
| 37.7 | 16 | 56.1% | app/api/middleware/secret_ingress.py:41 | SecretIngressMiddleware.dispatch() |
| 36.6 | 6 | 5.3% | app/api/repositories/role_prompt_repository.py:177 | RolePromptRepository.update() |
| 34.8 | 6 | 7.1% | app/config/package_loader.py:579 | PackageLoader._resolve_template_ref() |
| 34.8 | 6 | 7.1% | app/domain/repositories/postgres_ws_metrics_repository.py:81 | PostgresWSMetricsRepository.list_executions() |
| 30.1 | 10 | 41.4% | app/domain/prompt/assembler.py:389 | PromptAssembler._load_include() |

---

## Subsystem Risk Summary

Subsystems ordered by total CRAP debt (sum of all critical CRAP scores):

| Subsystem | Critical Count | Total CRAP Debt | Worst Single |
|-----------|---------------|----------------|-------------|
| API Services | 29 | 3097.3 | 626.9 |
| Workflow Engine | 29 | 1920.1 | 231.4 |
| API v1 Routers | 10 | 1380.3 | 662.6 |
| Other | 16 | 1286.7 | 309.6 |
| Workflow Nodes | 15 | 1019.7 | 165.7 |
| Web Routes | 10 | 916.9 | 500.8 |
| Mech Handlers | 11 | 682.9 | 100.9 |
| Document Handlers | 7 | 444.6 | 81.3 |
| API v1 Services | 4 | 362.5 | 190.4 |
| Domain Services | 4 | 315.8 | 126.1 |
| Auth | 3 | 243.8 | 119.3 |
| LLM Layer | 1 | 145.7 | 145.7 |
| Core/Observability | 1 | 47.4 | 47.4 |

---

## Recommended Next Actions

1. **get_document_render_model()** (CRAP 662.6) -- Still the single worst function in
   API v1 Routers. Was not a WP-CRAP-001 target. Needs decomposition into smaller handlers.
2. **get_production_tracks()** (CRAP 626.9) -- Partially improved by WS-CRAP-003 extraction
   but orchestrator still has CC=25. Further thinning needed.
3. **get_document() in document_routes** (CRAP 500.8) -- Absorbed complexity from removed
   helpers. Needs re-examination.
4. **Mech Handlers** -- 11 critical functions, all with similar patterns (CC 6-10, coverage
   3-7%). Good candidate for a focused WS since the pattern is uniform.
5. **ArchitectureSpecHandler** -- 6 of 7 remaining Document Handler criticals. A single
   focused WS could address the entire class.

---

_Generated: 2026-02-27. Source: /tmp/crap_results.json. Baseline: docs/audits/2026-02-26-crap-scores.md_
