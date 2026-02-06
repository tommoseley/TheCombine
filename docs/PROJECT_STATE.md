# PROJECT_STATE.md

**Last Updated:** 2026-02-06
**Updated By:** Claude (WS-ADR-044-003 complete, BuildingBlocksTray, concierge_intake migration)

## Current Focus

**COMPLETE:** ADR-045 -- System Ontology (execution_state: complete)

All work statements delivered:
- **WS-ADR-045-001** (Complete): Left rail restructure, tasks as building blocks, schema extraction, docs
- **WS-ADR-045-002** (Complete): POW classification (`pow_class`, `derived_from`, `source_version`, `tags`), left rail grouping by class, create-from-reference UX, editor metadata

**COMPLETE:** ADR-046 -- POW Instance Storage and Runtime Binding (execution_state: complete)

All work statements delivered:
- **WS-ADR-046-001** (Complete): 6 phases -- DB migration, domain model, service layer, API endpoints, frontend (ProjectWorkflow component), project lifecycle integration

**IN PROGRESS:** ADR-044 -- Admin Workbench

- **WS-ADR-044-001** (Complete): Left rail and tab bar UX redesign
- **WS-ADR-044-003** (Complete): Composition-First Workbench Redesign -- Left rail shows only compositions, Building Blocks in secondary tray, PGC internals with single-expansion

---

## Admin Workbench Status

**Location:** `/admin/workbench` (SPA route)

### Features Complete
- **Workspace lifecycle**: Git-branch isolation, create/close/TTL
- **Document type editing**: Package, Role, Task, QA, PGC, Schema tabs with source/resolved views
- **Role editing**: Standalone role prompt editor
- **Template editing**: Standalone template editor with metadata (name, purpose, use_case)
- **Schema editing** (2026-02-06): Standalone schema editor with JSON content and info tabs; artifact ID URL encoding fix
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
- **POW step editor dropdowns** (2026-02-05): "Produces", "Doc Type" (iterate_over), "Doc/Entity Type" (inputs) now use select dropdowns populated with DCW list
- **DCW workflow creation** (2026-02-05): Document types without workflows show "Create Workflow" button on Workflow tab; creates skeleton graph workflow with PGC/Generation/QA/Remediation/End nodes
- **Document type creation** (2026-02-05): "+ New" button in DCW section creates new document type with skeleton package.yaml, prompts, and schema
- **Node selection glow** (2026-02-05): Selected nodes in workflow canvas have prominent multi-layer glow effect
- **Template metadata** (2026-02-05): Templates support `meta.yaml` with name, purpose, use_case fields; Metadata tab in TemplateEditor
- **"Interaction Template" label** (2026-02-05): NodePropertiesPanel "Task Ref" renamed to "Interaction Template"
- **PGC composite gate** (2026-02-06): PGC nodes are black-box gates with `gate_kind` (discovery, plan, architecture, epic, remediation, compliance); internals show Pass A (Question Generation), Entry (Operator Answers), Pass B (Clarification Merge) with progressive disclosure
- **PGC gate taxonomy** (2026-02-06): 7 gate kinds with auto-populated `produces` field (e.g., `pgc_clarifications.discovery`)
- **Node property dropdowns** (2026-02-06): Templates, roles, tasks, schemas, PGC fragments all use dropdowns populated from left rail data
- **Standalone PGC fragments** (2026-02-06): PGC prompts extracted to `combine-config/prompts/pgc/{id}.v1/`; validation rule updated to accept either embedded or standalone
- **Composition-First UI** (2026-02-06, WS-ADR-044-003): Left rail shows only POWs and DCWs; Building Blocks moved to secondary slide-out tray
- **BuildingBlocksTray** (2026-02-06): Slide-out drawer with Prompt Fragments, Templates, Schemas tabs; closes only via X button (not on item selection or outside click)
- **PGC single-expansion** (2026-02-06): Pass A and Pass B in PGC Gate Internals use mutual exclusion -- only one expanded at a time
- **concierge_intake workflow migration** (2026-02-06): Task refs updated from seed format to combine-config artifact refs (`prompt:task:intake_gate:1.0.0`)

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
| WS-ADR-044-001 | Left Rail and Tab Bar UX Redesign | Complete |
| WS-ADR-044-003 | Composition-First Workbench Redesign | Complete |

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
|   |   |   +-- TabDropdown.jsx          # Dropdown tab component
|   |   |   +-- RoleEditor.jsx
|   |   |   +-- TemplateEditor.jsx
|   |   |   +-- SchemaEditor.jsx         # Standalone schema editor
|   |   |   +-- PackageEditor.jsx
|   |   |   +-- DiffView.jsx
|   |   |   +-- GitStatusPanel.jsx
|   |   |   +-- workflow/
|   |   |       +-- StepWorkflowEditor.jsx    # Orchestration workflow editor
|   |   |       +-- WorkflowEditorContent.jsx # Reusable React Flow canvas
|   |   |       +-- WorkflowEditor.jsx        # Thin wrapper (standalone)
|   |   |       +-- WorkflowCanvas.jsx
|   |   |       +-- WorkflowNode.jsx
|   |   |       +-- NodePropertiesPanel.jsx   # PGC composite gate internals
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
|   |   +-- useAdminSchemas.js
|   |   +-- usePromptFragments.js
|   +-- api/
|   |   +-- client.js
|   |   +-- adminClient.js               # URL-encoded artifact IDs
|   +-- utils/
|       +-- workflowTransform.js
+-- dist/

