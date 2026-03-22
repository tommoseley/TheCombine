# ADR-063 — Pipeline Rewind, Invalidation, and Regeneration Semantics

**Status:** Draft
**Date:** 2026-03-21
**Owners:** Tom / Combine Architecture

---

## 1. Context

The Combine operates as a staged, governed pipeline where downstream artifacts depend on upstream authority. As projects evolve, changes may occur after downstream artifacts have already been generated, including:

- Updates to intent or PGC answers
- Modifications to authoritative generated documents (PD, TA, etc.)
- Future user-supplied artifacts (e.g., mockups, constraints)
- Corrections identified through QA or governance processes

The system currently lacks a formal, deterministic model for:

- Identifying when downstream artifacts are no longer valid
- Determining the earliest affected pipeline stage
- Marking artifacts as stale
- Rewinding the pipeline
- Regenerating artifacts while preserving lineage

Without defined rewind semantics, the system risks silent inconsistency, broken governance, and loss of auditability.

---

## 2. Problem Statement

The Combine must support controlled change after artifact generation without violating governance or losing traceability.

The system must deterministically answer:

- What changes invalidate downstream artifacts?
- Where does invalidation begin?
- What becomes stale?
- How is regeneration performed?
- What historical state must be preserved?

---

## 3. Decision Drivers

- Deterministic pipeline behavior
- Preservation of governance and authority
- Clear lineage and auditability
- Support for future artifact-driven workflows
- Avoidance of silent drift
- Minimal user ambiguity regarding current vs stale state

---

## 4. Scope

**This ADR defines:**
- Pipeline stage ordering
- Invalidation rules
- Rewind semantics
- Regeneration behavior
- Lineage preservation
- Artifact status model

**This ADR does not define:**
- Artifact intake/upload model
- Document parsing or interpretation
- UI design beyond required state exposure

---

## 5. Canonical Pipeline Model

### 5.1 Stage Ordering (Authoritative)

The Combine pipeline is defined as:

```
CI → PD → TA → IP → WP → WS
```

- **CI:** Concierge Intake
- **PD:** Product Discovery
- **TA:** Technical Architecture
- **IP:** Implementation Plan
- **WP:** Work Package
- **WS:** Work Statement

PGC is cross-cutting and operates within stages, not between them.

---

## 6. Definitions

| Term | Definition |
|------|-----------|
| **Upstream Authority** | Any input or artifact that influences downstream generation |
| **Invalidation** | The determination that an artifact is no longer governed by current upstream authority |
| **Rewind** | Moving the pipeline's active state back to a prior stage, marking downstream artifacts stale |
| **Regeneration** | Creating new downstream artifacts based on updated upstream authority |
| **Stale Artifact** | An artifact invalidated by upstream rewind; no longer eligible for downstream use |
| **Current Artifact** | The active, authoritative artifact used for downstream progression |
| **Superseded Artifact** | A prior artifact replaced by regeneration; retained for lineage and audit |

---

## 7. Decision

### 7.1 Rewind is a first-class capability

The Combine shall support rewind as a governed architectural behavior.

### 7.2 Linear dependency model (MVP)

The pipeline is strictly linear. Rewinding to stage N invalidates all artifacts at stage N and beyond.

### 7.3 Non-destructive regeneration

Rewind shall not overwrite existing artifacts. New artifacts are created; prior artifacts are preserved.

### 7.4 Explicit staleness

Invalidated artifacts must be explicitly marked as stale. The system must not silently treat stale artifacts as current.

### 7.5 Regeneration produces new current artifacts

Regenerated artifacts become current; prior versions become superseded.

### 7.6 Manual and automatic triggers

Rewind may be initiated by user action or system-detected change.

### 7.7 Only current artifacts are eligible for downstream processing

Stale and superseded artifacts must not be used as inputs for generation, QA evaluation, promotion, or stabilization.

---

## 8. Invalidation Rules

### 8.1 Principle

Invalidation is based on dependency and authority, not chronology.

### 8.2 MVP Rule

Given the linear pipeline:

> Change at stage N → invalidate all artifacts at stage N and later

### 8.3 Conservative default

If impact scope is uncertain, rewind to the earliest plausible affected stage.

### 8.4 Non-destructive behavior

Invalidation changes status only; artifacts remain preserved.

---

## 9. Trigger Categories

### 9.1 Manual rewind

User explicitly rewinds pipeline to a selected stage.

### 9.2 Upstream mutation

Changes to CI, PD, TA, or other authoritative artifacts.

### 9.3 Governance correction

