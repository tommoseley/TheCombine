# PROJECT_STATE.md

**Last Updated:** 2026-02-04
**Updated By:** Claude (System Ontology and Workbench Planning)

## Current Focus

**ACCEPTED:** ADR-045 -- System Ontology: Primitives, Composites, and Configuration Taxonomy

Formalized the system's artifact classification:
- **Primitives:** Prompt Fragment (shapes behavior), Schema (defines acceptability)
- **Ontological term:** Interaction Pass (binds fragments + schema at execution time; vocabulary, not configuration)
- **Composites:** Role, Task, DCW (Document Creation/Production Workflow), POW (Project Orchestration Workflow)

**DRAFTED:** WS-ADR-045-001 -- Admin Workbench Left Rail Restructure and Schema Extraction

4-phase implementation plan:
1. Left rail restructure (Production Workflows > Building Blocks > Governance)
2. Tasks as Building Blocks
3. Schema extraction to standalone `combine-config/schemas/`
4. CLAUDE.md and documentation updates

### Recent Commits
All prior uncommitted work has been committed and pushed to `workbench/ws-d1de5d9924b1`:
- `9ec8196` feat(api): Admin workbench workflow editing, orchestration CRUD, and auth improvements
- `b6f9457` feat(config): Add orchestration workflows, prompt templates, and package updates
- `076190d` feat(spa): Admin workbench editors, workflow UI, and component updates
- `0b3783d` build(spa): Update SPA build artifacts
- `955e7c2` docs: Add session logs, update project state, and branding instructions

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

### Next: Left Rail Restructure (WS-ADR-045-001)
Current left rail mixes primitives and composites. ADR-045 mandates reorganization:
```
Production Workflows
  > Project Workflows (POWs)
  > Document Workflows (DCWs)
Building Blocks
  > Roles / Tasks / Schemas / Templates
Governance
  > Active Releases / Git Status
```

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
+-- /api/v1/intake/*     -> REST + SSE: concierge intake workflow
+-- /api/v1/production/* -> REST + SSE: production line status
+-- /api/v1/admin/workbench/*    -> Read-only config browsing
+-- /api/v1/admin/workspaces/*   -> Workspace-scoped editing + commit
+-- /assets/*            -> SPA static assets (JS, CSS)
+-- /admin/*             -> Jinja2 templates (legacy)

React SPA (Vite)
+-- src/
|   +-- App.jsx
|   +-- components/
|   |   +-- admin/
|   |   |   +-- AdminWorkbench.jsx       # Three-panel layout
|   |   |   +-- DocTypeBrowser.jsx       # Sidebar (to be restructured per ADR-045)
|   |   |   +-- PromptEditor.jsx         # Tab-based editor (incl. Workflow tab)
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
```

---

## Key Technical Decisions

1. **SPA at Root** -- SPA served for all users, handles its own auth state
2. **Lobby Boundary** -- No production UI components shared with lobby
3. **Document Production vs Orchestration Workflows** -- Graph-based (ADR-039) for per-document production, step-based (workflow.v1) for cross-document orchestration
4. **Orchestration steps are declarative** -- Steps declare what document to produce, not how (role/task belong on production workflow)
5. **@dnd-kit for drag-to-reorder** -- Modern React DnD, supports nested sortable contexts
6. **Workspace-scoped CRUD** -- Workflow create/delete goes through workspace service for Git-branch isolation
7. **System Ontology (ADR-045)** -- Prompt Fragments shape behavior; Schemas define acceptability; Interaction Passes bind and execute both

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
- Accept and execute WS-ADR-045-001 (left rail restructure, tasks as building blocks, schema extraction)
- Change "Produces" field in orchestration step editor to a dropdown of available document production workflows
- Clean up software_product_development definition.json to remove role/task_prompt from steps
- WS-044-04 (DocDef & Sidecar Editor) -- not started
- WS-044-10 Phase 4 (seed/ cleanup) -- not started

### Cleanup Tasks
- Delete unused `spa/src/components/LoginPage.jsx`
- Remove Zone.Identifier files (Windows metadata)
- Commit ADR-045 and WS-ADR-045-001 to Git
