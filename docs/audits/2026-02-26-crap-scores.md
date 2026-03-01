# CRAP Score Analysis -- 2026-02-26

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
| Total functions analyzed | 2175 |
| Critical (CRAP > 30) | 262 (12.0%) |
| Smelly (15-30) | 205 (9.4%) |
| Acceptable (5-15) | 420 (19.3%) |
| Clean (<= 5) | 1288 (59.2%) |
| Median CRAP | 3.7 |

---

## Critical Functions by Subsystem

| Subsystem | Critical Count | Worst CRAP | Worst Function |
|-----------|---------------|------------|----------------|
| API v1 Routers | 21 | 2532.9 | get_document_render_model() |
| Workflow Engine | 79 | 2190.4 | PlanExecutor._handle_result() |
| API Services | 35 | 1020.7 | get_production_tracks() |
| Document Handlers | 31 | 506.0 | InvariantPinnerHandler.execute() |
| Core/Observability | 4 | 342.0 | JSONFormatter.format() |
| Web Routes | 19 | 333.0 | _build_completion_context() |
| Other | 25 | 309.6 | compare_runs() |
| LLM Layer | 9 | 238.7 | OutputValidator._validate_type() |
| Domain Services | 23 | 229.8 | DocumentBuilder.build_stream() |
| Execution | 5 | 160.0 | WorkflowDefinition.validate() |
| Auth | 6 | 119.3 | callback() |
| Persistence | 5 | 95.7 | InMemoryDocumentRepository.save() |

---

### API v1 Routers (21 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 2532.9 | 51 | 1.6% | app/api/v1/routers/projects.py:719 | get_document_render_model() |
| 429.7 | 21 | 2.5% | app/api/v1/routers/projects.py:1089 | _repair_truncated_json() |
| 288.1 | 18 | 5.9% | app/api/v1/routers/projects.py:1237 | _resolve_answer_label() |
| 260.5 | 17 | 5.6% | app/api/v1/routers/projects.py:1171 | _build_pgc_from_context_state() |
| 185.0 | 14 | 4.4% | app/api/v1/routers/interrupts.py:114 | resolve_interrupt() |
| 140.3 | 12 | 3.8% | app/api/v1/routers/production.py:205 | start_production() |
| 112.9 | 11 | 5.6% | app/api/v1/routers/intake.py:140 | _extract_messages() |
| 99.2 | 12 | 15.4% | app/api/v1/routers/projects.py:1481 | list_work_packages() |
| 95.0 | 10 | 5.3% | app/api/v1/routers/intake.py:177 | _build_state_response() |
| 91.3 | 10 | 6.7% | app/api/v1/routers/projects.py:541 | get_project_tree() |
| 81.9 | 9 | 3.4% | app/api/v1/routers/intake.py:438 | _intake_event_generator() |
| 71.4 | 9 | 8.3% | app/api/v1/routers/projects.py:363 | update_project() |
| 67.0 | 9 | 10.5% | app/api/v1/routers/document_workflows.py:395 | submit_user_input() |
| 65.9 | 9 | 11.1% | app/api/v1/routers/projects.py:653 | get_project_document() |
| 59.2 | 8 | 7.1% | app/api/v1/routers/executions.py:65 | _state_to_response() |
| 44.3 | 7 | 8.7% | app/api/v1/routers/document_workflows.py:235 | start_execution() |
| 43.1 | 8 | 18.2% | app/api/v1/routers/workflows.py:59 | get_workflow() |
| 41.4 | 7 | 11.1% | app/api/v1/routers/workflows.py:134 | get_step_schema() |
| 37.3 | 6 | 4.5% | app/api/v1/routers/production.py:108 | _event_generator() |
| 35.4 | 7 | 16.7% | app/api/v1/routers/projects.py:1553 | list_work_statements() |
| 34.0 | 6 | 8.0% | app/api/v1/routers/websocket.py:21 | execution_websocket() |

