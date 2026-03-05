# WS-ROUTE-002: SPA Fallback + Client-Side Routing

## Status: Draft

## Parent: WP-ROUTE-001
## Governing ADR: ADR-056
## Depends On: WS-ROUTE-001
## Parallelizable With: WS-ROUTE-003

## Objective

Enable deep linking by: (1) adding a FastAPI catch-all that returns `index.html` for any non-API route, and (2) replacing the SPA's manual `window.location.pathname` matching with React Router for declarative route definitions and cold-load support.

## Scope

### In Scope

- FastAPI SPA fallback: catch-all route returning `index.html` for non-API paths
- Install `react-router-dom` in SPA
- Replace manual pathname matching in `App.jsx` with React Router `<Routes>`
- Define core SPA routes per ADR-056 section 2
- Cold-load support: direct navigation to `/projects/HWCA-001/docs/PD-001` works
- Update `home_routes.py` to use catch-all instead of individual route handlers
- SPA build must pass

### Out of Scope

- Work Binder deep linking (WS-ROUTE-004)
- API prefix consolidation (WS-ROUTE-003)
- Dead route cleanup (WS-ROUTE-005)
- Changes to existing API endpoints

## Implementation

### Step 1: Install React Router

```bash
cd spa && npm install react-router-dom
```

### Step 2: Update FastAPI SPA fallback

**File:** `app/web/routes/public/home_routes.py`

Replace individual route handlers with a single catch-all:

```python
@router.get("/{full_path:path}")
async def spa_fallback(request: Request, full_path: str):
    """Serve SPA index.html for any route not handled by API/auth/assets."""
    spa_path = Path(__file__).parent.parent.parent.parent.parent / "spa" / "dist" / "index.html"
    if spa_path.exists():
        return FileResponse(spa_path, media_type="text/html")
    # Fallback to Jinja2 template if SPA not built
    return templates.TemplateResponse("index.html", {"request": request})
```

Ensure this catch-all is mounted AFTER `/api/`, `/auth/`, and `/assets/` routes so it doesn't swallow API 404s.

**File:** `app/api/main.py`

Verify route ordering: API routers must be registered before the SPA fallback.

### Step 3: Refactor SPA routing with React Router

**File:** `spa/src/App.jsx`

Replace the manual `path` state and `popstate` listener with React Router:

```jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

function App() {
    return (
        <BrowserRouter>
            <Routes>
                {/* Public routes */}
                <Route path="/learn" element={<LearnPage />} />
                <Route path="/login" element={<Lobby />} />

                {/* Admin routes */}
                <Route path="/admin/workbench" element={<AuthGuard><AdminWorkbench /></AuthGuard>} />
                <Route path="/admin/executions/:executionId" element={<AuthGuard><AdminPanel /></AuthGuard>} />
                <Route path="/admin" element={<AuthGuard><AdminPanel /></AuthGuard>} />

                {/* Project routes */}
                <Route path="/projects/:projectId/docs/:displayId" element={<AuthGuard><DocumentView /></AuthGuard>} />
                <Route path="/projects/:projectId/work-binder/:displayId" element={<AuthGuard><WorkBinderView /></AuthGuard>} />
                <Route path="/projects/:projectId/work-binder" element={<AuthGuard><WorkBinderView /></AuthGuard>} />
                <Route path="/projects/:projectId/production" element={<AuthGuard><ProductionView /></AuthGuard>} />
                <Route path="/projects/:projectId" element={<AuthGuard><ProjectDashboard /></AuthGuard>} />

                {/* Default */}
                <Route path="/" element={<AuthGuard><AppContent /></AuthGuard>} />
                <Route path="*" element={<NotFound />} />
            </Routes>
        </BrowserRouter>
    );
}
```

### Step 4: Create wrapper components for new routes

Create thin wrapper components that extract URL params and render existing components:

**`DocumentView`**: Uses `useParams()` to get `projectId` and `displayId`, fetches document via resolver endpoint, renders `DocumentViewer` or `RenderModelViewer`.

**`WorkBinderView`**: Uses `useParams()` to get `projectId` and optional `displayId`, renders existing `WorkBinder` component with appropriate props.

**`ProjectDashboard`**: Uses `useParams()` to get `projectId`, renders existing project view (currently part of `AppContent`).

**`NotFound`**: Simple 404 page.

### Step 5: Update navigation

Replace `window.location.pathname = ...` calls with React Router's `useNavigate()`:

```jsx
const navigate = useNavigate();
navigate(`/projects/${projectId}/work-binder`);
```

### Step 6: Cold-load verification

Test that navigating directly to:
- `/projects/HWCA-001/docs/PD-001` → loads SPA → shows document
- `/projects/HWCA-001/work-binder` → loads SPA → shows Work Binder
- `/admin` → loads SPA → shows admin panel
- `/nonexistent` → loads SPA → shows 404 page

## Tier-1 Tests

No backend tier-1 tests — this is primarily a frontend change. Verification is via SPA build + manual cold-load testing.

## Allowed Paths

```
spa/src/App.jsx
spa/src/main.jsx
spa/src/components/ (new wrapper components only)
spa/package.json
spa/package-lock.json
app/web/routes/public/home_routes.py
app/api/main.py (route ordering only)
```

## Prohibited

- Do not modify existing component internal logic (only add wrappers)
- Do not modify API endpoints
- Do not modify work_binder.py (WS-ROUTE-003, WS-ROUTE-004)
- Do not remove existing routes from API (WS-ROUTE-005)
- Do not change the SPA build configuration

## Verification

- `cd spa && npm run build` succeeds
- Cold-load navigation to project/document URLs works
- Browser back/forward navigation works
- Existing routes (`/`, `/admin`, `/learn`) still work
- API routes are not swallowed by SPA fallback (test: `GET /api/v1/projects` still returns JSON, not HTML)
