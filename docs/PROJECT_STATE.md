# PROJECT_STATE.md

**Last Updated:** 2026-01-31
**Updated By:** Claude (React SPA Branding)

## Current Focus

**COMPLETE:** React SPA with Concierge Intake, Project Management, and Branding

The React SPA now has full project lifecycle management and branding:
- Concierge intake sidecar with SSE-based generation progress
- Project rename (inline edit in Project Info block)
- Project archive/unarchive (toggle button)
- Project delete (requires archive first)
- Archive filter toggle in project list sidebar
- App logos in favicon, sidebar header, and loading screens

### Recent Commits
- `80880cd` - feat(spa): Add app logos to favicon, sidebar, and loading screens
- `7ac0635` - feat(spa): React SPA with concierge intake and project management

---

## React SPA Status

**Location:** `spa/` directory

### Features Complete
- ProjectTree sidebar with project selection highlighting
- Floor component with Production Line status and Project Info block
- Theme switching (Industrial, Light, Blueprint)
- Concierge intake sidecar with chat interface
- SSE-based generation progress (replaced polling)
- Project management: rename, archive/unarchive, delete
- Archive filter in sidebar (default off)
- Delete requires archive first (enforced in UI)
- Selected project scrolls into view after operations

### API Endpoints Added
- `PATCH /api/v1/projects/{id}` - Update project name/description
- `POST /api/v1/projects/{id}/archive` - Archive project
- `POST /api/v1/projects/{id}/unarchive` - Restore archived project
- `DELETE /api/v1/projects/{id}` - Soft delete (requires archive first)
- `POST /api/v1/intake/start` - Start intake workflow
- `GET /api/v1/intake/{id}` - Get intake state
- `POST /api/v1/intake/{id}/message` - Submit user message
- `PATCH /api/v1/intake/{id}/field/{key}` - Update interpretation field
- `POST /api/v1/intake/{id}/initialize` - Lock and start generation
- `GET /api/v1/intake/{id}/events` - SSE for generation progress

---

## Architecture

```
FastAPI Backend
├── /api/v1/projects/*   → REST: list, create, get, update, archive, delete
├── /api/v1/intake/*     → REST + SSE: concierge intake workflow
├── /api/v1/production/* → REST + SSE: production line status
├── /admin/*             → Jinja2 templates (unchanged)
└── /*                   → Serve React SPA static files

React SPA (Vite)
├── src/
│   ├── components/
│   │   ├── App.jsx              # Main app with state management
│   │   ├── ProjectTree.jsx      # Sidebar with archive filter
│   │   ├── Floor.jsx            # Production line + project info
│   │   ├── ConciergeIntakeSidecar.jsx
│   │   ├── DocumentNode.jsx
│   │   ├── FullDocumentViewer.jsx
│   │   └── concierge/           # Intake sub-components
│   ├── hooks/
│   │   ├── useProjects.js       # With includeArchived option
│   │   ├── useConciergeIntake.js
│   │   ├── useProductionStatus.js
│   │   └── useTheme.js
│   ├── api/
│   │   └── client.js            # All API methods + SSE factories
│   └── styles/
│       └── themes.css
└── dist/                        # Production build
```

---

## Key Technical Decisions

1. **SSE over Polling** - User preference, cleaner real-time updates
2. **Archive before Delete** - Project governance requirement
3. **Sorted Project Selection** - After archive/delete, select next project in visual order
4. **Scroll to Selected** - Using scrollIntoView with smooth behavior

---

## What Jinja2 Templates Become Obsolete

These are replaced by React SPA:
- app/web/templates/home.html
- app/web/templates/partials/sidebar.html
- app/web/templates/partials/project_tree.html
- app/web/templates/production/line_react.html
- app/web/templates/production/floor.html

These stay (admin):
- app/web/templates/admin/*
- app/web/templates/auth/* (if any)

---

## Quick Commands

```bash
# Run backend
cd ~/dev/TheCombine && PYTHONPATH=. python3 ops/scripts/run.py

# Run SPA dev server
cd spa && npm run dev

# Build SPA for production
cd spa && npm run build
```

---

## Handoff Notes

The SPA is feature-complete for basic project management. Next steps could include:
- Production line orchestration integration
- Document viewing and editing
- More robust error handling
- Authentication integration
