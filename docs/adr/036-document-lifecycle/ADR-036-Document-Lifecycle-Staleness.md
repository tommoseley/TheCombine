# ADR-036: Document Lifecycle & Staleness Semantics

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-01-12 |
| **Decision Type** | Governance / Semantics Freeze |
| **Related ADRs** | ADR-033 (Render Model), ADR-034 (Document Composition) |

---

## Context

The Combine supports asynchronous, incremental document generation across multiple document types (Discovery, Epic Backlog, Story Backlog, Architecture, etc.).

Asynchronous generation introduces observable document states (e.g., partial results, in-progress generation, outdated dependencies). These states already exist in practice, but their meaning and handling are not explicitly governed, creating risk of future regressions (e.g., blocking UI, forced regeneration, data loss).

This ADR formalizes the document lifecycle semantics that the system already exhibits and freezes their interpretation.

---

## Decision

The Combine defines a document lifecycle model with explicit, non-destructive states.
These states are semantic, not procedural, and do not mandate new infrastructure.

### Canonical Document States

| State | Definition |
|-------|------------|
| `missing` | No document exists for the requested type + parameters |
| `generating` | Document generation has been initiated but is not complete |
| `partial` | Some sections or child elements exist; others are pending or intentionally ungenerated |
| `complete` | All expected sections are present |
| `stale` | Document exists but is potentially out of date due to upstream changes |

A document may transition through multiple states over its lifetime.

### State Transition Diagram

```
missing → generating → partial ←→ complete → stale
                ↑          ↑                    │
                │          │                    │
                └──────────┴─── regenerate ─────┘
```

### Transition Semantics

| From | To | Trigger |
|------|----|---------|
| `missing` | `generating` | User initiates generation |
| `generating` | `partial` | First section completes (multi-section docs) |
| `generating` | `complete` | All sections complete (single-section docs) |
| `partial` | `generating` | User requests additional sections |
| `partial` | `complete` | All expected sections now exist |
| `complete` | `partial` | New expected content added (e.g., new epic) but not yet generated |
| `complete` | `stale` | Upstream document changed |
| `stale` | `generating` | User initiates regeneration |
| `partial` | `stale` | Upstream document changed |

---

## Frozen Semantics

### 1. Non-Blocking Visibility (Hard Rule)

Documents must remain viewable in all states except `missing`.

- `generating` and `partial` documents are rendered
- The viewer must not block navigation while generation is in progress
- The UI may indicate state, but must not suppress content

### 2. Partial Is a First-Class Outcome (Clarified)

**`partial` is not just a transitional state—it is a valid, potentially permanent outcome.**

A document is `partial` when:
- Generation is in progress (transitional)
- User chose selective generation (intentional terminal state)
- New content was added but not yet generated

**Examples of intentional `partial`:**

| Scenario | Result |
|----------|--------|
| User generates stories for Epic 1 only | Story Backlog is `partial` |
| User generates only MVP epic stories | Story Backlog is `partial` |
| User adds Epic 6 to a complete Epic Backlog | Story Backlog becomes `partial` |

**Rules:**
- Sections appear as they become available
- Missing sections are omitted (not replaced with placeholders)
- `partial` documents may persist indefinitely
- `partial` is a valid answer to "is this document ready?" (Yes, for what exists)

### 3. Staleness Is Informational, Not Destructive

A `stale` document:
- Remains fully renderable
- Is not auto-deleted
- Is not auto-regenerated
- Does not block downstream documents

**Staleness is a signal, not a command.**

### 4. Upstream Changes Do Not Cascade Destruction

When an upstream document changes (e.g., Discovery → Epic Backlog → Story Backlog):
- Downstream documents may be marked `stale`
- Downstream documents must not be cleared or invalidated
- Regeneration is always explicit and user-initiated

### 5. Regeneration Is Always Explicit

The system never regenerates documents implicitly.

**Valid regeneration triggers:**
- User action (e.g., "Generate", "Generate All", "Regenerate")
- Explicit command endpoints

**Invalid triggers:**
- Viewing a document
- Navigating the tree
- Detecting staleness

---

## Staleness Propagation (Informational)

When a document is saved, downstream dependents MAY be marked `stale`.

| Document Type | Depends On |
|--------------|------------|
| `epic_backlog` | `project_discovery` |
| `story_backlog` | `epic_backlog` |
| `technical_architecture` | `epic_backlog` |

This dependency graph is implementation guidance, not a frozen contract. The graph may be extended without amending this ADR.

---

## Non-Goals

This ADR explicitly does not:

- Define a workflow engine
- Introduce a state machine implementation
- Require new database tables
- Mandate background job orchestration
- Specify UI affordances (icons, colors, labels)
- Define error/failure states (failures preserve last valid state)

Those concerns are implementation details, governed elsewhere.

---

## Rationale

This decision:

- Reflects existing system behavior
- Protects against common async UX failures (blocking, flicker, data loss)
- Enables long-running, boredom-resistant workflows
- Preserves user trust in generated artifacts
- Supports incremental, parallel generation at scale
- Respects user intent (selective generation is valid)

---

## Consequences

### Positive

- Async generation is safe, predictable, and user-visible
- Partial progress is preserved and valued
- Users can generate selectively without the system "completing" their work
- Future refactors cannot silently reintroduce blocking behavior

### Negative / Tradeoffs

- Some documents may be visibly out of date
- Users must make explicit decisions about regeneration
- UI must tolerate mixed states
- "Complete" requires knowing what "all sections" means (defined by docdef)

These tradeoffs are intentional.

---

## Compliance

Any future change that:

- Blocks viewing during generation
- Deletes downstream documents automatically
- Forces synchronous regeneration
- Hides partial results
- Auto-completes partial documents without user action

**violates ADR-036** and requires a superseding ADR.

---

## Final Note

ADR-036 does not introduce new behavior.
It acknowledges reality and prevents the system from backsliding into synchronous, destructive workflows.

**Partial is not broken. Partial is honest.**