Changes resulting from QA findings or contradiction resolution.

### 9.4 Future artifact mutation

Addition, replacement, or removal of user-supplied authoritative artifacts.

### 9.5 Prompt, schema, or policy changes

**Do NOT trigger automatic rewind.**

Prompt, schema, and policy changes affect future generation only unless explicitly invoked by the user.

---

## 10. Regeneration Semantics

### 10.1 New artifact creation

Regeneration creates new artifacts; prior artifacts are not modified.

### 10.2 Current vs superseded

New artifacts become current; prior artifacts become superseded.

### 10.3 Downstream blocking

Stale artifacts must not be used for further pipeline progression.

### 10.4 MVP simplification

Full downstream regeneration is acceptable for MVP.

---

## 11. Lineage Requirements

The system must track:

- Source of change
- Stage of rewind
- Affected artifacts
- Prior current artifacts
- Regenerated replacement artifacts
- Timestamps and actor
- Reason for invalidation

The system must support answering:

- What changed?
- Why did it change?
- What became stale?
- What replaced it?

---

## 12. Artifact Status Model (MVP)

The system shall support the following statuses:

| Status | Definition |
|--------|-----------|
| **current** | The active, authoritative artifact used for downstream progression |
| **stale** | An artifact invalidated due to upstream rewind; no longer eligible for downstream use |
| **superseded** | A prior artifact replaced by a regenerated version; retained for lineage and audit |

**Notes:**
- "Historical" is represented by superseded artifacts
- "Regenerating" and "blocked" are execution-layer states, not document statuses
- Status transitions must be deterministic and auditable

---

## 13. Implementation Requirements

### 13.1 Document versioning

The system must support multiple versions of a document per type. Each document must include:

- Status (current / stale / superseded)
- Version or sequence identifier
- Lineage reference (what it replaced or was replaced by)

### 13.2 Non-destructive storage

Artifacts must not be overwritten in place.

### 13.3 Stage-based invalidation

Invalidation must operate at stage boundaries.

### 13.4 Stabilization revocation

Any upstream rewind must revoke stabilization status of downstream artifacts.

Example: TA rewound → all dependent WPs and WSs become unstabilized.

### 13.5 QA gating behavior

- QA gates must reject input derived from stale artifacts
- Only current artifacts are eligible for promotion and downstream execution
- Superseded artifacts remain visible for audit but are not valid inputs for QA evaluation
- Any attempt to evaluate or promote stale artifacts must result in a deterministic failure with clear reason (e.g., "artifact invalidated due to upstream rewind")

---

## 14. User Experience Requirements

The system must expose:

- Current vs stale vs superseded status
- Pipeline position
- Cause of invalidation
- Required regeneration point

Future enhancements may include:

- Rewind controls on stages
- Diff views between stale and regenerated artifacts
- Branch/thread visualization

---

## 15. Consequences

### Positive

- Deterministic handling of change
- Preserved governance and authority
- Auditability and traceability
- Foundation for artifact-aware workflows
- Reduced ambiguity in pipeline state

### Negative

- Increased system complexity
- Need for versioned document storage
- Potential user confusion if state is not clearly surfaced
- Conservative invalidation may invalidate more work than necessary

---

## 16. Alternatives Considered

| Alternative | Verdict | Reason |
|------------|---------|--------|
| No rewind (manual correction only) | Rejected | Leads to silent inconsistency |
| Destructive overwrite | Rejected | Destroys lineage |
| Always regenerate entire pipeline | MVP fallback | Acceptable for MVP but not scalable |
| Fine-grained dependency graph | Deferred | Too complex for initial implementation |

---

## 17. MVP Approach

- Linear dependency model
- Stage-level invalidation
- Conservative rewind
- Full downstream regeneration
- Explicit status tracking (current / stale / superseded)
- Versioned document storage
- QA gates enforce current-only input

---

## 18. Open Questions

- Granularity of versioning (document vs sub-document)
- Automatic vs user-confirmed regeneration
- UI for lineage visualization
- Future dependency graph evolution
- Partial regeneration support

---

## 19. Follow-On ADRs

- ADR — User-Supplied Artifact Intake and Authority
- ADR — Artifact Type, Role, and Entry Stage
- ADR — Lineage Graph and Dependency Model
- ADR — Pipeline Status UX

---

## 20. Recommendation

Adopt rewind and invalidation as a first-class Combine capability using a linear stage model and conservative semantics.

This establishes the foundation for:

- Governed evolution of artifacts
- Future artifact-aware workflows
- Deterministic pipeline behavior under change
