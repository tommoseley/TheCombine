# ADR-043: The Production Line

## Status

**Accepted**

## Context

The Combine transforms user intent into structured artifacts through multi-step, multi-agent workflows. Each document (Project Discovery, Architecture, Epic Backlog, etc.) progresses through a sequence of stations: Binding, Assembly, Audit, and potentially Remediation loops.

Current UX problems:

1. **The waiting is opaque** — LLM assembly takes 30-60+ seconds. Users see a spinner with no insight into what's happening.

2. **Conversational mental model** — The current UI treats document production as a "chat" interaction rather than an industrial process.

3. **No orchestration visibility** — Users cannot see how documents relate, which are blocked, or why the line is stopped.

4. **Manual sequencing** — Users must navigate to each document, initiate production, wait, then move to the next. The dependency graph is implicit.

The Combine's value proposition is *industrial document manufacturing with governance*. The UX must reflect this.

## Decision

### 1. The Production Line is the Primary Surface

The Production Line is the real-time visualization of document manufacturing. It is the first thing operators see when they open the application.

**The test of success:**

> When operators open the app and think "Let's see how the line is doing" — we've won. That's not a chatbot. That's a system.

**Design principles:**

- **Visible Production** — The system explains its work by showing exactly which station is active
- **Progressive Disclosure** — High-level project tracks by default; station detail revealed when active
- **Industrial Authority** — Monospaced metadata, status stamps, elapsed timers reinforce production semantics
- **Operator Agency** — When the line stops, it's because *you are needed*, not because something broke

### 2. Production States (Canonical)

All UI, logs, and APIs use these terms exclusively. Conversational language ("generate", "retry", "failed", "error") is prohibited.

| State | Meaning | Visual |
|-------|---------|--------|
| **Queued** | Waiting to enter the line | ○ dim |
| **Binding** | Loading context, constraints, dependencies | ● pulse |
| **Assembling** | LLM constructing the artifact | ● pulse + timer |
| **Auditing** | QA validation against bound constraints | ● pulse |
| **Remediating** | Self-correction cycle in progress | ● amber + loop arrow |
| **Stabilized** | Artifact passed audit, production complete | ● green ✓ |
| **Blocked** | Upstream dependency incomplete | ○ locked |
| **Awaiting Operator** | Line stopped; operator input required | ● red + alert |
| **Halted** | Circuit breaker tripped; requires review | ● red + stop |
| **Escalated** | Operator reviewed halt, accepted outcome without resolution | ● gray + checkmark |

**Invariant: The system never waits silently.**

Every pause in production must be attributable to one of:
- An active station (Binding, Assembling, Auditing, Remediating)
- An operator interrupt (Awaiting Operator)
- A declared dependency (Blocked)
- A terminal state (Stabilized, Halted, Escalated)

If a user sees a spinner with no explanation, that is a UX regression and a violation of this doctrine.

**State transitions:**

```
Queued → Binding → Assembling → Auditing → Stabilized
                                    ↓
                              Remediating ←┘ (loop max 2)
                                    ↓
                                 Halted → Escalated (operator accepts)
```

### 3. Three-Layer Visualization

#### Layer 1: Project Tracks (The Mainline)

The vertical backbone shows all documents required for the project.

```
Project: Math Assessment App
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

concierge_intake     ●━━━━━━━━━━━━━━━━━━━━━━● Stabilized

project_discovery    ●━━━━━━━━━━━━━━━━━━━━━━● Auditing [12s]

epic_backlog         ○────────────────────────○ Blocked
tech_architecture    ○────────────────────────○ Blocked

story_backlog        ○────────────────────────○ Queued
```

#### Layer 2: Station Sequence (Branch Map)

When a track is active, it expands to show internal stations:

```
project_discovery    ●━━━●━━━●━━━●━━━●━━━●━━━● Auditing
                    bind asm  aud rem  aud
                      ✓   ✓   ✗   ✓   ▶ [12s]
                              ↩━━━┘
```

**Stations:**

