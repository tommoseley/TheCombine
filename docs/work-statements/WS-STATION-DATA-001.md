# WS-STATION-DATA-001: Data-Driven Station Display

## Status: ✅ Complete (All Phases)

## Context

Station dots in the production floor UI were hardcoded in frontend code (`STATION_IDS = ['pgc', 'asm', 'draft', 'qa', 'done']`). This violated the config-first principle and guaranteed drift as DCW shapes evolve.

## Objective

Make station display data-driven from DCW definitions via an event-driven architecture. Nodes broadcast their station identity and state changes. The UI reacts to events without knowing workflow structure.

---

## Phase 1: ✅ Complete (Foundation)

**Backend (`app/domain/workflow/plan_models.py`):**
- Added `StationMetadata` dataclass with id, label, order
- Added `station: Optional[StationMetadata]` field to `Node`
- Added `get_stations()` method to `WorkflowPlan` - returns ordered station list
- Added `get_node_station()` method - looks up station for a node (including internal nodes)

**Backend (`app/api/services/production_service.py`):**
- Replaced hardcoded `_build_station_sequence()` with `_build_station_sequence_from_workflow()`
- Added `_get_workflow_plan()` helper to load workflow definitions

**Frontend:**
- `spa/src/utils/constants.js` - Removed `STATION_IDS`
- `spa/src/api/transformers.js` - Removed `STATION_LABELS`, simplified `buildStations()`
- `spa/src/components/Floor.jsx` - Removed hardcoded stations from optimistic update
- `spa/src/data/factories.js` - Made `createStations()` parameterized (test-only)

**Workflow Definitions (combine-config):**
- `concierge_intake/releases/1.4.0/definition.json` - Added station metadata (intake → draft → qa → done)
- `project_discovery/releases/2.0.0/definition.json` - Added station metadata (pgc → draft → qa → done)
- `technical_architecture/releases/2.0.0/definition.json` - Added station metadata (pgc → draft → qa → done)

---

## Phase 2: ✅ Complete (Backend Event Emission)

**Backend (`app/domain/workflow/plan_executor.py`):**

Added import:
```python
from app.api.v1.routers.production import publish_event
```

Added helper methods:
- `_emit_stations_declared()` - Emits full station list on workflow start
- `_emit_station_changed()` - Emits state change for specific station

Event emission points:
1. **start_execution()** - Emits `stations_declared` with all stations as "pending"
2. **start_execution()** - Emits `station_changed` for entry node as "active"
3. **_handle_result()** - On node advance to different station:
   - Emits `station_changed` for old station as "complete"
   - Emits `station_changed` for new station as "active"
4. **_handle_result()** - On terminal state:
   - Emits `station_changed` for current station as "complete"
   - Emits `station_changed` for "done" station as "complete"
5. **_handle_result()** - On routing failure:
   - Emits `station_changed` for current station as "blocked"

---

## Phase 3: ✅ Complete (Frontend Event Handling)

**Frontend (`spa/src/hooks/useProductionStatus.js`):**

Added event handlers that apply state directly without refetching:

```javascript
// stations_declared - initializes station list for a track
eventSource.addEventListener('stations_declared', (event) => {
    const { document_type, stations } = JSON.parse(event.data);
    // Adds track if missing, or updates existing track's stations
});

// station_changed - updates single station state
eventSource.addEventListener('station_changed', (event) => {
    const { document_type, station_id, state } = JSON.parse(event.data);
    // Updates specific station's state in the track
});
```

Key behaviors:
- `stations_declared` creates track if it doesn't exist (handles race with initial fetch)
- `station_changed` gracefully handles missing stations array
- Neither event triggers `fetchStatus()` - state is applied directly

---

## Event Contract

### stations_declared (on workflow start)
```json
{
  "event": "stations_declared",
  "data": {
    "document_type": "project_discovery",
    "execution_id": "exec-123",
    "stations": [
      {"id": "pgc", "label": "PGC", "order": 1, "state": "pending"},
      {"id": "draft", "label": "DRAFT", "order": 2, "state": "pending"},
      {"id": "qa", "label": "QA", "order": 3, "state": "pending"},
      {"id": "done", "label": "DONE", "order": 4, "state": "pending"}
    ]
  }
}
```

### station_changed (on state transition)
```json
{
  "event": "station_changed",
  "data": {
    "document_type": "project_discovery",
    "execution_id": "exec-123",
    "station_id": "pgc",
    "state": "active",
    "phase": "entry"
  }
}
```

**Station states:** `pending | active | complete | blocked`
**Phase values (optional):** `pass_a | entry | merge | generating | evaluating | remediating`

---

## Verification

1. **Start Project Discovery** → `stations_declared` fires → UI shows PGC/DRAFT/QA/DONE all pending
2. **PGC begins** → `station_changed {pgc, active}` → PGC turns amber
3. **Answers submitted, PGC completes** → `station_changed {pgc, complete}` → PGC turns green
4. **Generation starts** → `station_changed {draft, active}` → DRAFT turns amber
5. **Generation completes** → `station_changed {draft, complete}` → DRAFT turns green
6. **QA starts** → `station_changed {qa, active}` → QA turns amber
7. **QA passes** → `station_changed {qa, complete}`, `station_changed {done, complete}` → All green

---

## Files Modified

| Phase | File | Change |
|-------|------|--------|
| 1 | `app/domain/workflow/plan_models.py` | StationMetadata, station field, get_stations() |
| 1 | `app/api/services/production_service.py` | Workflow-driven station derivation |
| 1 | `spa/src/utils/constants.js` | Removed STATION_IDS |
| 1 | `spa/src/api/transformers.js` | Removed STATION_LABELS |
| 1 | `combine-config/workflows/*/definition.json` | Station metadata on nodes |
| 2 | `app/domain/workflow/plan_executor.py` | Event emission on state changes |
| 3 | `spa/src/hooks/useProductionStatus.js` | Handle station events directly |

---

## Prohibited

- Do not have UI derive stations from workflow structure
- Do not require UI to understand internal node relationships
- Do not poll for station state — events push state changes
- Do not call `fetchStatus()` for station events — apply directly