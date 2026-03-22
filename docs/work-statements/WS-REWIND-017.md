# WS-REWIND-017 — Status Badges

**Status:** Draft
**Parent WP:** WP-REWIND-004
**Governing ADR:** ADR-063

## Objective

Expose current / stale / superseded status as visual badges on documents in binder and document views.

## Scope

### In Scope
- Status badge component: current (green), stale (amber/warning), superseded (grey)
- Display on document cards in pipeline view
- Display in binder document list
- Display on individual document detail view

### Out of Scope
- Status filtering UI (handled by query layer)
- Badge click actions
- Version history navigation

## Procedure

### Step 1: Create status badge component
- React component: `StatusBadge` with props: status ('current' | 'stale' | 'superseded')
- Visual: green chip for current, amber/warning chip for stale, grey chip for superseded
- Accessible: includes aria-label

### Step 2: Wire into document views
- Pipeline stage cards: show badge next to document title
- Binder table of contents: show badge next to each document entry
- Document detail view: show badge in header

### Step 3: API integration
- Document API responses already include `status` field
- No new API calls needed — just render the existing field

### Step 4: Write tests
- Test: badge renders correct color for each status
- Test: badge appears in pipeline view
- Test: badge appears in binder view
- Test: accessible labels present

## Verification Criteria
- Three distinct visual states for current/stale/superseded
- Badges visible wherever documents are listed
- No additional API calls required
- Accessible

## Allowed Paths
- spa/src/components/StatusBadge.jsx
- spa/src/components/ (integration)

## Prohibited Actions
- Do not add click actions to badges (deferred)
- Do not implement version navigation
