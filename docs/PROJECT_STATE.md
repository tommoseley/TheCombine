# PROJECT_STATE.md

**Last Updated:** 2026-02-04
**Updated By:** Claude (WS-ADR-044-001 executed: Admin Workbench UX redesign)

## Current Focus

**COMPLETE:** ADR-045 -- System Ontology (execution_state: complete)

All work statements delivered:
- **WS-ADR-045-001** (Complete): Left rail restructure, tasks as building blocks, schema extraction, docs
- **WS-ADR-045-002** (Complete): POW classification (`pow_class`, `derived_from`, `source_version`, `tags`), left rail grouping by class, create-from-reference UX, editor metadata

**COMPLETE:** ADR-046 -- POW Instance Storage and Runtime Binding (execution_state: complete)

All work statements delivered:
- **WS-ADR-046-001** (Complete): 6 phases -- DB migration, domain model, service layer, API endpoints, frontend (ProjectWorkflow component), project lifecycle integration

**IN PROGRESS:** ADR-044 -- Admin Workbench

- **WS-ADR-044-001** (Executed, pending verification): Left rail and tab bar UX redesign

---

## Admin Workbench Status

**Location:** `/admin/workbench` (SPA route)

### Features Complete
- **Workspace lifecycle**: Git-branch isolation, create/close/TTL
- **Document type editing**: Package, Role, Task, QA, PGC, Schema tabs with source/resolved views
- **Role editing**: Standalone role prompt editor
- **Template editing**: Standalone template editor
- **Package editing**: Standalone package editor
- **Diff view**: Side-by-side diff viewer
- **Workflow tab on document types**: React Flow canvas for document production workflows (concierge_intake, project_discovery)
- **Orchestration workflow editor**: Interactive step editing with drag-to-reorder (@dnd-kit), add/delete steps, JSON tab, metadata view
- **Workflow CRUD**: Create new orchestration workflows from sidebar, delete from editor header
- **Git status panel**: Dirty indicator, commit dialog, discard, diff view
- **Preview engine**: Resolved prompt preview with provenance
- **Tier 1 validation**: Package validation, graph workflow validation (PlanValidator), step workflow JSON validation
- **Left rail redesigned** (WS-ADR-044-001): Flat POW list with `pow_class` badges, flat alphabetical DCW list with version badges, collapsible Building Blocks with colored dots and count badges, Git Status in Governance
- **Sidebar header hierarchy**: Distinct background colors and typography for group vs sub-section headers; collapsed/expanded state persisted to localStorage
- **Grouped tab bar** (WS-ADR-044-001): Tabs grouped by Interaction Pass -- Package, Workflow, Generation (dropdown), QA (dropdown), PGC (dropdown), Schema; TabDropdown component with click-outside-to-close
- **Focused Building Block view**: Interactions/Schemas opened from Building Blocks show just the artifact content without tab bar; DCWs show full grouped tab bar
- **Interactions as Building Blocks**: Derived from document types, navigate to focused task prompt view; selection decoupled from Document Workflows
- **Schemas as Building Blocks**: Derived from document types, navigate to focused schema view; selection decoupled from Document Workflows
- **Standalone schema extraction**: 7 schemas extracted to `combine-config/schemas/` with `schema_ref` in package.yaml
- **Dual-read schema resolution**: Backend resolves standalone schemas first, falls back to packaged
- **Schema API endpoints**: `/admin/workbench/schemas` list and `/admin/workbench/schemas/{id}` detail
- **POW classification** (WS-ADR-045-002): `pow_class` (reference/template/instance), `derived_from` lineage, `tags` on workflow definitions
- **Create-from-reference UX**: Primary creation path forks a reference POW as a template with lineage; blank creation secondary
- **Editor metadata**: Classification badge in header, editable tags, derived_from navigation link, source version display
- **Dot color CSS variables**: `--dot-green`, `--dot-blue`, `--dot-purple` defined per theme (Light, Industrial, Blueprint)

---

## WS-044 Status

