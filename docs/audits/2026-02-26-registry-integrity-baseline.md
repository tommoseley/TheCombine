# Registry Integrity Baseline -- 2026-02-26

**Branch:** `workbench/ws-b12f2a74613a`
**Script:** `ops/scripts/check_registry_integrity.py`
**WS:** WS-REGISTRY-001 (Canonical Paths & Integrity Gate)

---

## Result: ALL 81 ASSETS VERIFIED

All entries in `active_releases.json` resolve to existing, valid artifacts at their canonical global paths.

---

## Full Check Results

### document_types (13 entries) -- ALL PASS

| ID | Version | Status |
|----|---------|--------|
| backlog_item | 1.0.0 | PASS |
| concierge_intake | 1.0.0 | PASS |
| epic | 1.0.0 | PASS |
| execution_plan | 1.0.0 | PASS |
| feature | 1.0.0 | PASS |
| implementation_plan | 1.0.0 | PASS |
| intent_packet | 1.0.0 | PASS |
| pipeline_run | 1.0.0 | PASS |
| plan_explanation | 1.0.0 | PASS |
| project_discovery | 1.4.0 | PASS |
| technical_architecture | 1.0.0 | PASS |
| work_package | 1.0.0 | PASS |
| work_statement | 1.0.0 | PASS |

### tasks (28 entries) -- ALL PASS

Includes `work_package:1.0.0` and `work_statement:1.0.0` -- newly created by WS-REGISTRY-001.

| ID | Version | Status |
|----|---------|--------|
| backlog_generator | 1.0.0 | PASS |
| clarification_questions_generator | 1.1.0 | PASS |
| concierge_intent_reflection | 1.0.0 | PASS |
| epic_architecture | 1.0.0 | PASS |
| epic_backlog | 1.0.0 | PASS |
| implementation_plan | 1.0.0 | PASS |
| intake_document_generation | 1.0.0 | PASS |
| intake_gate | 1.0.0 | PASS |
| intake_qa | 1.0.0 | PASS |
| plan_explanation | 1.0.0 | PASS |
| pm_discovery_generation | 1.0.0 | PASS |
| pm_discovery_qa | 1.0.0 | PASS |
| project_discovery | 1.4.0 | PASS |
| project_discovery_qa | 1.1.0 | PASS |
| project_discovery_questions | 1.0.0 | PASS |
| qa_semantic_compliance | 1.1.0 | PASS |
| story_backlog | 1.0.0 | PASS |
| story_implementation | 1.0.0 | PASS |
| strategy_architecture_v1 | 1.0.0 | PASS |
| strategy_discovery_v1 | 1.0.0 | PASS |
| strategy_requirements_v1 | 1.0.0 | PASS |
| strategy_review_v1 | 1.0.0 | PASS |
| task_prompt_auditor | 1.0.0 | PASS |
| task_prompt_certification_checklist | 1.0.0 | PASS |
| technical_architecture | 1.0.0 | PASS |
| technical_architecture_questions | 1.0.0 | PASS |
| work_package | 1.0.0 | PASS |
| work_statement | 1.0.0 | PASS |

### schemas (23 entries) -- ALL PASS

Includes `work_package:1.0.0` and `work_statement:1.0.0` -- newly created by WS-REGISTRY-001.

| ID | Version | Status |
|----|---------|--------|
| backlog_item | 1.0.0 | PASS |
| clarification_question_set | 1.0.0 | PASS |
| clarification_questions | 1.0.0 | PASS |
| concierge_intake | 1.0.0 | PASS |
| epic | 1.0.0 | PASS |
| execution_plan | 1.0.0 | PASS |
| feature | 1.0.0 | PASS |
| implementation_plan | 1.0.0 | PASS |
| intake_classification | 1.0.0 | PASS |
| intake_confirmation | 1.0.0 | PASS |
| intent_packet | 1.0.0 | PASS |
| pipeline_run | 1.0.0 | PASS |
| plan_explanation | 1.0.0 | PASS |
| project_discovery | 1.4.0 | PASS |
| qa_semantic_compliance_output | 1.0.0 | PASS |
| route_confirmation | 1.0.0 | PASS |
| routing_decision | 1.0.0 | PASS |
| spawn_receipt | 1.0.0 | PASS |
| technical_architecture | 1.0.0 | PASS |
| work_package | 1.0.0 | PASS |
| work_statement | 1.0.0 | PASS |
| workflow | 1.0.0 | PASS |
| workflow_plan | 1.0.0 | PASS |

### roles (7 entries) -- ALL PASS

| ID | Version | Status |
|----|---------|--------|
| business_analyst | 1.0.0 | PASS |
| developer | 1.0.0 | PASS |
| project_manager | 1.0.0 | PASS |
| quality_assurance | 1.0.0 | PASS |
| role_prompt_auditor | 1.0.0 | PASS |
| role_prompt_certification_checklist | 1.0.0 | PASS |
| technical_architect | 1.0.0 | PASS |

### workflows (10 entries) -- ALL PASS

| ID | Version | Status |
|----|---------|--------|
| backlog_generator | 1.0.0 | PASS |
| concierge_intake | 1.4.0 | PASS |
| implementation_plan | 1.0.0 | PASS |
| intake_and_route | 1.0.0 | PASS |
| plan_explanation | 1.0.0 | PASS |
| project_discovery | 2.0.0 | PASS |
| software_product_development | 1.0.0 | PASS |
| technical_architecture | 2.0.0 | PASS |
| work_package | 1.0.0 | PASS |
| work_statement | 1.0.0 | PASS |

---

## Notes

- Zero failures at baseline. All active_releases entries resolve correctly.
- `work_package` and `work_statement` task prompts and schemas were created by WS-REGISTRY-001 to resolve audit findings #1 and #2.
- Sections not checked: `mechanical_ops`, `pgc`, `templates` (different resolution patterns, not covered by this gate).
- Future WSs (WS-CLEANUP-EFS-001, WS-PIPELINE-001) will modify active_releases entries. The gate will catch any breakage they introduce.
