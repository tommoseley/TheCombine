# WS-SUBWAY-MAP-001: Production Line Subway Map Implementation

**Created:** 2026-01-27
**Status:** Draft - Pending Acceptance
**Scope:** Multi-commit (5 phases)
**Related:** ADR-043, docs/PRODUCTION_LINE_VISION.md, docs/THE_COMBINE_VISION.md

## Objective

Transform the Production Line UI from a simple document list into a Subway Map visualization showing dependency topology, station progression, and real-time generation animation.

## Approach

Hybrid implementation: Build complete UX with mock data first, then wire to backend.

## Design Decisions

Resolved during WS drafting:

| Question | Decision | Rationale |
|----------|----------|-----------|
| Station labels | Defer to Phase 2 | See what fits visually |
| Elapsed time per track | Likely yes, defer | Async execution may make this complex |
| Mobile view | Desktop-first, responsive later | Focus on core UX now |
| Connector lines | Try both straight and curved | Curved more organic, evaluate in Phase 1-2 |
| Layout location | Dedicated execution panel | Full page /production route, not sidebar widget |

## Gemini Refinements (Incorporated)

1. **Blocker Clarity (Phase 1):** Blocked state shows "Awaiting: [doc_ids]" text explicitly
2. **Draft Available State (Phase 2):** Add visual state between ASM and QA so user can preview document while QA runs
3. **Heartbeat/Latency Warning (Phase 4):** If SSE silent beyond threshold, pulse changes to "lagging" indicator
4. **Partial Generation (Phase 5):** Generate All only triggers remaining unstabilized tracks

---

## Phases

### Phase 1: Static Subway Map Layout

**Goal:** Render the dependency graph with connector lines and join gates using mock data.

**Deliverables:**
- Standalone HTML/React prototype: `docs/prototypes/subway-map-prototype.html`
- Dark theme "control room" aesthetic (slate-900 background)
- Dependency graph layout:
  - concierge_intake -> project_discovery
  - project_discovery -> epic_backlog (parallel branch)
  - project_discovery -> technical_architecture (parallel branch)
  - epic_backlog + technical_architecture -> story_backlog (JOIN GATE)
- Visual elements:
  - Track nodes (circles) for each document
  - Connector lines between dependent documents (try both straight and curved)
  - Join gate symbol for multi-dependency convergence
  - Document names and types displayed
  - **Blocked state shows "Awaiting: [doc_ids]" explicitly**

**Mock Data Structure:**
```javascript
const mockTracks = [
  { id: 'concierge_intake', name: 'Concierge Intake', state: 'stabilized', depends_on: [], blocked_by: [] },
  { id: 'project_discovery', name: 'Project Discovery', state: 'queued', depends_on: ['concierge_intake'], blocked_by: [] },
  { id: 'epic_backlog', name: 'Epic Backlog', state: 'blocked', depends_on: ['project_discovery'], blocked_by: ['project_discovery'] },
  { id: 'technical_architecture', name: 'Technical Architecture', state: 'blocked', depends_on: ['project_discovery'], blocked_by: ['project_discovery'] },
  { id: 'story_backlog', name: 'Story Backlog', state: 'blocked', depends_on: ['epic_backlog', 'technical_architecture'], blocked_by: ['epic_backlog', 'technical_architecture'], join_gate: true }
];
```

**Acceptance Criteria:**
- [ ] Prototype renders in browser without errors
- [ ] All 5 document tracks visible with clear dependency flow
- [ ] Connector lines show dependency relationships
- [ ] Both straight and curved connector options available for comparison
- [ ] Join gate visually distinct from single-dependency blocks
- [ ] Blocked tracks show "Awaiting: X, Y" text
- [ ] Dark theme applied consistently
- [ ] Layout has room to breathe (not cramped)

**Prohibited:**
- No backend integration
- No SSE connection
- No real data fetching

---

### Phase 2: Station Stops

**Goal:** Add the 6 station dots per track showing generation phases.

**Deliverables:**
- Station dots added to each track: PGC, ASM, DRAFT, QA, REM, DONE
- Station states: pending, complete, active, failed
- **DRAFT state:** Indicates document content available for preview while QA still running
- Color coding:
  - Pending: gray/slate (empty circle)
  - Complete: green/emerald (filled circle)
  - Active: indigo (filled, will pulse in Phase 4)
  - Draft Available: blue/cyan (clickable to preview)
  - Failed: red
- Evaluate: labels always visible vs hover-only based on visual fit

**Mock Data Addition:**
```javascript
{
  id: 'project_discovery',
  name: 'Project Discovery',
  state: 'assembling',
  stations: [
    { id: 'pgc', label: 'PGC', state: 'complete' },
    { id: 'asm', label: 'ASM', state: 'complete' },
    { id: 'draft', label: 'DRAFT', state: 'active' },  // Can preview now
    { id: 'qa', label: 'QA', state: 'pending' },
    { id: 'rem', label: 'REM', state: 'pending' },
    { id: 'done', label: 'DONE', state: 'pending' }
  ]
}
```

**Acceptance Criteria:**
- [ ] Each track shows 6 station dots (PGC, ASM, DRAFT, QA, REM, DONE)
- [ ] Station states visually distinguishable
- [ ] DRAFT state indicates "preview available" clearly
- [ ] Stations align horizontally per track
- [ ] Layout remains clean with stations added
- [ ] Decision made on labels (always visible or hover)
- [ ] Decision made on connector style (straight vs curved)

**Prohibited:**
- No animation yet
- No backend integration

---

### Phase 3: SSE Wiring

**Goal:** Connect prototype to real backend SSE events.