### Workflow Engine (79 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 2190.4 | 47 | 1.0% | app/domain/workflow/plan_executor.py:824 | PlanExecutor._handle_result() |
| 1580.7 | 40 | 1.2% | app/domain/workflow/nodes/qa.py:86 | QANodeExecutor.execute() |
| 720.7 | 27 | 1.6% | app/domain/workflow/plan_executor.py:1518 | PlanExecutor._filter_excluded_topics() |
| 714.0 | 27 | 2.0% | app/domain/workflow/nodes/qa.py:844 | QANodeExecutor._parse_qa_response() |
| 528.0 | 23 | 1.5% | app/domain/workflow/plan_executor.py:287 | PlanExecutor.execute_step() |
| 312.5 | 19 | 6.7% | app/domain/workflow/pg_state_persistence.py:185 | PgStatePersistence._row_to_state() |
| 256.3 | 16 | 2.1% | app/domain/workflow/plan_executor.py:1399 | PlanExecutor._pin_invariants_to_known_constraints() |
| 228.6 | 15 | 1.7% | app/domain/workflow/plan_executor.py:1813 | PlanExecutor._persist_produced_documents() |
| 193.2 | 14 | 2.9% | app/domain/workflow/nodes/qa.py:437 | QANodeExecutor._run_semantic_qa() |
| 171.0 | 13 | 2.2% | app/domain/workflow/nodes/gate.py:377 | GateNodeExecutor._execute_pgc_gate() |
| 165.7 | 13 | 3.3% | app/domain/workflow/nodes/gate.py:324 | GateNodeExecutor._resolve_urn() |
| 165.1 | 13 | 3.4% | app/domain/workflow/plan_executor.py:1082 | PlanExecutor._extract_qa_feedback() |
| 145.2 | 12 | 2.6% | app/domain/workflow/project_orchestrator.py:419 | ProjectOrchestrator._run_active_executions() |
| 138.7 | 12 | 4.2% | app/domain/workflow/nodes/qa.py:330 | QANodeExecutor._run_code_based_validation() |
| 123.4 | 11 | 2.4% | app/domain/workflow/pg_state_persistence.py:30 | PgStatePersistence.save() |
| 114.7 | 11 | 5.0% | app/domain/workflow/plan_executor.py:2129 | PlanExecutor._emit_stations_declared() |
| 102.3 | 10 | 2.6% | app/domain/workflow/prompt_loader.py:174 | PromptLoader.load_task() |
| 100.9 | 10 | 3.1% | app/domain/workflow/step_executor.py:158 | StepExecutor._execute_with_remediation() |
| 98.5 | 10 | 4.0% | app/domain/workflow/nodes/intake_gate_profile.py:316 | IntakeGateProfileExecutor._extract_classification_fallback() |
| 97.0 | 10 | 4.5% | app/domain/workflow/plan_executor.py:587 | PlanExecutor._build_context() |
| 96.4 | 10 | 4.8% | app/domain/workflow/workflow_executor.py:189 | WorkflowExecutor._execute_production_step() |
| 93.4 | 10 | 5.9% | app/domain/workflow/plan_executor.py:1201 | PlanExecutor._persist_conversation() |
| 81.3 | 9 | 3.7% | app/domain/workflow/validator.py:59 | WorkflowValidator.validate() |
| 81.0 | 9 | 3.8% | app/domain/workflow/workflow_executor.py:130 | WorkflowExecutor.process_clarification() |
| 81.0 | 9 | 3.8% | app/domain/workflow/nodes/task.py:363 | TaskNodeExecutor._format_pgc_questions() |
| 80.7 | 9 | 4.0% | app/domain/workflow/plan_executor.py:195 | PlanExecutor.start_execution() |
| 80.3 | 9 | 4.2% | app/domain/workflow/nodes/intake_gate_profile.py:191 | IntakeGateProfileExecutor._execute_confirmation_phase() |
| 79.0 | 9 | 4.8% | app/domain/workflow/edge_router.py:206 | EdgeRouter._compare() |
| 78.4 | 9 | 5.0% | app/domain/workflow/project_orchestrator.py:547 | ProjectOrchestrator._calculate_final_status() |
| 75.7 | 9 | 6.2% | app/domain/workflow/plan_executor.py:1774 | PlanExecutor._build_invariant_statement() |
| 75.7 | 9 | 6.2% | app/domain/workflow/validator.py:133 | WorkflowValidator._load_schema() |
| 74.9 | 9 | 6.7% | app/domain/workflow/gates/qa.py:177 | QAGate._validate_against_schema() |
| 69.9 | 9 | 9.1% | app/domain/workflow/plan_executor.py:1164 | PlanExecutor._find_generating_node() |
| 66.7 | 8 | 2.9% | app/domain/workflow/plan_executor.py:695 | PlanExecutor._load_pgc_answers_for_qa() |
| 65.9 | 9 | 11.1% | app/domain/workflow/project_orchestrator.py:528 | ProjectOrchestrator._update_blocked_states() |
| 65.1 | 8 | 3.7% | app/domain/workflow/prompt_loader.py:118 | PromptLoader.load_role() |
| 64.9 | 8 | 3.8% | app/domain/workflow/project_orchestrator.py:89 | ProjectOrchestrator.run_full_line() |
| 64.6 | 8 | 4.0% | app/domain/workflow/workflow_executor.py:237 | WorkflowExecutor._execute_iteration_step() |
| 64.6 | 8 | 4.0% | app/domain/workflow/step_executor.py:269 | StepExecutor._build_user_prompt_with_answers() |
| 64.6 | 8 | 4.0% | app/domain/workflow/nodes/task.py:313 | TaskNodeExecutor._render_qa_feedback() |
| 64.0 | 8 | 4.3% | app/domain/workflow/registry.py:78 | WorkflowRegistry._load_all() |
| 61.9 | 8 | 5.6% | app/domain/workflow/project_orchestrator.py:494 | ProjectOrchestrator._wait_for_completions() |
| 61.9 | 8 | 5.6% | app/domain/workflow/nodes/mock_executors.py:135 | MockGateExecutor.execute() |
| 61.9 | 8 | 5.6% | app/domain/workflow/gates/clarification.py:212 | ClarificationGate.validate_questions_only() |
| 56.1 | 8 | 9.1% | app/domain/workflow/project_orchestrator.py:278 | ProjectOrchestrator._find_ready_documents() |
| 52.9 | 8 | 11.1% | app/domain/workflow/remediation.py:155 | RemediationLoop.get_error_summary() |
| 50.4 | 7 | 4.0% | app/domain/workflow/outcome_recorder.py:49 | OutcomeRecorder.record_outcome() |
| 49.9 | 7 | 4.3% | app/domain/workflow/plan_executor.py:1632 | PlanExecutor._promote_pgc_invariants_to_document() |
| 48.7 | 7 | 5.3% | app/domain/workflow/gates/qa.py:54 | QAGate.check() |
| 48.3 | 7 | 5.6% | app/domain/workflow/plan_executor.py:655 | PlanExecutor._get_pgc_questions_for_merge() |
| 47.9 | 7 | 5.9% | app/domain/workflow/gates/clarification.py:142 | ClarificationGate._extract_json() |
| 47.4 | 7 | 6.2% | app/domain/workflow/outcome_recorder.py:188 | OutcomeRecorder._build_routing_rationale() |
| 46.8 | 7 | 6.7% | app/domain/workflow/nodes/gate.py:214 | GateNodeExecutor._execute_gate_profile() |
| 46.2 | 7 | 7.1% | app/domain/workflow/iteration.py:44 | IterationHandler.expand() |
| 46.2 | 7 | 7.1% | app/domain/workflow/interrupt_registry.py:126 | _build_interrupt_payload() |
| 45.5 | 7 | 7.7% | app/domain/workflow/input_resolver.py:237 | InputResolver._check_reference_rules() |
| 44.7 | 7 | 8.3% | app/domain/workflow/plan_executor.py:1260 | PlanExecutor._sync_thread_status() |
| 44.7 | 7 | 8.3% | app/domain/workflow/interrupt_registry.py:94 | _determine_interrupt_type() |
| 44.7 | 7 | 8.3% | app/domain/workflow/validator.py:204 | WorkflowValidator._validate_scope_references() |
| 43.8 | 7 | 9.1% | app/domain/workflow/gates/qa.py:114 | QAGate._check_structure() |
| 42.7 | 7 | 10.0% | app/domain/workflow/plan_models.py:346 | WorkflowPlan.get_node_station() |
| 42.5 | 41 | 90.4% | app/domain/workflow/validation/rules.py:103 | check_promotion_validity() |
| 39.8 | 7 | 12.5% | app/domain/workflow/nodes/intake_gate.py:223 | IntakeGateExecutor._extract_category() |
| 38.6 | 6 | 3.2% | app/domain/workflow/remediation.py:73 | RemediationLoop.build_remediation_prompt() |
| 37.5 | 6 | 4.3% | app/domain/workflow/nodes/intake_gate.py:85 | IntakeGateExecutor.execute() |
| 37.1 | 35 | 88.0% | app/domain/workflow/plan_executor.py:1955 | PlanExecutor._spawn_child_documents() |
| 36.3 | 6 | 5.6% | app/domain/workflow/workflow_executor.py:74 | WorkflowExecutor.run_until_pause() |
| 36.3 | 6 | 5.6% | app/domain/workflow/plan_executor.py:533 | PlanExecutor.handle_escalation_choice() |
| 36.3 | 6 | 5.6% | app/domain/workflow/project_orchestrator.py:233 | ProjectOrchestrator._run_orchestration_loop() |
| 36.1 | 14 | 51.7% | app/domain/workflow/nodes/task.py:172 | TaskNodeExecutor._build_messages() |
| 35.7 | 6 | 6.2% | app/domain/workflow/plan_executor.py:446 | PlanExecutor.run_to_completion_or_pause() |
| 35.4 | 10 | 36.7% | app/domain/workflow/nodes/intake_gate_profile.py:92 | IntakeGateProfileExecutor._execute_initial_phase() |
| 35.3 | 6 | 6.7% | app/domain/workflow/input_resolver.py:173 | InputResolver._resolve_single() |
| 35.3 | 6 | 6.7% | app/domain/workflow/gates/qa.py:154 | QAGate._get_schema_for_doc_type() |
| 34.8 | 6 | 7.1% | app/domain/workflow/nodes/intake_gate_profile.py:371 | IntakeGateProfileExecutor._execute_extraction() |
| 34.3 | 6 | 7.7% | app/domain/workflow/plan_executor.py:1702 | PlanExecutor._embed_pgc_clarifications() |
| 34.3 | 6 | 7.7% | app/domain/workflow/input_resolver.py:128 | InputResolver.resolve() |
| 32.9 | 18 | 64.2% | app/domain/workflow/nodes/llm_executors.py:107 | LoggingLLMService.complete() |
| 31.8 | 6 | 10.5% | app/domain/workflow/step_state.py:227 | StepState.from_dict() |