combine-config/
+-- _active/active_releases.json   # Includes schemas, pgc sections
+-- document_types/                 # DCW packages with schema_ref
+-- schemas/                        # Standalone schemas (ADR-045)
|   +-- {schema_id}/releases/{ver}/schema.json
+-- prompts/roles/                  # Shared role prompts
+-- prompts/templates/              # Shared templates with meta.yaml
+-- prompts/pgc/                    # Standalone PGC fragments
|   +-- {id}.v1/releases/{ver}/pgc.prompt.txt
+-- prompts/tasks/                  # Standalone task prompts
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
12. **DCW workflow creation** -- Document types can have workflows created on-demand; skeleton includes standard PGC/Gen/QA/Remediation/End graph
13. **PGC composite gates** (2026-02-06) -- PGC is a black-box gate node with internals (Pass A: Question Gen, Entry: Operator Answers, Pass B: Clarification Merge); gate_kind determines purpose (discovery, plan, architecture, etc.)
14. **Standalone PGC fragments** -- PGC prompts live in `prompts/pgc/{id}.v1/` not embedded in document type packages; validation rule accepts either
15. **Artifact ID URL encoding** -- Frontend encodes artifact IDs with `encodeURIComponent()` for API calls
16. **BuildingBlocksTray behavior** -- Slide-out tray closes only via X button, not on item selection or clicking editor; enables multi-select workflows
17. **Task ref artifact format** -- Workflow task_refs use `prompt:task:{name}:{version}` format pointing to combine-config artifacts

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
- **WS-ADR-047-001** (Accepted): Mechanical Operations Foundation
  - Phase 1: Operation Type Registry (Extractor, Merger)
  - Phase 2: Backend Loading Service
  - Phase 3: Execution Handlers
  - Phase 4: API Endpoints
  - Phase 5: Building Blocks Tray Integration
  - Phase 6: Node Properties Panel for MECH
  - Phase 7: First Instance (pgc_clarification_merge)
- **Genericize Intake Gate**: Migrate from hardcoded intake_gate to use Interaction Template pattern
  - Create Discovery Interaction Template for intake workflows
  - Standard pattern: Interaction Template -> LLM -> Structured Output
- Clean up software_product_development definition.json to remove role/task_prompt from steps
- WS-044-04 (DocDef & Sidecar Editor) -- not started
- WS-044-10 Phase 4 (seed/ cleanup) -- not started

### Cleanup Tasks
- Delete unused `spa/src/components/LoginPage.jsx`
- Remove Zone.Identifier files (Windows metadata)
- Migrate remaining seed/ workflows and prompts to combine-config/

### Known Issues
- `clarification_questions` schema shows `active_version: null` in API despite being in active_releases.json - possible ID mismatch with `clarification_question_set`

### Design Decisions Deferred
- **Optional template tokens** (YAGNI): Allow `$$TOKEN?` syntax for optional tokens that get omitted if not in includes map. Trivial to implement when customer need arises.
