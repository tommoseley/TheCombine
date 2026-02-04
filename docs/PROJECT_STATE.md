# PROJECT_STATE.md

**Last Updated:** 2026-02-04
**Updated By:** Claude (Admin Workbench Workflow Editing)

## Current Focus

**IN PROGRESS:** Admin Workbench — Workflow Editing Restructure

Separated two distinct workflow types in the Admin Workbench:
- **Document Production Workflows** (graph-based, ADR-039) now appear as a "Workflow" tab on their document type in PromptEditor
- **Project Orchestration Workflows** (step-based, workflow.v1) have a dedicated StepWorkflowEditor with interactive editing, drag-to-reorder, and workflow CRUD

Key architectural insight: orchestration steps declare WHAT document to produce (e.g., `project_discovery`), not HOW. Role and task prompt bindings belong on the document production workflow's task node.

### Uncommitted Changes
All work is uncommitted. Large changeset spanning backend and frontend — should commit soon.

---

## Admin Workbench Status

**Location:** `/admin/workbench` (SPA route)

### Features Complete
- **Workspace lifecycle**: Git-branch isolation, create/close/TTL
- **Document type editing**: Package, Role, Task, QA, PGC, Schema tabs with source/resolved views
- **Role editing**: Standalone role prompt editor
- **Template editing**: Standalone template editor
- **Workflow tab on document types**: React Flow canvas for document production workflows (concierge_intake, project_discovery)
- **Orchestration workflow editor**: Interactive step editing with drag-to-reorder (@dnd-kit), add/delete steps, JSON tab, metadata view
- **Workflow CRUD**: Create new orchestration workflows from sidebar, delete from editor header
- **Git status panel**: Dirty indicator, commit dialog, discard, diff view
- **Preview engine**: Resolved prompt preview with provenance
- **Tier 1 validation**: Package validation, graph workflow validation (PlanValidator), step workflow JSON validation

### In Progress
- Produces field should be a dropdown of available document production workflows

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
1. User visits `/` → SPA loads
2. SPA checks auth via `/api/me`
3. Unauthenticated → Lobby component
4. User clicks SSO button → `/auth/login/{provider}`
5. OAuth callback → redirects to `/`
6. Authenticated → Production environment (AppContent)

---

## Architecture

```
FastAPI Backend
├── /                    → Serve React SPA (handles own auth state)
├── /api/me              → Auth check endpoint
├── /auth/login/*        → OAuth initiation
├── /auth/callback/*     → OAuth callback
├── /auth/logout         → Session termination
├── /api/v1/projects/*   → REST: list, create, get, update, archive, delete
├── /api/v1/intake/*     → REST + SSE: concierge intake workflow
├── /api/v1/production/* → REST + SSE: production line status
├── /api/v1/admin/workbench/*    → Read-only config browsing
├── /api/v1/admin/workspaces/*   → Workspace-scoped editing + commit
├── /assets/*            → SPA static assets (JS, CSS)
└── /admin/*             → Jinja2 templates (legacy)

React SPA (Vite)
├── src/
│   ├── App.jsx
│   ├── components/
│   │   ├── admin/
│   │   │   ├── AdminWorkbench.jsx       # Three-panel layout
│   │   │   ├── DocTypeBrowser.jsx       # Sidebar with doc types, roles, templates, workflows
│   │   │   ├── PromptEditor.jsx         # Tab-based editor (incl. Workflow tab)
│   │   │   ├── RoleEditor.jsx
│   │   │   ├── TemplateEditor.jsx
│   │   │   ├── GitStatusPanel.jsx
│   │   │   └── workflow/
│   │   │       ├── StepWorkflowEditor.jsx    # Orchestration workflow editor
│   │   │       ├── WorkflowEditorContent.jsx # Reusable React Flow canvas
│   │   │       ├── WorkflowEditor.jsx        # Thin wrapper (standalone)
│   │   │       ├── WorkflowCanvas.jsx
│   │   │       ├── WorkflowNode.jsx
│   │   │       ├── NodePropertiesPanel.jsx
│   │   │       └── EdgePropertiesPanel.jsx
│   │   ├── ProjectTree.jsx
│   │   ├── Floor.jsx
│   │   └── ConciergeIntakeSidecar.jsx
│   ├── hooks/
│   │   ├── useAuth.jsx
│   │   ├── useWorkspace.js
│   │   ├── useWorkflowEditor.js
│   │   ├── useAdminWorkflows.js         # Fetches orchestration workflows
│   │   └── ...
│   ├── api/
│   │   ├── client.js
│   │   └── adminClient.js
│   └── utils/
│       └── workflowTransform.js         # React Flow ↔ workflow JSON
└── dist/
```

---

## Key Technical Decisions

1. **SPA at Root** — SPA served for all users, handles its own auth state
2. **Lobby Boundary** — No production UI components shared with lobby
3. **Document Production vs Orchestration Workflows** — Graph-based (ADR-039) for per-document production, step-based (workflow.v1) for cross-document orchestration
4. **Orchestration steps are declarative** — Steps declare what document to produce, not how (role/task belong on production workflow)
5. **@dnd-kit for drag-to-reorder** — Modern React DnD, supports nested sortable contexts
6. **Workspace-scoped CRUD** — Workflow create/delete goes through workspace service for Git-branch isolation

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
- Change "Produces" field in orchestration step editor to a dropdown of available document production workflows
- Clean up existing software_product_development definition.json to remove role/task_prompt from steps
- Consider updating workflow.v1 schema to reflect orchestration-only concerns
- Commit the large uncommitted changeset

### Cleanup Tasks
- Delete unused `spa/src/components/LoginPage.jsx`
- Remove Zone.Identifier files (Windows metadata)