### API Services (35 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 1020.7 | 32 | 1.2% | app/api/services/production_service.py:264 | get_production_tracks() |
| 660.6 | 26 | 2.1% | app/api/services/admin_workbench_service.py:346 | AdminWorkbenchService.list_prompt_fragments() |
| 317.7 | 18 | 2.6% | app/api/services/mechanical_ops_service.py:200 | MechanicalOpsService.list_operations() |
| 291.3 | 17 | 1.7% | app/api/services/qa_coverage_service.py:18 | get_qa_coverage() |
| 250.7 | 16 | 2.9% | app/api/services/admin_workbench_service.py:813 | AdminWorkbenchService.list_orchestration_workflows() |
| 249.4 | 16 | 3.0% | app/api/services/dashboard_service.py:40 | get_dashboard_summary() |
| 247.2 | 16 | 3.3% | app/api/services/production_service.py:62 | _build_station_sequence_from_workflow() |
| 197.5 | 14 | 2.2% | app/api/services/cost_service.py:21 | get_cost_dashboard_data() |
| 197.2 | 14 | 2.2% | app/api/services/transcript_service.py:86 | get_execution_transcript() |
| 192.2 | 14 | 3.1% | app/api/services/admin_workbench_service.py:742 | AdminWorkbenchService.list_workflows() |
| 169.9 | 13 | 2.4% | app/api/services/workspace_service.py:912 | WorkspaceService.get_preview() |
| 165.7 | 13 | 3.3% | app/api/services/production_service.py:483 | get_production_status() |
| 136.4 | 12 | 4.8% | app/api/services/mechanical_ops_service.py:315 | MechanicalOpsService.get_operation() |
| 121.3 | 20 | 36.7% | app/api/services/workspace_service.py:242 | WorkspaceService._artifact_id_to_path() |
| 112.9 | 11 | 5.6% | app/api/services/project_creation_service.py:181 | extract_intake_document_from_state() |
| 107.9 | 11 | 7.1% | app/api/services/preview_service.py:442 | PreviewService._diff_prompts() |
| 107.9 | 11 | 7.1% | app/api/services/document_status_service.py:341 | DocumentStatusService._derive_subtitle() |
| 98.5 | 10 | 4.0% | app/api/services/workspace_service.py:849 | WorkspaceService.get_diff() |
| 82.2 | 9 | 3.3% | app/api/services/admin_workbench_service.py:498 | AdminWorkbenchService.get_prompt_fragment() |
| 72.9 | 21 | 51.0% | app/api/services/workspace_service.py:640 | WorkspaceService._run_tier1_validation() |
| 71.4 | 9 | 8.3% | app/api/services/project_service.py:175 | ProjectService.get_project_full() |
| 58.3 | 8 | 7.7% | app/api/services/preview_service.py:517 | PreviewService._diff_metadata() |
| 54.7 | 8 | 10.0% | app/api/services/project_service.py:41 | ProjectService.list_projects() |
| 52.6 | 7 | 2.4% | app/api/services/role_prompt_service.py:85 | RolePromptService.build_prompt() |
| 49.3 | 7 | 4.8% | app/api/services/workspace_service.py:1168 | WorkspaceService.delete_orchestration_workflow() |
| 48.3 | 7 | 5.6% | app/api/services/preview_service.py:477 | PreviewService._diff_schemas() |
| 47.6 | 9 | 21.9% | app/api/services/config_validator.py:467 | ConfigValidator.validate_schema_compatibility() |
| 43.8 | 7 | 9.1% | app/api/services/document_status_service.py:274 | DocumentStatusService._derive_readiness() |
| 39.8 | 6 | 2.0% | app/api/services/production_service.py:147 | get_document_type_dependencies() |
| 37.1 | 6 | 4.8% | app/api/services/workspace_service.py:1079 | WorkspaceService.create_orchestration_workflow() |
| 37.1 | 6 | 4.8% | app/api/services/production_service.py:30 | _get_workflow_plan() |
| 36.6 | 6 | 5.3% | app/api/services/project_service.py:312 | ProjectService.create_project() |
| 33.7 | 6 | 8.3% | app/api/services/project_service.py:230 | ProjectService.get_architecture() |
| 31.3 | 6 | 11.1% | app/api/services/search_service.py:97 | SearchService._search_documents() |
| 31.3 | 6 | 11.1% | app/api/services/project_service.py:137 | ProjectService.get_project_with_work_packages() |

