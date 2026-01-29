# PROJECT_STATE.md

**Last Updated:** 2026-01-29
**Updated By:** Claude (Subway Map v6 - CSS Themes + Document Viewer)

## Current Focus

Subway Map v6 prototype complete with CSS-based theming, skeuomorphic document viewer, and smooth zoom animations. Ready for backend integration and project tree simplification.

## IMPORTANT: Vision Documents

**READ THESE FIRST:**

1. docs/THE_COMBINE_VISION.md - Product vision, why we exist, the endgame
2. docs/PRODUCTION_LINE_VISION.md - Subway Map UI specification

The Production Line UI is the flagship feature - a Subway Map topology showing:
- Dependency tracks with document flow
- Join gates where multiple dependencies converge
- Station stops (PGC, ASM, QA, REM, DONE) per document
- Real-time animation as documents progress
- Generate All lights up the entire tree as the factory runs

## Subway Map Prototype Status

**Location:** docs/prototypes/subway-map-v6/index.html

### Theme System (CSS Variables)

Three themes implemented via CSS classes:
- **Industrial** (default): Deep navy #0b1120, amber active states, factory floor aesthetic
- **Light**: Clean white/gray for bright environments
- **Blueprint**: Technical drawing blue, paper-white sidecars

Theme variables control all colors:
```css
--bg-canvas, --bg-node, --bg-panel, --bg-sidecar
--text-primary, --text-muted, --text-sidecar
--state-stabilized-bg/text/edge
--state-active-bg/text/edge  
--state-queued-bg/text/edge
--action-success, --action-warning
```

Edge colors are in JS (EDGE_COLORS object) since edges are programmatic.

### Document Viewer (Skeuomorphic Paper Design)

When user clicks "View Document" on stabilized nodes:
- 520px wide paper document slides in
- Pure white background with Georgia serif fonts
- Serial number (REF: CI-2026-001)
- Section headings in small caps
- Signature line with cursive font
- "View Full Document" button at footer
- Camera zooms smoothly to focus on node+sidecar

### Sidecar Components

| Sidecar | Trigger | Color | Purpose |
|---------|---------|-------|---------|
| DocumentViewer | "View Document" | Emerald | Paper document preview |
| QuestionTray | "Answer Questions" | Amber | Operator input form |
| FeatureGrid | "X features" | Indigo | L3 feature list |

All sidecars:
- Top-aligned horizontal bridges
- Zoom-to-focus animation (single smooth movement)
- Theme-aware colors via --bg-sidecar, --text-sidecar

### Architecture Decisions

- CSS variables for theming (no prop drilling)
- Modular code with MODULE comment sections
- Factory functions for consistent node creation
- Dagre handles L1 (spine) ONLY - vertical layout
- L2 epics manually positioned in grid (3 per row)
- Waypoint junction nodes for T-junction manifold routing
- useReactFlow for programmatic camera control

### Code Organization (929 lines)

```
CSS Themes:        Lines 15-175
Constants/Data:    Lines 226-265  
Layout Utils:      Lines 267-410
QuestionTray:      Lines 481-520
FeatureGrid:       Lines 523-560
DocumentViewer:    Lines 548-645
DocumentNode:      Lines 648-750
WaypointNode:      Lines 752-760
SubwayMap (App):   Lines 765-920
```

### What's Implemented

- 3 color themes (Industrial, Light, Blueprint)
- Skeuomorphic document viewer with paper styling
- Zoom-to-focus for all sidecars
- Top-aligned horizontal bridges
- Vertical L1 spine with TB Dagre layout
- L2 epics in 3-column grid with row wrapping
- Industrial manifold routing (T-junctions)
- Questions side-car for operator input
- Features side-car for L3 content
- Intent badges only show "OPTIONAL" (mandatory is default)
- Factory functions for clean data creation
- 13 epics, 115 features in test data

## Next Steps (Immediate)

1. **Simplify Project Tree**: Remove document list from sidebar - just navigate to floor
2. **Wire Floor to Backend**: Connect SSE to ProductionService for real data
3. **Replace Mock Data**: Use actual project/document data

## Key Files

**Prototype:**
- docs/prototypes/subway-map-v6/index.html (929 lines, 55KB)

**Production Line Backend:**
- Route: app/web/routes/production.py
- Template: app/web/templates/production/line_react.html
- Service: app/api/services/production_service.py
- SSE Events: app/api/v1/routers/production.py

**Vision Docs:**
- docs/THE_COMBINE_VISION.md
- docs/PRODUCTION_LINE_VISION.md

## Technical Debt

### Sidebar Loads All Document Status
Issue: Every sidebar refresh queries document status for ALL projects.
Preferred: Lazy load only when project accordion expands.

### Prototype -> Production Migration
The v6 prototype needs to be migrated into line_react.html with:
- Real data from ProductionService instead of mock initialData
- SSE connection for state updates
- Proper React build (currently using Babel standalone)

## Handoff Notes for Next Session

1. **Open** docs/prototypes/subway-map-v6/index.html to see current state
2. **Theme toggle**: Click button in top-left panel to cycle themes
3. **Click states**: Click any node to cycle queued -> active -> stabilized
4. **Sidecars**: 
   - "View Document" on green nodes opens paper document
   - "Answer Questions" on active nodes with input
   - "X features" on epics opens feature list
5. **All sidecars zoom to focus** with smooth camera animation
6. **Next priority**: Simplify project tree, wire to backend