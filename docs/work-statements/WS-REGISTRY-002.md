# WS-REGISTRY-002: story_backlog Retirement

## Status: Accepted

## Parent: WP-REGISTRY-001

## Governing References

- Audit: `docs/audits/2026-02-26-post-pipeline-003.md` (finding #5, #7)
- Audit: `docs/audits/2026-02-26-audit-summary.md` (finding #8)
- WP-REGISTRY-001 Phase 2 ("Sweep the Yard")

---

## Intent

The `story_backlog` document type is half-governed: handler registered in code, service exists, task prompt in `combine-config/prompts/tasks/`, but no `active_releases.document_types` entry and no `combine-config/document_types/` directory. The related `story_detail` doc type exists only in seed data and the story_backlog service.

**Decision: Retire.** Remove all story_backlog and story_detail infrastructure from the runtime codebase.

---

## Scope In

- Delete story_backlog handler and service files
- Remove handler registration from registry
- Remove story_backlog task from active_releases.json
- Remove story_backlog and story_detail seed data from loader.py
- Delete story_backlog task prompt directory
- Remove story_backlog endpoints from commands router (keep thread + document build endpoints)
- Remove story_backlog auto-init from document routes
- Remove story_backlog UI elements from viewer template
- Remove StoryBacklogView deprecation route
- Remove story_backlog from migration CASE statement
- Clean up affected test files
- Delete task prompt directory
- Clean stale epic references in production_service.py (comments + runtime `epic_id` bug)
- Remove dead `epic_context` parameter from role_prompt_service.py

## Scope Out

- Do NOT modify deprecated/ directory (historical artifacts)
- Do NOT modify handlers other than story_backlog
- Do NOT modify workflow definitions
- Do NOT modify active document type configs beyond removing story_backlog task entry

---

## Inventory

### Files to Delete (2)

| File | Lines | Reason |
|------|-------|--------|
| `app/domain/handlers/story_backlog_handler.py` | 88 | 100% story_backlog |
| `app/domain/services/story_backlog_service.py` | 771 | 100% story_backlog |

### Directories to Delete (1)

| Directory | Reason |
|-----------|--------|
| `combine-config/prompts/tasks/story_backlog/` | Task prompt for retired type |

### Files to Edit (14)

| File | Change |
|------|--------|
| `app/domain/handlers/registry.py` | Remove import + dict entry |
| `combine-config/_active/active_releases.json` | Remove tasks.story_backlog |
| `app/domain/registry/loader.py` | Remove story_backlog + story_detail seed blocks |
| `app/api/routers/commands.py` | Remove 5 story_backlog endpoints, keep thread + doc build |
| `app/api/main.py` | Update comments (remove WS-STORY-BACKLOG-COMMANDS) |
| `app/web/routes/public/document_routes.py` | Remove config entry + auto-init block |
| `app/web/templates/public/partials/_document_viewer_content.html` | Remove icon, button, JS functions |
| `app/core/middleware/deprecation.py` | Remove StoryBacklogView route mapping |
| `app/api/services/production_service.py` | Fix `epic_id` -> `work_package_id`, update 3 stale comments |
| `app/api/services/role_prompt_service.py` | Remove dead `epic_context` param, update docstrings |
| `app/domain/services/staleness_service.py` | Remove comment |
| `alembic/versions/20260112_001_add_view_docdef.py` | Remove CASE branch |
| `tests/unit/test_document_ownership.py` | Remove story_backlog tests |
| `tests/domain/services/test_staleness_service.py` | Remove story_backlog test |
| `tests/test_document_status_service.py` | Change doc_type_id reference |
| `tests/integration/test_adr034_proof.py` | Remove StoryBacklog fixtures/tests |
| `tests/integration/test_docdef_golden_traces.py` | Remove golden trace class |
| `tests/core/middleware/test_deprecation.py` | Update route references |
| `tests/test_document_status_api.py.skip` | Remove story_backlog fixtures |

---

## Verification

1. New retirement test passes (`tests/tier1/test_story_backlog_retirement.py`)
2. `ops/scripts/tier0.sh` passes (excluding known pre-existing failures)
3. Zero grep matches for `story_backlog|StoryBacklog|story_detail|StoryDetail` in `app/` and `combine-config/`
4. Registry integrity check passes

---

_End of WS-REGISTRY-002_