### Document Handlers (31 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 506.0 | 22 | 0.0% | app/api/services/mech_handlers/invariant_pinner.py:34 | InvariantPinnerHandler.execute() |
| 356.5 | 19 | 2.2% | app/domain/handlers/project_discovery_handler.py:129 | ProjectDiscoveryHandler.render() |
| 272.0 | 16 | 0.0% | app/api/services/mech_handlers/exclusion_filter.py:35 | ExclusionFilterHandler.execute() |
| 210.0 | 14 | 0.0% | app/api/services/mech_handlers/spawner.py:51 | SpawnerHandler.execute() |
| 192.7 | 14 | 3.0% | app/domain/handlers/pipeline_run_handler.py:30 | PipelineRunHandler.render() |
| 185.5 | 14 | 4.3% | app/domain/handlers/architecture_spec_handler.py:80 | ArchitectureSpecHandler.transform() |
| 156.0 | 12 | 0.0% | app/api/services/mech_handlers/merger.py:51 | MergerHandler.execute() |
| 132.0 | 11 | 0.0% | app/api/services/mech_handlers/validator.py:122 | ValidatorHandler._validate_field() |
| 110.0 | 10 | 0.0% | app/api/services/mech_handlers/router.py:52 | RouterHandler.execute() |
| 110.0 | 10 | 0.0% | app/api/services/mech_handlers/extractor.py:48 | ExtractorHandler.execute() |
| 92.4 | 10 | 6.2% | app/domain/handlers/project_discovery_handler.py:37 | ProjectDiscoveryHandler.validate() |
| 90.0 | 9 | 0.0% | app/api/services/mech_handlers/merger.py:197 | MergerHandler.validate_config() |
| 90.0 | 9 | 0.0% | app/api/services/mech_handlers/router.py:164 | RouterHandler._extract_classification() |
| 90.0 | 9 | 0.0% | app/api/services/mech_handlers/validator.py:60 | ValidatorHandler.execute() |
| 81.3 | 9 | 3.7% | app/domain/handlers/architecture_spec_handler.py:146 | ArchitectureSpecHandler.render() |
| 81.3 | 9 | 3.7% | app/domain/handlers/architecture_spec_handler.py:318 | ArchitectureSpecHandler._render_components() |
| 77.9 | 9 | 5.3% | app/domain/handlers/architecture_spec_handler.py:38 | ArchitectureSpecHandler.validate() |
| 72.0 | 8 | 0.0% | app/api/services/mech_handlers/exclusion_filter.py:140 | ExclusionFilterHandler._filter_items() |
| 72.0 | 8 | 0.0% | app/api/services/mech_handlers/exclusion_filter.py:185 | ExclusionFilterHandler._filter_decision_points() |
| 63.3 | 8 | 4.8% | app/domain/handlers/architecture_spec_handler.py:203 | ArchitectureSpecHandler.render_summary() |
| 56.0 | 7 | 0.0% | app/api/services/mech_handlers/merger.py:150 | MergerHandler._merge_values() |
| 56.0 | 7 | 0.0% | app/api/services/mech_handlers/router.py:194 | RouterHandler._score_route() |
| 56.0 | 7 | 0.0% | app/api/services/mech_handlers/router.py:241 | RouterHandler._determine_confidence() |
| 56.0 | 7 | 0.0% | app/api/services/mech_handlers/extractor.py:150 | ExtractorHandler.validate_config() |
| 56.0 | 7 | 0.0% | app/api/services/mech_handlers/clarification_merger.py:33 | ClarificationMergerHandler.execute() |
| 54.7 | 8 | 10.0% | app/domain/handlers/base_handler.py:280 | BaseDocumentHandler.extract_title() |
| 50.4 | 7 | 4.0% | app/domain/handlers/architecture_spec_handler.py:419 | ArchitectureSpecHandler._render_interfaces() |
| 42.0 | 6 | 0.0% | app/api/services/mech_handlers/router.py:281 | RouterHandler.validate_config() |
| 36.0 | 6 | 5.9% | app/domain/handlers/project_discovery_handler.py:365 | ProjectDiscoveryHandler._render_decision_points() |
| 35.7 | 6 | 6.2% | app/domain/handlers/architecture_spec_handler.py:375 | ArchitectureSpecHandler._render_data_models() |
| 33.7 | 6 | 8.3% | app/domain/handlers/project_discovery_handler.py:242 | ProjectDiscoveryHandler.render_summary() |

