# PROJECT_STATE.md

**Last Updated:** 2026-02-01
**Updated By:** Claude (Lobby & Authentication)

## Current Focus

**COMPLETE:** React SPA Lobby and Authentication Integration

The React SPA now has full authentication integration:
- Lobby component for unauthenticated users (strict boundary enforcement)
- OAuth SSO with Google and Microsoft
- User management in bottom-left sidebar
- SPA served at root URL for all users

### Recent Commits
- `314599c` - feat(spa): Lobby - strict boundary enforcement
- `d1fbe31` - feat(spa): Factory Gates authentication and user management
- `80880cd` - feat(spa): Add app logos to favicon, sidebar, and loading screens

---

## Lobby Specification

The lobby is outside the factory. Nothing is moving. Nothing is being built.
It exists only to explain the nature of the system and to control entry.
Crossing the login boundary is crossing into production.

### Requirements Implemented
| Requirement | Description |
|-------------|-------------|
| LOBBY-01 | Identity only: "THE COMBINE" + tagline |
| LOBBY-02 | SSO entry points only (Google, Microsoft) |
| LOBBY-03 | Zero production terminology or UI components |
| LOBBY-UX-01 | Minimal interaction (SSO + legal links) |
| LOBBY-UX-02 | No animations, no status indicators |
| LOBBY-UX-03 | Enterprise access terminal tone |

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
├── /assets/*            → SPA static assets (JS, CSS)
├── /logo-*.png          → Logo assets
└── /admin/*             → Jinja2 templates (unchanged)

React SPA (Vite)
├── src/
│   ├── App.jsx                    # Lobby vs Production routing
│   ├── components/
│   │   ├── ProjectTree.jsx        # Sidebar with archive filter
│   │   ├── Floor.jsx              # Production line + project info
│   │   ├── ConciergeIntakeSidecar.jsx
│   │   └── concierge/             # Intake sub-components
│   ├── hooks/
│   │   ├── useAuth.jsx            # Auth context and state
│   │   ├── useProjects.js         # With includeArchived option
│   │   ├── useConciergeIntake.js
│   │   └── useTheme.js
│   ├── api/
│   │   └── client.js              # All API methods + CSRF handling
│   └── styles/
│       └── themes.css
└── dist/                          # Production build
```

---

## Key Technical Decisions

1. **SPA at Root** - SPA served for all users, handles its own auth state
2. **Lobby Boundary** - No production UI components shared with lobby
3. **SSE over Polling** - User preference, cleaner real-time updates
4. **Archive before Delete** - Project governance requirement
5. **User Bottom-Left** - Standard AI application pattern

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

The SPA is feature-complete for authentication and basic project management:
- Lobby enforces strict boundary (no production leakage)
- OAuth SSO working with Google and Microsoft
- User management accessible from bottom-left
- Production environment loads after successful auth

### Next Work
Continue to solidify the user experience.

### Cleanup Tasks
- Delete unused `spa/src/components/LoginPage.jsx`
- Remove Zone.Identifier files (Windows metadata)
