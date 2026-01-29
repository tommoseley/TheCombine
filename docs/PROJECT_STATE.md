# PROJECT_STATE.md

**Last Updated:** 2026-01-29
**Updated By:** Claude (Subway Map v6 - Modular with Manifold Routing)

## Current Focus

Subway Map visualization prototype (v6) complete with modular architecture and industrial manifold routing. Ready for backend integration.

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

**Architecture Decisions:**
- Modular code organization with MODULE comment sections
- Factory functions for consistent node creation
- Dagre handles L1 (spine) ONLY - vertical layout
- L2 epics manually positioned in grid (3 per row) below Epic Backlog
- Waypoint junction nodes for T-junction manifold routing
- Straight edges for vertical spine, smoothstep for horizontal branches
- L3+ content (features, stories) uses Side-Car pattern

**Code Organization (MODULE sections in index.html):**
```
Line  38: data/constants.js      - COLORS, GRID, TRAY configs
Line  51: data/factories.js      - createDocument, createEpic, createStations, createQuestions
Line  74: data/projectData.js    - initialData with 13 epics
Line 103: utils/layout.js        - Dagre + grid layout + manifold routing
Line 165: components/nodes/StationDots.jsx
Line 189: components/sidecars/QuestionTray.jsx
Line 221: components/sidecars/FeatureGrid.jsx
Line 251: components/nodes/DocumentNode.jsx
Line 399: components/nodes/WaypointNode.jsx
Line 413: App.jsx                - Main component
```

**Grid Configuration:**
```javascript
GRID = {
    EPICS_PER_ROW: 3,
    EPIC_WIDTH: 220,
    EPIC_HEIGHT: 70,
    EPIC_GAP_X: 50,
    EPIC_GAP_Y: 100,
    EPIC_OFFSET_X: 80,
    EPIC_OFFSET_Y: 80
}
```

**Manifold Routing:**
- WaypointNode: Invisible 1x1px junction for routing
- One junction per row at SPINE_X position
- Vertical spine: straight edges (eliminates gaps)
- Horizontal branches: smoothstep with borderRadius: 20

**What's Implemented:**
- Vertical L1 spine with TB Dagre layout
- L2 epics in 3-column grid with row wrapping
- Industrial manifold routing (T-junctions via waypoint nodes)
- Questions side-car (amber) for operator input
- Features side-car (indigo) for L3 content
- Node headers ("DOCUMENT", "EPIC") with color-coded borders
- Collapse/expand with feature count badge
- Factory functions for clean data creation
- 13 epics, 115 features in test data

**What's NOT Implemented (Next Session):**
- SSE wiring to backend ProductionService
- Real data integration (currently mock data)
- "Generate All" button functionality
- Animation cascade/stagger timing
- Feature click -> drill into stories

## Key Files

**Prototype:**
- docs/prototypes/subway-map-v6/index.html (current)
- docs/prototypes/subway-map-v6/data/*.js (reference modules)
- docs/prototypes/subway-map-v6/components/**/*.jsx (reference components)
- docs/prototypes/subway-map-v6/utils/layout.js (reference)

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

## Work Statement Status

WS-ADR-043-001 Production Line - Phase 7 UI in progress
- Basic React component with SSE: DONE
- Track display with descriptions: DONE
- Subway Map visualization prototype: DONE (v6 with manifold routing)
- Backend integration: TODO
- Station animation: TODO
- Generate All flow: TODO

## Handoff Notes for Next Session

1. **Start by opening** docs/prototypes/subway-map-v6/index.html in browser to see current state
2. **Key prototype features to understand:**
   - L1 spine is vertical via Dagre
   - L2 epics are in 3-column grid (manually positioned, not Dagre)
   - Waypoint junctions create clean T-junction routing
   - Click any node to cycle state (queued -> active -> stabilized)
   - Click "X features" button on epics to open Features side-car
   - Click "Answer Questions" on active nodes with input required
3. **Factory functions simplify data creation:**
   - createDocument(id, name, desc, state, intent, options)
   - createEpic(id, name, state, intent, featureNames)
   - createStations(activeStation)
   - createQuestions(questions)
4. **Next steps:**
   - Wire SSE to get real document states from backend
   - Replace mock `initialData` with data from ProductionService
   - Test with actual project data
5. **Grid can be configured:**
   - Change EPICS_PER_ROW for different column counts
   - Adjust GRID constants for spacing