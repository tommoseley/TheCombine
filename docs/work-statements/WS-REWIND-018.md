# WS-REWIND-018 — Rewind Summary Panel

**Status:** Draft
**Parent WP:** WP-REWIND-004
**Governing ADR:** ADR-063

## Objective

After a rewind, show a summary panel indicating what changed, what became stale, and where regeneration must resume from.

## Scope

### In Scope
- Summary panel component showing:
  - What triggered the rewind (reason, stage)
  - Which documents became stale (list with types and titles)
  - Where regeneration should start (active rewind point)
  - "Regenerate" action button (calls regeneration endpoint)
- Display after rewind completes
- Display when pipeline has stale documents (persistent indicator)

### Out of Scope
- Diff between stale and regenerated versions
- Historical rewind timeline
- Automatic regeneration

## Procedure

### Step 1: Create rewind summary component
- React component: `RewindSummary`
- Props: rewind result (from API), stale document list
- Sections: trigger reason, affected documents, next action

### Step 2: Show after rewind action
- After successful rewind, show summary panel inline in pipeline view
- Highlight the rewind point in the stage progression

### Step 3: Persistent stale indicator
- When project has stale documents, show a warning banner
- Banner includes: "Pipeline has stale documents from [stage]. Regeneration required."
- Link to rewind summary for details

### Step 4: Regenerate action
- "Regenerate from [stage]" button in summary panel
- Calls `POST /api/v1/projects/{project_id}/regenerate`
- Refreshes view on completion

### Step 5: Write tests
- Test: summary shows correct rewind reason
- Test: stale documents listed correctly
- Test: regenerate button calls correct API
- Test: persistent banner appears when stale docs exist

## Verification Criteria
- Summary panel displays all required information after rewind
- Persistent indicator visible when stale documents exist
- Regenerate action triggers correct API call
- Panel updates after regeneration completes

## Allowed Paths
- spa/src/components/RewindSummary.jsx
- spa/src/components/ (integration)
- spa/src/api/

## Prohibited Actions
- Do not implement diff views
- Do not implement automatic regeneration
- Do not build historical timeline
