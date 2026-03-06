# WS-DEEPLINK-001: SPA Cold-Load Deep Link Resolution

**Parent:** WP-ROUTE-001 (Unified Routing v2 — routing contract complete)
**Depends on:** WP-ID-001 (complete — display_id minting), WP-ROUTE-001 (complete — URL routing contract, SPA fallback, document resolver endpoint)
**Blocks:** Pasteable/shareable URLs, agent-friendly document references

---

## Objective

Complete the last mile of ADR-056: when a user pastes a deep link URL into a fresh browser tab, the SPA must render the correct view without requiring navigation through the project list or any other intermediate screen.

---

## Context

WP-ROUTE-001 shipped the routing contract infrastructure:

- SPA fallback: FastAPI returns `index.html` for all non-API GET requests
- Universal document resolver: `GET /api/v1/projects/{project_slug}/documents/{display_id}` returns document JSON
- URL routing contract defined in ADR-056

What's missing is the last mile on the SPA side: React Router v7 is installed and declarative routes are defined in `App.jsx`, but some manual `pathname.includes()` matching remains (e.g., line 74 of App.jsx for Work Binder detection). Cold-load resolution works for project selection via `useParams()` but Work Binder child document resolution (WS→parent WP) is not yet wired for cold load.

---

## Scope

**In scope:**

- Remove remaining manual `pathname.includes()` matching in App.jsx — replace with declarative route hooks
- Complete cold-load resolution for Work Binder child documents (WS→parent WP via `parent_document_id`)
- Handle error states: invalid project_id → 404 page, invalid display_id → 404 page
- Ensure browser back/forward navigation works between views
- Ensure programmatic navigation (e.g., clicking a document in the Work Binder) updates the URL

**Out of scope:**

- New API endpoints (document resolver already exists from WP-ROUTE-001)
- API route consolidation (`/work-binder/` → `/api/v1/work-binder/` migration is a separate WS)
- Updating `ROUTING_CONTRACT.md` v1 → v2 content (separate doc WS)

---

## Prohibited

- Do not add new API endpoints — use the existing document resolver and project endpoints
- Do not modify backend routing or the SPA fallback handler
- Do not break existing navigation flows — all current click-based navigation must continue to work
- Do not introduce server-side rendering (SSR) — this is client-side routing only

---

## Steps

### Phase 1: Remove Manual Pathname Matching

**Step 1.1: Replace manual pathname matching**

React Router v7 is already installed and routes are defined in `App.jsx`. Remove remaining `pathname.includes()` calls (e.g., line 74 of App.jsx for Work Binder auto-expand detection). Replace with `useMatch()` or `useLocation()` from React Router.

**Existing route tree (already defined in App.jsx, verify complete):**

```
/                                           → Lobby (project selector)
/projects/:projectId                        → Project dashboard
/projects/:projectId/docs/:displayId        → Document viewer
/projects/:projectId/work-binder            → Work Binder
/projects/:projectId/work-binder/:displayId → WB focused on document
/projects/:projectId/production             → Production floor
/admin                                      → Admin panel
/admin/workbench                            → Admin workbench
/admin/executions/:executionId              → Execution detail
```

### Phase 2: Cold-Load Resolution

**Step 2.1: Project resolution on cold load**

When the SPA loads with a URL like `/projects/HWCA-001/docs/PD-001`:

1. Parse `HWCA-001` from the URL
2. Fetch project data from API (e.g., `GET /api/v1/projects/HWCA-001` or equivalent)
3. Set project context in application state
4. If project not found → render 404 page within SPA

**Step 2.2: Document resolution on cold load**

After project resolution:

1. Parse `PD-001` from the URL
2. Fetch document data from `GET /api/v1/projects/HWCA-001/documents/PD-001`
3. Render the document viewer with the fetched data
4. If document not found → render 404 page within SPA

**Step 2.3: Work Binder resolution on cold load**

For `/projects/HWCA-001/work-binder/WP-001`:

1. Resolve project (Step 2.1)
2. Resolve document (Step 2.2) — WP-001 resolves via display_id prefix to `work_package`
3. Open Work Binder with WP-001 selected

For `/projects/HWCA-001/work-binder/WS-003`:

1. Resolve project
2. Resolve WS-003 → find parent WP via `parent_document_id`
3. Open Work Binder with parent WP selected and WS-003 expanded

### Phase 3: Navigation Integration

**Step 3.1: URL updates on navigation**

When a user clicks a document, WP, or WS within the SPA:

- The URL must update to reflect the new view (e.g., clicking WP-001 in Work Binder changes URL to `/projects/HWCA-001/work-binder/WP-001`)
- Use `pushState` (via router library) — not full page reloads

**Step 3.2: Back/forward navigation**

Browser back and forward buttons must navigate between previously visited views within the SPA. The router library handles this if properly configured.

**Step 3.3: Loading states**

Cold-load resolution requires async fetches. Show appropriate loading indicators while project and document data are being fetched. Do not flash a 404 before data loads.

### Phase 4: Error Handling

**Step 4.1: 404 page**

Create a simple 404 component rendered within the SPA when:

- Project slug doesn't match any project
- Display ID doesn't resolve to a document in the project

The 404 page should suggest navigating to the Lobby (`/`).

**Step 4.2: Network error handling**

If API calls fail (500, timeout, network error), show an error state with a retry option. Do not render 404 for transient failures.

### Phase 5: Verify

**Step 5.1:** Cold-load each route in ADR-056 section 2 by pasting the URL directly into a fresh browser tab. Each must render the correct view.

**Step 5.2:** Navigate between views using the SPA UI. Verify URL updates on each navigation action.

**Step 5.3:** Use browser back/forward buttons to navigate between views. Verify correct view rendering.

**Step 5.4:** Test 404 handling: paste a URL with an invalid project slug, paste a URL with an invalid display_id.

**Step 5.5:** Refresh the browser on any deep-linked page. Verify the page re-renders correctly (not redirected to Lobby).

---

## Allowed Paths

```
spa/src/
spa/dist/
```

---

## Verification

- [ ] Pasting `/projects/HWCA-001/docs/PD-001` in a fresh tab renders the PD document
- [ ] Pasting `/projects/HWCA-001/work-binder/WP-001` in a fresh tab renders the Work Binder with WP-001 selected
- [ ] Pasting `/projects/HWCA-001/work-binder/WS-003` in a fresh tab resolves to parent WP and shows WS-003
- [ ] Pasting `/projects/INVALID/docs/PD-001` shows 404 page
- [ ] Pasting `/projects/HWCA-001/docs/INVALID-999` shows 404 page
- [ ] Clicking a document in the UI updates the URL bar
- [ ] Browser back/forward navigates between previously visited views
- [ ] Browser refresh on any deep-linked page re-renders the same view
- [ ] All existing navigation flows continue to work (no regressions)
- [ ] No manual `pathname.includes()` matching remains in the SPA codebase

---

_Draft: 2026-03-06_