**Deliverables:**
- Move prototype into `app/web/templates/production/line_react.html`
- Connect to `/api/v1/production/events?project_id={id}`
- Handle SSE events:
  - `station_transition` - update station dot state
  - `track_started` - change track state to active
  - `track_stabilized` - change track state to stabilized
  - `draft_available` - enable preview link (new event)
  - `line_stopped` - show interrupt indicator
  - `production_complete` - all tracks stabilized
- Replace mock data with real API fetch on load
- Update `production_service.py` to include:
  - `depends_on` array per track
  - `blocked_by` array per track (unmet dependencies)
  - `stations` array per track (if workflow execution exists)

**Backend Changes:**
- `get_production_tracks()` returns stations array with 6 stations
- `get_production_status()` returns depends_on and blocked_by for each track
- New SSE event: `draft_available` when ASM completes
- SSE events include station-level detail

**Acceptance Criteria:**
- [ ] Page loads real track data from API
- [ ] SSE connection established on page load
- [ ] Station transitions reflected in UI without refresh
- [ ] Track state changes reflected in UI
- [ ] Draft available state enables document preview
- [ ] Console logs confirm events received
- [ ] Blocked tracks show actual blocker names

**Prohibited:**
- No animation yet (static state updates only)

---

### Phase 4: Animation

**Goal:** Add visual feedback for active stations, track completion, and latency awareness.

**Deliverables:**
- Pulse animation for active stations (CSS @keyframes)
- "Energize" effect on connector lines when upstream track completes:
  - Gray -> Green/Indigo transition
  - Glow effect
- Join gate "unlocks" animation when all inputs ready
- Smooth transitions between states (CSS transitions)
- **Heartbeat monitoring:** If SSE silent > threshold (e.g., 30s), active station changes to "lagging" pulse (amber/warning)

**CSS Additions:**
```css
@keyframes pulse-normal {
  0%, 100% { opacity: 1; box-shadow: 0 0 8px rgba(99, 102, 241, 0.6); }
  50% { opacity: 0.7; box-shadow: 0 0 4px rgba(99, 102, 241, 0.3); }
}

@keyframes pulse-lagging {
  0%, 100% { opacity: 1; box-shadow: 0 0 8px rgba(245, 158, 11, 0.6); }
  50% { opacity: 0.5; box-shadow: 0 0 4px rgba(245, 158, 11, 0.3); }
}

.station-active { animation: pulse-normal 1.5s ease-in-out infinite; }
.station-lagging { animation: pulse-lagging 1s ease-in-out infinite; }

.connector-energized {
  stroke: #10b981;
  filter: drop-shadow(0 0 4px rgba(16, 185, 129, 0.5));
  transition: all 0.5s ease;
}
```

**Acceptance Criteria:**
- [ ] Active station pulses visibly (normal pulse)
- [ ] Lagging state triggers after SSE silence threshold
- [ ] Connector lines animate when track stabilizes
- [ ] Join gate shows unlock animation
- [ ] Animations are smooth, not jarring
- [ ] Performance acceptable (no jank)

**Prohibited:**
- No new backend changes (SSE heartbeat/keepalive already exists)

---

### Phase 5: Generate All

**Goal:** Single button triggers full production line orchestration for remaining tracks.

**Deliverables:**
- "Generate All" button in UI header
- Button calls `POST /api/v1/production/start?project_id={id}`
- **Partial generation support:** Only triggers tracks not yet stabilized
- UI shows immediate feedback (button disabled, "Starting...")
- Tree progressively lights up as SSE events arrive
- Error handling if generation fails
- Completion state when all tracks stabilized
- Button text changes based on state:
  - "Generate All" (nothing started)
  - "Continue Generation" (partial progress)
  - "Complete" (all stabilized, disabled)

**Interaction Flow:**
1. User clicks "Generate All" (or "Continue Generation")
2. Button shows loading state
3. Backend identifies first track(s) with met dependencies
4. Stations pulse through PGC -> ASM -> DRAFT -> QA -> (REM if needed) -> DONE
5. Track stabilizes, connector energizes
6. Next tracks start (parallel where possible)
7. Join gates wait for all inputs
8. Process continues until complete or interrupted

**Acceptance Criteria:**
- [ ] Generate All button visible and functional
- [ ] Partial generation works (skips already-stabilized tracks)
- [ ] Button text reflects current state
- [ ] Full line orchestration triggers correctly
- [ ] UI updates in real-time as generation progresses
- [ ] Completion state clearly shown
- [ ] Errors displayed if generation fails
- [ ] Can navigate away and return to see current state

**Prohibited:**
- None - full integration expected

---

## File Inventory

**New Files:**
- `docs/prototypes/subway-map-prototype.html` (Phase 1-2)

**Modified Files:**
- `app/web/templates/production/line_react.html` (Phase 3-5)
- `app/api/services/production_service.py` (Phase 3)
- `app/api/v1/routers/production.py` (Phase 3, 5)
- `app/domain/workflow/production_state.py` (Phase 3 - add DRAFT state if needed)

**Test Files:**
- Manual browser testing for Phases 1-2
- Integration testing for Phases 3-5

---

## Success Criteria

When complete:
1. User sees dependency graph as subway map
2. Each document track shows station progression (6 stations)
3. Blocked tracks explicitly show what they are waiting for
4. Draft available state allows early preview
5. Real-time updates via SSE with latency awareness
6. Animations provide "factory running" feedback
7. Generate All triggers full/partial orchestration
8. UI matches vision in docs/PRODUCTION_LINE_VISION.md

---

## Execution Authorization

This Work Statement requires explicit acceptance before execution begins.

Phase 1 may begin upon acceptance. Subsequent phases require Phase N-1 completion.
