# WS-PIPELINE-003: Legacy Ontology Cleanup (Epic/Feature/Backlog Removal)

## Status: Accepted

## Parent Work Package: WP-PIPELINE-001

## Governing References

- ADR-050 -- Work Statement Verification Constitution
- ADR-051 -- Work Package as Runtime Primitive
- ADR-052 -- Document Pipeline WP/WS Integration
- POL-WS-001 -- Work Statement Standard
- WS-DCW-004 -- Prior attempt at epic removal (incomplete)

## Verification Mode: A

## Allowed Paths

- combine-config/
- app/
- tests/
- seed/ (if any references remain)

---

## Objective

Complete the epic/feature/backlog_item removal that WS-DCW-004 started but did not finish. Remove all references to the deprecated ontology (epics, features, backlog items, stories) from combine-config, app code, and test code. Clean up active_releases.json to remove legacy entries. The WP/WS ontology is the only work decomposition model.

---

## Preconditions

- WS-PIPELINE-001 is complete (pipeline uses IP, not IPP+IPF)
- The software_product_development POW uses WP/WS ontology

---

## Contamination Audit (Current State)

### combine-config (by area)

| Area | Files | Examples |
|------|-------|---------|
| document_types/epic/ | Entire directory | schema, package.yaml, prompts |
| document_types/feature/ | Entire directory | schema, package.yaml, prompts |
| document_types/backlog_item/ | Entire directory | schema, package.yaml (12+ epic refs) |
| workflows/backlog_generator/ | Entire directory | definition |
| workflows/story_set_generator/ | Entire directory | definition |
| workflows/feature_set_generator/ | Entire directory | definition |
| schemas/epic/ | Entire directory | schema.json |
| schemas/backlog_item/ | Entire directory | references epic |
| schemas/workflow_plan/ | schema.json | references epic |
| schemas/clarification_question_set/ | schema.json | references epic |
| prompts/tasks/epic_backlog/ | Entire directory | task prompt |
| prompts/tasks/epic_architecture/ | Entire directory | task prompt |
| prompts/tasks/story_backlog/ | Entire directory | task prompt |
| prompts/tasks/story_set_generator/ | Entire directory | task prompt |
| prompts/tasks/feature_set_generator/ | Entire directory | task prompt |
| prompts/tasks/story_implementation/ | Entire directory | task prompt |
| prompts/tasks/backlog_generator/ | Entire directory | task prompt |
| prompts/tasks/plan_explanation/ | task prompt | references epic |
| prompts/tasks/implementation_plan/ | task prompt | references epic |
| prompts/tasks/technical_architecture/ | task prompt | references epic |
| prompts/tasks/project_discovery_questions/ | task prompt | references epic |
| prompts/pgc/ | primary_implementation_plan, technical_architecture | references epic |
| active_releases.json | Multiple sections | epic doc type, tasks, schemas |

### App Code (50+ files)

| Area | File Count | Key Files |
|------|-----------|-----------|
| persistence/models.py | 1 | Database models |
| api/models/ | 4 | role_task, document_definition, llm_thread, document, document_type |
| api/routers/ | 1 | commands |
| api/schemas/ | 2 | responses, requests |
| api/v1/ | 2 | projects router, workflow schema |
| api/utils/ | 1 | id_generators |
| api/services/ | 6 | role_prompt, doc_definition, workspace, search, production, project |
| core/ | 2 | middleware/deprecation, config |
| domain/models/ | 1 | llm_logging |
| domain/registry/ | 1 | loader |
| domain/schemas/ | 1 | metrics |
| domain/workflow/ | 6 | iteration, plan_executor, input_resolver, scope |
| domain/handlers/ | 4 | work_package, backlog_item, base, story_backlog |
| domain/services/ | 8 | document_builder, set_reconciler, render_model_builder, staleness, story_backlog, graph_validator, llm_response_parser, fanout |
| web/routes/ | 4 | search, view, document, debug, composer |
| web/templates/ | 5 | production line, story_backlog, home, search_results, document_viewer |
| web/static/ | 2 | thread_monitor.js, SPA bundle |

### Test Code (34 files)

| Area | File Count | Key Files |
|------|-----------|-----------|
| api/ | 3 | command_routes, conftest, workflows |
| domain/registry/ | 2 | document_registry, view_docdef_resolution |
| domain/workflow/ | 7 | state, loader, models, executor, input_resolver, context, validator, iteration |
| domain/services/ | 4 | staleness, ux_config, render_model_builder |
| tier1/workflow/ | 1 | spawn_child_documents |
| tier1/handlers/ | 5 | production_floor_wp_ws, ipf_wp_reconciliation, epic_feature_cleanup, epic_feature_removal, ipp_wp_candidates |
| tier1/services/ | 5 | fanout, backlog_pipeline, production_child_tracks, backlog_ordering, graph_validator |
| integration/ | 2 | docdef_golden_traces, adr034_proof |
| unit/ | 1 | document_ownership |
| root tests/ | 1 | document_status_service |

---

## Scope

### In Scope