### Core/Observability (4 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 342.0 | 18 | 0.0% | app/observability/logging.py:25 | JSONFormatter.format() |
| 67.0 | 9 | 10.5% | app/core/environment.py:118 | Environment.validate() |
| 47.4 | 7 | 6.2% | app/core/dependencies/auth.py:45 | require_api_key() |
| 42.0 | 6 | 0.0% | app/observability/health.py:107 | HealthChecker.check_all() |

### Web Routes (19 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 333.0 | 19 | 4.5% | app/web/routes/public/intake_workflow_routes.py:708 | _build_completion_context() |
| 237.9 | 16 | 4.7% | app/web/routes/public/document_routes.py:253 | get_document() |
| 218.9 | 15 | 3.2% | app/web/routes/public/intake_workflow_routes.py:491 | _build_template_context() |
| 143.3 | 12 | 3.0% | app/web/routes/public/workflow_build_routes.py:172 | _render_workflow_state() |
| 82.9 | 9 | 3.0% | app/web/routes/public/view_routes.py:89 | FragmentRenderer._resolve_fragment() |
| 73.9 | 9 | 7.1% | app/web/routes/public/project_routes.py:213 | get_project_documents_status() |
| 72.7 | 9 | 7.7% | app/web/routes/public/project_routes.py:424 | soft_delete_project() |
| 58.3 | 8 | 7.7% | app/web/routes/public/intake_workflow_routes.py:433 | get_intake_status() |
| 49.9 | 7 | 4.3% | app/web/routes/public/workflow_build_routes.py:101 | _parse_pgc_form() |
| 46.5 | 7 | 6.9% | app/web/routes/public/intake_workflow_routes.py:80 | start_intake_workflow() |
| 45.5 | 7 | 7.7% | app/web/routes/public/intake_workflow_routes.py:640 | _build_message_context() |
| 44.3 | 7 | 8.7% | app/web/routes/public/document_routes.py:372 | build_document() |
| 43.8 | 7 | 9.1% | app/web/routes/public/project_routes.py:309 | archive_project() |
| 42.7 | 7 | 10.0% | app/web/routes/public/project_routes.py:513 | get_project() |
| 34.6 | 6 | 7.4% | app/web/routes/public/intake_workflow_routes.py:207 | submit_intake_message() |
| 34.0 | 6 | 8.0% | app/web/routes/public/workflow_build_routes.py:284 | submit_pgc_answers() |
| 33.7 | 6 | 8.3% | app/web/routes/public/project_routes.py:574 | update_project() |
| 31.8 | 6 | 10.5% | app/web/routes/admin/composer_routes.py:175 | preview_render() |
| 30.7 | 6 | 11.8% | app/web/routes/public/workflow_build_routes.py:237 | start_workflow_build() |

