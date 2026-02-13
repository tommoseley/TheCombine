# Production Line UI Vision - Subway Map

Created: 2026-01-27
Context: Session discussion about dependency visualization for Production Line

## The Vision: Industrial Execution Dashboard

The Production Line is not just a list of documents - its a live factory floor
visualization showing the assembly line in action.

## Core Concept: Subway Map Topology

Instead of a linear list, the Production Line renders as a converging track
topology (like a subway map) that shows:

1. Document dependencies as tracks - lines connect documents showing flow
2. Join gates - where multiple tracks must converge
3. Station stops per document - each doc has 4-5 stations (PGC, ASM, QA, REM, DONE)
4. Real-time animation - stations light up as the document progresses

## The Full Dependency Graph

```
concierge_intake
       |
project_discovery
       |
+------+------+
|             |
epic_backlog  tech_arch
|             |
+------+------+
       |
     Epic  <-- JOIN GATE: needs both epic_backlog AND tech_arch
       |
    Feature
       |
     Story
       |
     Task
```

With multiple Epics running in parallel:

```
+===========+
|  Epic 1   |--o-o-o-o-o  (each o is a station)
+===========+
|  Epic 2   |--o-o-o-o-o
+===========+
|  Epic 3   |--o-o-o-o-o
+===========+
```

## Station Stops (Per Document Track)

Each document track shows its progression through generation:

```
project_discovery  o---*---*---*---o
                  PGC ASM QA  REM DONE
```

Legend:
- o = pending/waiting (empty)
- * = complete (filled)
- @ = active/pulsing (currently executing)

## Stations

- PGC - Pre-Generation Clarification (binding inputs, user questions)
- ASM - Assembly (LLM generation)
- QA  - Quality Audit (validation)
- REM - Remediation (if QA fails, loops back to ASM)
- DONE - Stabilized (complete)

## Generate All Animation Flow

When user clicks Generate All:

1. First track (concierge_intake already stabilized) shows green line
2. project_discovery track activates:
   - PGC station pulses while gathering inputs
   - ASM station pulses during LLM generation
   - QA station pulses during validation
   - REM station pulses if remediation needed
   - DONE station fills green when stabilized
3. Connector line to next tracks energizes (gray to green/indigo)
4. Parallel tracks (epic_backlog, tech_arch) both start
5. JOIN GATE waits for both to complete before Epic tracks unlock
6. Epic tracks spawn and run in parallel
7. Each Epics Features spawn and run
8. Continue down to Stories and Tasks

The whole tree gradually fills with light as the factory runs.

## Visual States

| State | Visual | Description |
|-------|--------|-------------|
| Stabilized | Solid green node + green line | Complete, locked |
| Queued | Gray node | Dependencies met, waiting to start |
| Active | Pulsing indigo + station animation | Currently generating |
| Blocked | Hollow gray + amber border | Waiting on upstream |
| Join Gate | Symbol + multiple input lines | Waiting on ALL deps |
| Halted | Red node + stop icon | Error or operator needed |
| Awaiting Operator | Amber pulse | Needs user input |

## Dark Mode Control Room Aesthetic

The Production Line uses a dark theme (slate-900 background) to:
- Create visual distinction from rest of app (operations center)
- Allow track colors to pop (green, indigo, amber, red)
- Support the industrial factory floor metaphor
- Reduce eye strain during long generation runs

## Implementation Notes

Current state (2026-01-27):
- Basic React component with SSE connection exists
- Tracks show document_type, name, description, state
- Start Production button triggers single document build
- Missing: Station visualization, track connectors, join gates, animation

Files to modify:
- app/web/templates/production/line_react.html - Main React component
- app/api/services/production_service.py - Add station info to tracks
- app/domain/workflow/production_state.py - Station enum already exists

## Data Contract (needed)

```json
{
  "document_type": "project_discovery",
  "state": "assembling",
  "stations": [
    {"id": "pgc", "state": "complete"},
    {"id": "asm", "state": "active"},
    {"id": "qa", "state": "pending"},
    {"id": "rem", "state": "pending"},
    {"id": "done", "state": "pending"}
  ],
  "depends_on": ["concierge_intake"],
  "blocks": ["epic_backlog", "technical_architecture"]
}
```

## Mockups

See dependency_mockups.html (created this session) for static mockups.
Option C (Subway Map) is the target vision.

---

Key Insight: The Production Line IS the product differentiator.
This is what makes The Combine Industrial AI - you literally watch the factory run.
