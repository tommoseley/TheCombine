# WS-PIPELINE-002: Floor Layout Redesign (Master-Detail)

## Status: Complete

## Parent Work Package: WP-PIPELINE-001

## Governing References

- ADR-050 -- Work Statement Verification Constitution
- POL-WS-001 -- Work Statement Standard
- docs/branding/design-principles.md -- Calm Authority, Spatial Over Temporal

## Verification Mode: A

## Allowed Paths

- spa/src/
- app/web/templates/production/
- app/web/routes/
- app/api/
- tests/

---

## Objective

Replace the full-canvas ReactFlow floor with a master-detail layout. The pipeline becomes a compact vertical rail of selectable nodes (the master). Clicking a node mounts its content in a large detail panel (the detail). The Work Binder is the last node in the rail; its detail view is the workbench grid for managing WPs and WSs.

This eliminates 70% wasted screen space, removes action buttons from node cards, and makes the Work Binder a natural extension of the pipeline rather than a separate screen.

---

## Preconditions

- WS-PIPELINE-001 is complete (new pipeline structure, single IP, execution_mode on steps)
- Floor.jsx exists at spa/src/components/Floor.jsx
- DocumentNode.jsx exists at spa/src/components/DocumentNode.jsx
- FullDocumentViewer.jsx exists for document rendering

---

## Current State

The floor uses ReactFlow as a full-width canvas. Document nodes are large cards (approx 340px wide) arranged vertically with edges between them. Each card contains: document type label, status dot + state text, description text, station dots (progress), and action buttons ("View Document", "Start Production").

The canvas takes the full center region. ~70% of the screen is empty space around the vertical chain of cards. Document viewing requires the FullDocumentViewer overlay or a sidecar.

---

## Target State

### Layout

```
+-------------+----------------+----------------------------------+
| Project     | Pipeline Rail  | Content Panel                    |
| Tree        | (compact)      | (detail view)                    |
| (existing)  |                |                                  |
|             | [CI] selected  | Document content / Workbench     |
|             | [PD]           | grid / "Start Production" etc.   |
|             | [IP]           |                                  |
|             | [TA]           |                                  |
|             | [WB]           |                                  |
+-------------+----------------+----------------------------------+
```

### Pipeline Rail (Master)

- Fixed-width column (~200-240px)
- Each node is a compact card:
  - Document type label (short)
  - Status dot + state
  - Station dots (if applicable)
  - Selected state highlight (border or background)
- No action buttons on cards. No description text.
- Click selects. Selected node highlighted. Content mounts in detail panel.
- First node auto-selected on load.
- Edges between nodes shown as simple connector lines (no ReactFlow overhead, could be pure CSS/SVG).

### Content Panel (Detail)

- Takes remaining width (~60-70% of viewport)
- Content depends on selected node type:
  - **Document nodes** (CI, PD, IP, TA): Mount the document viewer (existing FullDocumentViewer or IA-driven renderer). If document doesn't exist yet, show "Start Production" button + context.
  - **WB node**: Mount the Workbench view.
- Single content region. No overlay, no sidecar.

### Work Binder Detail View (when WB node selected)

Minimum v1:

- **Header**: "Work Binder" + project code
- **Candidate WPs section**: Read-only list from IP output. Each shows: candidate ID, title, scope summary. "Create Work Packages" button triggers LLM generation of governed WPs from candidates + TA.
- **Governed WPs section**: Table/grid of created WPs. Columns: WP ID (monospace), Title, TA Binding, Provenance, WS Count, State (dot + label).
- **Per-WP interaction**: Click a governed WP row to see its details + WS list. "Create Work Statements" button on each WP.
- **Filters**: All / Candidate / Governed. By state.

### Routing

- `/project/:id` -- default view, first pipeline node selected
- State preserved via URL params or component state: `?node=technical_architecture`
- No separate /workbench route needed -- WB is just a node selection

---

## Scope

### In Scope

1. Replace ReactFlow canvas in Floor.jsx with master-detail layout
2. Create PipelineRail component (compact node column)
3. Create ContentPanel component (detail region, content switching)
4. Create WorkBench component (WB detail view with WP/WS management)
5. Adapt DocumentNode.jsx into compact RailNode (or create new component)
6. Mount existing document viewers in ContentPanel
7. Handle "Start Production" as content panel action (not node card button)
8. Handle node selection state (click to select, auto-select first on load)
9. WB detail: display candidate WPs from IP, display governed WPs
10. WB detail: "Create WPs" button (calls backend to generate WPs)
11. WB detail: "Create WSs" button per WP (calls backend to decompose)
12. WP provenance stamping: source_ip_version, generated_by: llm
13. Theme support (Industrial, Light, Blueprint) on new layout