### Other (25 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 309.6 | 18 | 3.4% | app/api/routers/admin.py:143 | compare_runs() |
| 192.2 | 14 | 3.1% | app/api/routers/accounts.py:111 | link_callback() |
| 190.4 | 14 | 3.4% | app/api/v1/services/llm_execution_service.py:419 | LLMExecutionService._context_to_info() |
| 163.9 | 13 | 3.7% | app/api/repositories/role_prompt_repository.py:94 | RolePromptRepository.create() |
| 124.1 | 11 | 2.2% | app/tasks/document_builder.py:151 | run_workflow_build() |
| 79.0 | 9 | 4.8% | app/api/v1/services/llm_execution_service.py:183 | LLMExecutionService.execute_step() |
| 72.0 | 8 | 0.0% | app/health.py:66 | HealthChecker.check_health() |
| 61.2 | 10 | 20.0% | app/api/routers/documents.py:348 | get_document() |
| 58.3 | 8 | 7.7% | app/api/v1/services/llm_execution_service.py:313 | LLMExecutionService.list_executions() |
| 56.1 | 8 | 9.1% | app/api/v1/services/execution_service.py:101 | ExecutionService.list_executions() |
| 55.6 | 16 | 46.3% | app/api/middleware/secret_ingress.py:41 | SecretIngressMiddleware.dispatch() |
| 50.9 | 7 | 3.6% | app/config/package_loader.py:653 | PackageLoader.assemble_qa_prompt() |
| 48.3 | 7 | 5.6% | app/api/v1/services/execution_service.py:153 | ExecutionService.submit_acceptance() |
| 47.9 | 7 | 5.9% | app/tasks/registry.py:58 | update_task() |
| 43.8 | 7 | 9.1% | app/api/routers/admin.py:474 | list_workflows() |
| 42.7 | 7 | 10.0% | app/api/v1/services/execution_service.py:219 | ExecutionService.resume_execution() |
| 42.7 | 7 | 10.0% | app/domain/registry/loader.py:210 | get_buildable_documents() |
| 42.0 | 6 | 0.0% | app/web/bff/fragment_renderer.py:99 | FragmentRenderer.render_list() |
| 38.7 | 6 | 3.1% | app/tasks/document_builder.py:30 | run_document_build() |
| 37.7 | 6 | 4.2% | app/api/routers/admin.py:235 | replay_llm_run() |
| 36.6 | 6 | 5.3% | app/api/repositories/role_prompt_repository.py:177 | RolePromptRepository.update() |
| 34.8 | 6 | 7.1% | app/config/package_loader.py:579 | PackageLoader._resolve_template_ref() |
| 34.8 | 6 | 7.1% | app/api/v1/services/llm_execution_service.py:252 | LLMExecutionService.submit_clarification() |
| 34.8 | 6 | 7.1% | app/domain/repositories/postgres_ws_metrics_repository.py:81 | PostgresWSMetricsRepository.list_executions() |
| 30.1 | 10 | 41.4% | app/domain/prompt/assembler.py:389 | PromptAssembler._load_include() |