1. **combine-config cleanup:**
   - Remove or archive: document_types/epic/, document_types/feature/, document_types/backlog_item/
   - Remove or archive: workflows/backlog_generator/, workflows/story_set_generator/, workflows/feature_set_generator/
   - Remove or archive: schemas/epic/
   - Remove or archive: prompts/tasks/epic_backlog/, epic_architecture/, story_backlog/, story_set_generator/, feature_set_generator/, story_implementation/, backlog_generator/
   - Clean epic references from: schemas/backlog_item/, schemas/workflow_plan/, schemas/clarification_question_set/
   - Clean epic references from remaining task prompts (plan_explanation, implementation_plan, technical_architecture, project_discovery_questions)
   - Clean epic references from PGC prompts
   - Update active_releases.json: remove epic, feature, backlog_item doc types; remove epic_backlog, epic_architecture, story_backlog, story_implementation, backlog_generator, plan_explanation, strategy_* tasks; remove backlog_generator, plan_explanation workflows

2. **App code cleanup:**
   - Remove handlers: backlog_item_handler.py, story_backlog_handler.py
   - Remove services: story_backlog_service.py, set_reconciler.py (if epic-only), backlog-specific services
   - Clean references in: models, routers, schemas, services, templates, static files
   - Remove deprecated document type registrations
   - Remove epic/feature/backlog from ID generators, display name maps, search routes

3. **Test code cleanup:**
   - Remove test files for deprecated features (epic_feature_cleanup, epic_feature_removal, backlog_pipeline, backlog_ordering, etc.)
   - Clean epic references from remaining test files
   - Update fixtures and conftest files

4. **SPA bundle:**
   - Rebuild after cleaning source components that reference epic

### Out of Scope

- Pipeline restructuring (WS-PIPELINE-001)
- Floor layout changes (WS-PIPELINE-002)
- Database migration (epic data in existing projects remains; no schema migration)
- Removing plan_explanation document type (may have non-epic uses -- audit first)

---

## Tier 1 Verification Criteria

1. `grep -r "epic" combine-config/ --exclude-dir=_archive` returns zero matches
2. `grep -r "epic" app/` returns zero matches (excluding migrations, comments referencing ADRs/WSs by name)
3. `grep -r "backlog_item" app/` returns zero matches (same exclusions as above)
4. `grep -r "story_backlog" app/` returns zero matches
5. `grep -r "feature_set_generator" combine-config/ --exclude-dir=_archive` returns zero matches
6. active_releases.json contains no epic, feature, or backlog_item entries in any section
7. No handler registered for epic, feature, or backlog_item in registry.py
8. `grep -r "epic" tests/ --exclude-dir=_archive` returns zero matches (excluding test names that verify removal)
9. Tier 0 returns zero
10. All remaining tests pass

---

## Procedure

### Phase 1: Archive Deprecated Config

1. Create combine-config/_archive/ directory (if it doesn't exist)
2. Move (not delete) deprecated directories to _archive/:
   - document_types/epic/ -> _archive/document_types/epic/
   - document_types/feature/ -> _archive/document_types/feature/
   - document_types/backlog_item/ -> _archive/document_types/backlog_item/
   - workflows/backlog_generator/ -> _archive/workflows/backlog_generator/
   - workflows/story_set_generator/ -> _archive/workflows/story_set_generator/
   - workflows/feature_set_generator/ -> _archive/workflows/feature_set_generator/
   - schemas/epic/ -> _archive/schemas/epic/
   - prompts/tasks/epic_backlog/ -> _archive/prompts/tasks/epic_backlog/
   - (and remaining deprecated prompt dirs)
3. Update active_releases.json: remove all deprecated entries

### Phase 2: Clean Remaining Config References

4. Clean epic references from prompts that survive (plan_explanation, implementation_plan, TA, PD questions)
5. Clean schemas/backlog_item/, schemas/workflow_plan/, schemas/clarification_question_set/
6. Clean PGC prompts

### Phase 3: Clean App Code

7. Remove deprecated handlers and services
8. Clean references in models, routers, schemas, services
9. Clean templates and static files
10. Update handler registry
11. Remove deprecated display names, ID generators, route handlers

### Phase 4: Clean Tests

12. Remove test files for deprecated features
13. Clean epic references from remaining tests
14. Update fixtures and conftest

### Phase 5: Verify

15. Run grep verification (criteria 1-6)
16. Tier 0 returns zero
17. All tests pass

---

## Prohibited Actions

- Do not delete archived config (move to _archive/, not rm)
- Do not modify pipeline structure (that is WS-PIPELINE-001)
- Do not modify floor layout (that is WS-PIPELINE-002)
- Do not run database migrations
- Do not remove plan_explanation without auditing non-epic uses first
- Do not modify the software_product_development POW (already handled by WS-PIPELINE-001)

---

## Risk

The main risk is breaking something that still references a deprecated type at runtime. Mitigation: the grep-based verification criteria ensure no references survive. Additionally, Tier 0 will catch import errors and test failures.

If plan_explanation has non-epic uses, it survives this cleanup. The audit will determine.

---

_End of WS-PIPELINE-003_
