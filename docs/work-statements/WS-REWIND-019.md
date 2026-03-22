# WS-REWIND-019 — Audit/History View

**Status:** Draft
**Parent WP:** WP-REWIND-004
**Governing ADR:** ADR-063

## Objective

Provide minimal lineage visibility for rewind events and regenerated replacements in the project view.

## Scope

### In Scope
- Lineage event list component showing rewind history
- For each event: timestamp, actor, reason, affected stages, affected document count
- Accessible from project view (e.g., "History" tab or section)
- Call `GET /api/v1/projects/{project_id}/lineage` endpoint

### Out of Scope
- Graph/tree visualization of lineage
- Version-to-version diff
- Filtering or search within lineage
- Export lineage to external format

## Procedure

### Step 1: Create lineage list component
- React component: `LineageHistory`
- Fetches from `/api/v1/projects/{project_id}/lineage`
- Renders timeline of events: rewinds, regenerations
- Each event shows: timestamp, actor, reason, stage, affected count

### Step 2: Wire into project view
- Add "History" section or tab to project detail view
- Load lineage events on mount

### Step 3: Event detail expansion
- Click on an event to expand: show list of affected document types
- No navigation to individual documents (deferred)

### Step 4: Write tests
- Test: lineage list renders events in chronological order
- Test: event details show correct fields
- Test: empty state when no rewind events exist
- Test: expansion shows affected document types

## Verification Criteria
- Lineage events visible in project view
- Events show all required fields
- Chronological ordering correct
- Empty state handled gracefully

## Allowed Paths
- spa/src/components/LineageHistory.jsx
- spa/src/components/ (integration)
- spa/src/api/

## Prohibited Actions
- Do not implement graph visualization
- Do not build diff/comparison views
- Do not add export functionality