### LLM Layer (9 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 238.7 | 16 | 4.5% | app/llm/output_parser.py:115 | OutputValidator._validate_type() |
| 145.7 | 12 | 2.4% | app/llm/providers/anthropic.py:58 | AnthropicProvider.complete() |
| 99.2 | 11 | 10.0% | app/llm/telemetry.py:310 | TelemetryService._summarize_calls() |
| 71.4 | 9 | 8.3% | app/llm/telemetry.py:286 | TelemetryService.get_model_usage() |
| 61.9 | 8 | 5.6% | app/llm/prompt_builder.py:72 | PromptBuilder.build_user_prompt() |
| 58.3 | 8 | 7.7% | app/llm/output_parser.py:57 | OutputValidator.validate() |
| 47.4 | 7 | 6.2% | app/llm/document_condenser.py:155 | DocumentCondenser._split_sections() |
| 34.3 | 6 | 7.7% | app/llm/telemetry.py:110 | CostCalculator.calculate_cost() |
| 33.0 | 6 | 9.1% | app/llm/output_parser.py:92 | OutputValidator._validate_schema() |

### Domain Services (23 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 229.8 | 15 | 1.5% | app/domain/services/document_builder.py:417 | DocumentBuilder.build_stream() |
| 167.5 | 13 | 2.9% | app/domain/services/prompt_assembler.py:86 | PromptAssembler.assemble() |
| 140.6 | 12 | 3.7% | app/domain/services/render_model_builder.py:745 | RenderModelBuilder._process_derived_section() |
| 116.2 | 11 | 4.5% | app/domain/services/render_model_builder.py:448 | RenderModelBuilder._compute_schema_bundle_sha256() |
| 98.9 | 10 | 3.8% | app/domain/services/render_model_builder.py:666 | RenderModelBuilder._process_container_with_repeat() |
| 98.5 | 10 | 4.0% | app/domain/services/render_model_builder.py:298 | RenderModelBuilder.build() |
| 97.5 | 10 | 4.3% | app/domain/services/render_model_builder.py:586 | RenderModelBuilder._process_nested_list_shape() |
| 83.1 | 9 | 2.9% | app/domain/services/document_builder.py:356 | DocumentBuilder.build() |
| 78.4 | 9 | 5.0% | app/domain/services/render_model_builder.py:813 | RenderModelBuilder._resolve_pointer() |
| 77.2 | 9 | 5.6% | app/domain/services/render_model_builder.py:710 | RenderModelBuilder._build_parent_as_data() |
| 72.0 | 8 | 0.0% | app/domain/services/ux_config_service.py:140 | UXConfigService.get_primary_action() |
| 59.2 | 8 | 7.1% | app/domain/services/document_builder.py:278 | DocumentBuilder._complete_llm_logging() |
| 56.0 | 7 | 0.0% | app/domain/services/schema_resolver.py:210 | SchemaResolver._walk_for_refs() |
| 56.0 | 7 | 0.0% | app/domain/services/schema_resolver.py:260 | SchemaResolver._rewrite_refs() |
| 49.0 | 7 | 5.0% | app/domain/services/llm_response_parser.py:132 | LLMResponseParser.parse() |
| 47.4 | 7 | 6.2% | app/domain/services/document_builder.py:237 | DocumentBuilder._start_llm_logging() |
| 46.2 | 7 | 7.1% | app/domain/services/render_model_builder.py:528 | RenderModelBuilder._process_single_shape() |
| 37.1 | 6 | 4.8% | app/domain/services/prompt_assembler.py:215 | PromptAssembler.format_prompt_text() |
| 35.3 | 6 | 6.7% | app/domain/services/document_builder.py:204 | DocumentBuilder._prepare_build() |
| 35.3 | 6 | 6.7% | app/domain/services/document_builder.py:551 | DocumentBuilder._build_user_message() |
| 34.3 | 6 | 7.7% | app/domain/services/prompt_assembler.py:176 | PromptAssembler._build_schema_bundle() |
| 34.3 | 6 | 7.7% | app/domain/services/render_model_builder.py:639 | RenderModelBuilder._process_container_simple() |
| 31.3 | 6 | 11.1% | app/domain/services/render_model_builder.py:32 | derive_risk_level() |