### Out of Scope

- LLM-assisted "Bind" button (TA component auto-binding)
- User-authored WPs
- WP editing after creation
- Drag-and-drop WP reordering
- WS execution UI
- Real-time SSE updates for WP/WS state changes (can be added later)
- Mobile responsive layout

---

## Tier 1 Verification Criteria

### Layout Structure

1. Floor component renders a two-column layout (rail + content), not a ReactFlow canvas
2. Rail renders one node per pipeline step in correct order
3. Clicking a rail node updates selected state
4. Content panel renders different content based on selected node type
5. First node is auto-selected on component mount

### Node Cards (Rail)

6. Rail nodes do NOT contain "View Document" buttons
7. Rail nodes do NOT contain "Start Production" buttons
8. Rail nodes show: label, status dot, state text
9. Selected rail node has visual highlight

### Content Panel

10. Selecting a document node mounts document viewer with correct document
11. Selecting WB node mounts WorkBench component
12. "Start Production" appears in content panel when document doesn't exist yet

### Work Binder

13. WorkBench component renders candidate WPs section (from IP)
14. WorkBench component renders governed WPs section
15. "Create Work Packages" button exists and calls backend
16. Governed WP rows show: WP ID, Title, State
17. "Create Work Statements" button exists per governed WP
18. WP creation stamps provenance (source_ip_version, generated_by)

### Theme

19. Rail and content panel respect theme CSS variables
20. All three themes (Industrial, Light, Blueprint) render without errors

---

## Procedure

### Phase 1: Layout Shell

1. Create PipelineRail component
   - Accepts pipeline steps data
   - Renders compact node cards
   - Manages selected state
   - Emits onSelect callback

2. Create ContentPanel component
   - Accepts selected node data
   - Switches between document viewer and workbench based on node type

3. Refactor Floor.jsx
   - Replace ReactFlow with PipelineRail + ContentPanel side by side
   - Preserve project header, theme cycling, SSE connection
   - Wire selection state

### Phase 2: Document Content Integration

4. Mount existing FullDocumentViewer (or IA renderer) inside ContentPanel for document nodes
5. Move "Start Production" from DocumentNode into ContentPanel's empty state
6. Ensure document viewing works for all existing types (CI, PD, IP, TA)
7. Verify station dots / progress still visible (in rail card)

### Phase 3: Work Binder

8. Create WorkBench component
   - Fetch candidate WPs from IP document content
   - Fetch governed WPs from backend (GET /api/v1/projects/:id/work-packages)
   - Render candidate list (read-only) and governed grid

9. Wire "Create Work Packages" button
   - POST to backend endpoint (triggers LLM WP generation)
   - On success, refresh governed WPs list
   - WP records include provenance: { generated_by: "llm", source_ip_version: "..." }

10. Wire "Create Work Statements" button per WP
    - POST to backend endpoint (triggers LLM WS decomposition)
    - On success, refresh WS count for that WP

### Phase 4: Polish & Verify

11. Theme support on all new components
12. Auto-select first node on load
13. Handle edge cases: no documents yet, production in progress, errors
14. All Tier 1 tests pass
15. Tier 0 returns zero

---

## API Endpoints Needed

These may already exist. Audit before creating.

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/v1/projects/:id/work-packages | List governed WPs |
| POST | /api/v1/projects/:id/work-packages/generate | Trigger LLM WP generation |
| GET | /api/v1/projects/:id/work-packages/:wpId/work-statements | List WSs for a WP |
| POST | /api/v1/projects/:id/work-packages/:wpId/work-statements/generate | Trigger LLM WS decomposition |

---

## Prohibited Actions

- Do not remove ReactFlow as a dependency (workflow diagrams inside TA still use it)
- Do not modify pipeline config (that is WS-PIPELINE-001)
- Do not modify document type schemas or prompts
- Do not implement WP editing, reordering, or user-authored WPs
- Do not implement the Bind button (TA auto-binding)

---

## Design Guidance

Refer to docs/branding/ for design tokens, typography, and component patterns.

- **Rail nodes**: Use --bg-node background, --border-node border. Selected state uses --accent or increased border weight.
- **Content panel**: Use --bg-canvas background.
- **Workbench grid**: Monospace font for WP IDs per typography.md. State dots use --state-* variables.
- **Transitions**: No clever animations. Content panel swaps on click. Fade-in acceptable (0.2s max).
- **Density**: Rail is compact (small type scale). Content panel is spacious (standard type scale).

---

_End of WS-PIPELINE-002_
