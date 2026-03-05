# WS-ROUTE-004: Work Binder Deep Linking

## Status: Draft

## Parent: WP-ROUTE-001
## Governing ADR: ADR-056
## Depends On: WS-ROUTE-002, WS-ROUTE-003

## Objective

Enable deep linking within the Work Binder. The route `/projects/{project_id}/work-binder/{display_id}` opens the WB with the specified document selected. Both WP and WS display_ids are supported — a WS display_id resolves to its parent WP.

## Scope

### In Scope

- Work Binder component reads `displayId` from URL params (via React Router)
- On mount with `displayId`: resolve document type from prefix, auto-select the WP or WS
- WS resolution: WS-003 → find parent WP via `parent_document_id` → select WP → expand WS
- URL updates when user selects a different WP or WS (`navigate()` call)
- Back/forward navigation within WB
- `/docs/{display_id}` route works for WB documents too (flat document view)

### Out of Scope

- SPA routing setup (WS-ROUTE-002 — already done)
- API consolidation (WS-ROUTE-003 — already done)
- Dead route cleanup (WS-ROUTE-005)
- Changes to WB layout or styling

## Implementation

### Step 1: Update WorkBinderView wrapper

**File:** `spa/src/components/WorkBinder/WorkBinderView.jsx` (created in WS-ROUTE-002)

Read `displayId` from URL params and pass to WorkBinder:

```jsx
import { useParams } from 'react-router-dom';

function WorkBinderView() {
    const { projectId, displayId } = useParams();
    return <WorkBinder projectId={projectId} initialDisplayId={displayId} />;
}
```

### Step 2: Add deep link resolution to WorkBinder

**File:** `spa/src/components/WorkBinder/index.jsx`

On mount, if `initialDisplayId` is provided:

1. Parse prefix from display_id
2. If prefix is `WP` → select that WP directly
3. If prefix is `WS` → fetch WS document → read `parent_document_id` → find parent WP → select WP → mark WS as expanded
4. If prefix is `WPC` → select that candidate

```jsx
useEffect(() => {
    if (!initialDisplayId) return;

    const prefix = initialDisplayId.split('-')[0];
    if (prefix === 'WP') {
        setSelectedWpId(initialDisplayId);
    } else if (prefix === 'WS') {
        // Fetch WS, find parent WP, select it, expand WS
        resolveWsToParentWp(initialDisplayId);
    } else if (prefix === 'WPC') {
        setSelectedCandidateId(initialDisplayId);
    }
}, [initialDisplayId]);
```

### Step 3: URL updates on selection

**File:** `spa/src/components/WorkBinder/index.jsx`

When the user selects a WP or WS, update the URL:

```jsx
import { useNavigate } from 'react-router-dom';

const navigate = useNavigate();

const handleSelectWp = (wpId) => {
    setSelectedWpId(wpId);
    navigate(`/projects/${projectId}/work-binder/${wpId}`, { replace: true });
};
```

Use `replace: true` so each selection doesn't add a history entry (user can still go back to exit WB).

### Step 4: Add WS parent resolution to API client

**File:** `spa/src/api/client.js`

If not already available, add a method to fetch a single document by display_id:

```javascript
getDocumentByDisplayId: (projectId, displayId) =>
    request(`/projects/${projectId}/documents/${displayId}`),
```

This uses the resolver endpoint from WS-ROUTE-001.

## Tier-1 Tests

No backend tests — this is a frontend-only change. Verification is via SPA build + manual testing.

## Allowed Paths

```
spa/src/components/WorkBinder/index.jsx
spa/src/components/WorkBinder/WorkBinderView.jsx
spa/src/api/client.js
```

## Prohibited

- Do not modify WB layout, styling, or existing functionality
- Do not modify backend routes
- Do not add new API endpoints
- Do not modify App.jsx routes (WS-ROUTE-002)

## Verification

- `/projects/HWCA-001/work-binder/WP-001` → opens WB with WP-001 selected
- `/projects/HWCA-001/work-binder/WS-003` → opens WB with parent WP selected, WS-003 expanded
- `/projects/HWCA-001/work-binder/WPC-001` → opens WB with WPC-001 selected
- Selecting a different WP updates URL
- Browser back button returns to previous selection
- `/projects/HWCA-001/work-binder` (no display_id) → opens WB with no selection (current behavior)
- SPA build passes