### Execution (5 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 160.0 | 13 | 4.5% | app/execution/workflow_definition.py:153 | WorkflowDefinition.validate() |
| 112.9 | 11 | 5.6% | app/execution/context.py:188 | ExecutionContext.save_state() |
| 77.2 | 9 | 5.6% | app/execution/workflow_definition.py:124 | WorkflowDefinition.get_execution_order() |
| 49.0 | 7 | 5.0% | app/execution/llm_step_executor.py:137 | LLMStepExecutor._process_response() |
| 36.6 | 6 | 5.3% | app/execution/llm_step_executor.py:225 | LLMStepExecutor.continue_with_clarification() |

### Auth (6 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 119.3 | 11 | 3.6% | app/auth/routes.py:157 | callback() |
| 79.0 | 9 | 4.8% | app/auth/routes.py:33 | validate_origin() |
| 45.5 | 7 | 7.7% | app/auth/oidc_config.py:150 | OIDCConfig.normalize_claims() |
| 36.0 | 6 | 5.9% | app/auth/oidc_config.py:33 | OIDCConfig._register_providers() |
| 32.2 | 6 | 10.0% | app/auth/pat_service.py:85 | InMemoryPATRepository.delete() |
| 30.1 | 6 | 12.5% | app/auth/repositories.py:202 | InMemorySessionRepository.delete() |

### Persistence (5 critical)

| CRAP | CC | Coverage | File:Line | Function |
|-----:|---:|---------:|-----------|----------|
| 95.7 | 10 | 5.0% | app/persistence/repositories.py:100 | InMemoryDocumentRepository.save() |
| 61.9 | 8 | 5.6% | app/persistence/repositories.py:160 | InMemoryDocumentRepository.list_by_scope() |
| 60.7 | 8 | 6.2% | app/persistence/repositories.py:132 | InMemoryDocumentRepository.get_by_scope_type() |
| 56.0 | 7 | 0.0% | app/persistence/pg_repositories.py:41 | _stored_to_orm_document() |
| 33.0 | 6 | 9.1% | app/persistence/repositories.py:241 | InMemoryExecutionRepository.list_by_scope() |

---

## Subsystem Risk Summary

Subsystems ordered by total CRAP debt (sum of all critical CRAP scores):

| Subsystem | Critical Count | Total CRAP Debt | Worst Single |
|-----------|---------------|----------------|-------------|
| Workflow Engine | 79 | 11357.9 | 2190.4 |
| API Services | 35 | 5473.0 | 1020.7 |
| API v1 Routers | 21 | 4815.8 | 2532.9 |
| Document Handlers | 31 | 3573.4 | 506.0 |
| Other | 25 | 1928.2 | 309.6 |
| Domain Services | 23 | 1781.1 | 229.8 |
| Web Routes | 19 | 1658.4 | 333.0 |
| LLM Layer | 9 | 789.9 | 238.7 |
| Core/Observability | 4 | 498.4 | 342.0 |
| Execution | 5 | 435.7 | 160.0 |
| Auth | 6 | 342.1 | 119.3 |
| Persistence | 5 | 307.3 | 95.7 |

---

## Recommended Actions

1. **Workflow Engine** -- 79 critical functions with worst CRAP 2190.4. Highest total debt.
   Extract pure logic from PlanExecutor and QANodeExecutor into testable helpers.
2. **API v1 Routers** -- get_document_render_model() at CC=51 is the single worst function.
   Decompose into smaller route handlers and extract business logic to services.
3. **API Services** -- 35 critical functions. Production and admin services need coverage.
4. **Document Handlers** -- 31 critical, many mech_handlers at 0% coverage.
   Add Tier-1 tests for all mechanical handlers.
5. **Domain Services** -- RenderModelBuilder has 9 critical functions. Extract shape processing.
6. **Web Routes** -- 19 critical. Extract template context builders to testable services.

Work Statements for subsystems with CRAP > 100 worst function are tracked in WP-CRAP-001.

---

_Generated: 2026-02-26. Source: /tmp/crap_results.json_