| WS | Title | Status |
|---|---|---|
| WS-044-01 | Core Architecture | Complete |
| WS-044-02 | Package Model | Complete |
| WS-044-03 | Prompt & Schema Editors | Complete |
| WS-044-04 | DocDef & Sidecar Editor | Not started |
| WS-044-05 | Workflow & Production Mode Config | Partial |
| WS-044-06 | Preview & Dry-Run Engine | Complete |
| WS-044-07 | Release & Rollback Management | Complete |
| WS-044-08 | Governance Guardrails | Complete |
| WS-044-09 | Git Repository Layout | Complete |
| WS-044-10 | Migration (seed/ -> combine-config/) | Phases 1-3 complete |
| WS-044-11 | Golden Trace Runner | Deferred |
| WS-ADR-044-001 | Left Rail and Tab Bar UX Redesign | Executed (pending verification) |

## WS-045 Status (ADR-045 execution_state: complete)

| WS | Title | Status |
|---|---|---|
| WS-ADR-045-001 | Left Rail Restructure and Schema Extraction | Complete |
| WS-ADR-045-002 | POW Classification, Lineage, Left Rail Grouping | Complete |

## WS-046 Status (ADR-046 execution_state: complete)

| WS | Title | Status |
|---|---|---|
| WS-ADR-046-001 | POW Instance Storage and Runtime Binding | Complete |

---

## React SPA Status

**Location:** `spa/` directory
**Served At:** `/` (root URL for all users)

### Features Complete
- **Lobby**: Entry terminal for unauthenticated users
- **Authentication**: OAuth SSO (Google, Microsoft)
- **User Management**: Bottom-left sidebar with avatar, name, email
- ProjectTree sidebar with project selection highlighting
- Floor component with Production Line status and Project Info block
- **ProjectWorkflow panel**: Assign workflow to project, instance viewer with steps and drift indicator
- Theme switching (Industrial, Light, Blueprint)
- Concierge intake sidecar with chat interface
- SSE-based generation progress
- Project management: rename, archive/unarchive, delete
- **Admin Workbench**: Full prompt/workflow editing environment

### Authentication Flow
1. User visits `/` -> SPA loads
2. SPA checks auth via `/api/me`
3. Unauthenticated -> Lobby component
4. User clicks SSO button -> `/auth/login/{provider}`
5. OAuth callback -> redirects to `/`
6. Authenticated -> Production environment (AppContent)

---

## Architecture

```
FastAPI Backend
+-- /                    -> Serve React SPA (handles own auth state)
+-- /api/me              -> Auth check endpoint
+-- /auth/login/*        -> OAuth initiation
+-- /auth/callback/*     -> OAuth callback
+-- /auth/logout         -> Session termination
+-- /api/v1/projects/*   -> REST: list, create, get, update, archive, delete
+-- /api/v1/projects/{id}/workflow  -> REST: workflow instance CRUD, drift, history
+-- /api/v1/intake/*     -> REST + SSE: concierge intake workflow
+-- /api/v1/production/* -> REST + SSE: production line status
+-- /api/v1/admin/workbench/*    -> Read-only config browsing (incl. /schemas)
+-- /api/v1/admin/workspaces/*   -> Workspace-scoped editing + commit
+-- /assets/*            -> SPA static assets (JS, CSS)
+-- /admin/*             -> Jinja2 templates (legacy)

React SPA (Vite)
+-- src/
|   +-- App.jsx
|   +-- components/
|   |   +-- admin/
|   |   |   +-- AdminWorkbench.jsx       # Three-panel layout
|   |   |   +-- DocTypeBrowser.jsx       # Sidebar (composition hierarchy)
|   |   |   +-- PromptEditor.jsx         # Grouped tab bar editor
|   |   |   +-- TabDropdown.jsx          # Dropdown tab component (new)
|   |   |   +-- RoleEditor.jsx
|   |   |   +-- TemplateEditor.jsx
|   |   |   +-- PackageEditor.jsx
|   |   |   +-- DiffView.jsx
|   |   |   +-- GitStatusPanel.jsx
|   |   |   +-- workflow/
|   |   |       +-- StepWorkflowEditor.jsx    # Orchestration workflow editor
|   |   |       +-- WorkflowEditorContent.jsx # Reusable React Flow canvas
|   |   |       +-- WorkflowEditor.jsx        # Thin wrapper (standalone)
|   |   |       +-- WorkflowCanvas.jsx
|   |   |       +-- WorkflowNode.jsx
|   |   |       +-- NodePropertiesPanel.jsx
|   |   |       +-- EdgePropertiesPanel.jsx
|   |   +-- ProjectTree.jsx
|   |   +-- Floor.jsx
|   |   +-- ProjectWorkflow.jsx          # Workflow instance viewer (ADR-046)
|   |   +-- ConciergeIntakeSidecar.jsx
|   +-- hooks/
|   |   +-- useAuth.jsx
|   |   +-- useWorkspace.js
|   |   +-- useWorkflowEditor.js
|   |   +-- useAdminWorkflows.js
|   |   +-- useAdminRoles.js
|   |   +-- useAdminTemplates.js
|   +-- api/
|   |   +-- client.js
|   |   +-- adminClient.js
|   +-- utils/
|       +-- workflowTransform.js
+-- dist/

combine-config/
+-- _active/active_releases.json   # Includes schemas section
+-- document_types/                 # DCW packages with schema_ref
+-- schemas/                        # Standalone schemas (ADR-045)
|   +-- {schema_id}/releases/{ver}/schema.json
+-- prompts/roles/                  # Shared role prompts
+-- prompts/templates/              # Shared templates
+-- workflows/                      # Workflow definitions
```