| Station | Activity |
|---------|----------|
| **bind** | Loading constraints from intake, PGC answers, upstream documents |
| **asm** | LLM assembling the artifact |
| **aud** | Semantic and structural audit against bound constraints |
| **rem** | Remediation cycle (self-correction) |

The remediation loop is visualized as a curve back to assembly. This normalizes self-correction as a quality feature, not a failure.

#### Layer 3: Fan-Out (Parallel Tracks)

When a document spawns multiple children (e.g., Epic Backlog → Stories):

```
epic_backlog         ●━━━━━━━━━━━━━━━━━━━━━━● Stabilized
                     ├─ story_001  ●━━━━━━━● Auditing [8s]
                     ├─ story_002  ●━━━━━━━● Stabilized
                     ├─ story_003  ●━━━●━━━● Remediating
                     └─ [+12 more] ━━━━━━━━━ 8/15 Stabilized
```

**Batch rule:** 15+ sub-documents collapse into a summary rail with progress count.

**Attention focusing rule:** At most one remediating child auto-expands at a time. This keeps operator attention on where the system is "hurting" without noise from parallel healthy tracks.

### 4. Production Controls

#### Per-Document: [Start Production]

Each queued document shows a **[Start Production]** button:

```
☑ concierge_intake   Stabilized
☐ project_discovery  [Start Production]
☐ epic_backlog       Blocked (awaiting project_discovery)
```

#### Project-Level: [Run Full Line]

A project-level **[Run Full Line ▶]** button initiates complete production:

1. Traverses the dependency graph
2. Starts each document as its dependencies stabilize
3. Pauses only for Operator Interrupts
4. Other tracks continue while one awaits operator
5. Completes when all documents reach `Stabilized` or `Halted`

```
[Run Full Line ▶]  |  Progress: 3/7 Stabilized  |  Active: 2  |  Awaiting Operator: 1
```

### 5. Operator Interrupt Contract

When the line requires human input, production enters **Awaiting Operator** state.

**The framing is critical:**

> "The line is stopped because you are needed."

This reinforces operator agency. The system is not broken, stuck, or confused. It has reached a decision point that requires human judgment.

#### Interrupt Surface

```
┌─────────────────────────────────────────────────────────────┐
│  ⚠️  LINE STOPPED: epic_backlog awaiting operator          │
│                                                             │
│  The system needs your input to continue production.        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  How should epics be prioritized?                    │   │
│  │                                                      │   │
│  │  ○ Business value first                             │   │
│  │  ○ Technical risk first                             │   │
│  │  ○ User-facing features first                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Other tracks continue while this one awaits your input.    │
│                                                             │
│                              [Resume Production →]          │
└─────────────────────────────────────────────────────────────┘
```

#### Interrupt Types

| Type | Trigger | Resolution |
|------|---------|------------|
| **Clarification Required** | PGC identifies gaps that need operator input | Answer questions |
| **Audit Review** | Circuit breaker tripped after max remediation | Approve, override, or escalate |
| **Constraint Conflict** | Bound constraints cannot be simultaneously satisfied | Resolve conflict |

#### Interrupt Behaviors

- Interrupt appears inline on the Production Line, not a page navigation
- Other tracks continue producing while one awaits operator
- Operator can defer ("Answer Later") — track stays paused, line continues
- After resolution, track auto-resumes from where it stopped
- Interrupts are logged for audit trail

### 6. Watching the Line

The Production Line is designed for continuous observation. It answers:

- "What's happening right now?"
- "Why is that document taking so long?"
- "What's blocking the architecture doc?"
- "When will the project be ready?"

#### Default View (Line Status)

When nothing is running:

```
Production Line: Idle

All 7 documents Stabilized
Last production run: 2026-01-26 12:40:44 (2 hours ago)

[Run Full Line ▶]  [View Documents]
```

#### Active View (Production Running)

When production is active:

```
Production Line: Active

┌──────────────────────────────────────────────────────────┐
│ concierge_intake     ●━━━━━━━━━━━━━━━━━━● Stabilized     │
│ project_discovery    ●━━━●━━━●━━━●━━━━━━● Auditing [8s]  │
│ epic_backlog         ○────────────────────○ Blocked       │
│ tech_architecture    ○────────────────────○ Blocked       │
└──────────────────────────────────────────────────────────┘

Active: project_discovery at Auditing station
Next: epic_backlog, tech_architecture (parallel, on stabilization)
```

#### Station Drill-Down

Clicking any station reveals production telemetry:

- **bind**: Constraints loaded, upstream documents referenced
- **asm**: LLM run ID, token count, elapsed time, assembled prompt hash
- **aud**: Semantic QA report, constraint coverage, findings
- **rem**: Feedback provided, correction applied

Links to existing admin views for full detail.

### 7. Real-Time Updates

The Production Line uses Server-Sent Events (SSE) to push state transitions:

```
Event: station_transition
Data: {
  "execution_id": "exec-406b58908188",
  "document_type": "project_discovery",
  "state": "Auditing",
  "station": "aud",
  "elapsed_ms": 8234,
  "retry_count": 1
}

Event: line_stopped
Data: {
  "execution_id": "exec-789abc",
  "document_type": "epic_backlog",
  "reason": "clarification_required",
  "interrupt_id": "int-456def"
}
```

The UI updates immediately on:
- Station transitions
- State changes
- Operator interrupts
- Production completion
- Circuit breaker trips

### 8. URL Structure

```
/production                              # Production Line (primary surface)
/production?project={id}                 # Specific project
/production?project={id}&focus={doc}     # With track expanded
/production/fullscreen                   # Full-page for complex runs
```

The Production Line is:
- The default landing page after login
- Accessible from any page via persistent sidebar/header element
- Where [Run Full Line] navigates to automatically

## Consequences

### Positive

1. **Visible work** — Operators understand production status at a glance
2. **Industrial mental model** — Reinforces The Combine as a production system, not a chatbot
3. **Operator agency** — Interrupts frame the operator as essential, not a bottleneck
4. **Parallel awareness** — See all active production, not one document at a time
5. **Natural drill-down** — Click any station for full telemetry
6. **Efficient orchestration** — [Run Full Line] eliminates manual sequencing

### Negative

1. **Frontend complexity** — Real-time multi-track visualization requires careful state management
2. **SSE infrastructure** — New endpoint and connection management
3. **Language migration** — Existing code/logs use "generate/retry/failed" terminology

### Neutral

1. **Existing admin views remain** — Production Line links to them for detail
2. **Document viewer unchanged** — Operators can still view completed documents directly

## Implementation Notes

### Terminology Migration

Replace throughout codebase:

| Old | New | User-Facing Phrasing |
|-----|-----|----------------------|
| generate, generation | assemble, assembly | "Start Production", "Assembling..." |
| retry, retry_count | remediation, remediation_count | "Remediating (1/2)" |
| failed, failure | audit_rejected, halted | "Audit rejected", "Halted" |
| success | stabilized | "Stabilized" |
| pending | queued, blocked | "Queued", "Blocked" |
| paused | awaiting_operator | "Awaiting operator" |
| error | halted | "Halted" |
| (new) | escalated | "Escalated" |

### Required Backend Work

1. **SSE endpoint** — `/api/v1/production/events?project={id}`
2. **Project orchestrator** — Coordinates executions based on dependency graph
3. **Interrupt registry** — Tracks pending operator interrupts
4. **State aggregator** — Real-time production status for all project documents

### Required Frontend Work

1. **Production Line component** — Track visualization with stations
2. **Operator Interrupt modal** — Inline resolution without navigation
3. **Auto-expand behavior** — Tracks expand when entering active state
4. **Full-screen mode** — For fan-out scenarios
5. **Idle/Active states** — Different presentations based on line activity

### Data Already Available

- `workflow_executions.execution_log` — Full station history
- `workflow_executions.state` — Current position, remediation counts
- `documents` table — Stabilization status per document type
- `document_types` — Dependency graph

## References

- ADR-042: Constraint Binding & Cross-Node Drift Enforcement
- ADR-041: Prompt Assembly
- ADR-010: LLM Execution Logging