---

## Key Technical Decisions

1. **SPA at Root** -- SPA served for all users, handles its own auth state
2. **Lobby Boundary** -- No production UI components shared with lobby
3. **Document Production vs Orchestration Workflows** -- Graph-based (ADR-039) for per-document production, step-based (workflow.v2) for cross-document orchestration
4. **Orchestration steps are declarative** -- Steps declare what document to produce, not how (role/task belong on production workflow)
5. **@dnd-kit for drag-to-reorder** -- Modern React DnD, supports nested sortable contexts
6. **Workspace-scoped CRUD** -- Workflow create/delete goes through workspace service for Git-branch isolation
7. **System Ontology (ADR-045)** -- Prompt Fragments shape behavior; Schemas define acceptability; Interaction Passes bind and execute both
8. **Schema dual-read** -- Standalone schemas checked first, packaged schemas as fallback (transition support)
9. **POW classification (ADR-045/WS-002)** -- `pow_class` (reference/template/instance), `derived_from` lineage, `tags`; left rail groups by class; create-from-reference as primary path
10. **Instance POWs in database (ADR-046)** -- Project-scoped mutable workflow instances stored in DB, not `combine-config/`; drift computed at read time; append-only audit trail
11. **Grouped tab bar (WS-ADR-044-001)** -- Tabs grouped by Interaction Pass (Generation, QA, PGC) with dropdown menus; focused view for Building Block artifacts

---

## Quick Commands

```bash
# Run backend
cd ~/dev/TheCombine && source venv/bin/activate
python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

# Build SPA for production
cd spa && npm run build

# Run SPA dev server (for development only)
cd spa && npm run dev
```

---

## Handoff Notes

### Next Work
- Visual verification of WS-ADR-044-001 against approved wireframe (`docs/prototypes/workbench-wireframe.html`)
- Change "Produces" field in orchestration step editor to a dropdown of available document production workflows
- Clean up software_product_development definition.json to remove role/task_prompt from steps
- WS-044-04 (DocDef & Sidecar Editor) -- not started
- WS-044-10 Phase 4 (seed/ cleanup) -- not started

### Cleanup Tasks
- Delete unused `spa/src/components/LoginPage.jsx`
- Remove Zone.Identifier files (Windows metadata)
- Uncommitted schema changes in `combine-config/document_types/` (primary_implementation_plan, technical_architecture) -- review and commit or discard

### Known Risk
- `reflection_prompt` artifact type exists in `allPromptKinds` but is not mapped to any tab dropdown group; verify no current document types use it
