# ADR-067 — Lineage Path Restoration and Thread Management

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-03-28 |
| **Origin** | APAM-003 investigation — rewind threads accumulate, no mechanism to restore or prune |
| **Contributors** | Tom, GPT, Claude |

---

## 1. Problem

The system supports pipeline rewind (ADR-063), but lacks mechanisms to:

- View full history of document versions and rewind/restore events
- Restore a prior checkpoint as the new authoritative state
- Archive discarded rewind threads

Rewind introduces branching history. Without path management:

- History becomes cluttered
- Operators cannot promote a previously valid chain
- Downstream artifacts remain ambiguous relative to authority

---

## 2. Decision

Introduce **lineage-path restoration** and **thread management** as governed, first-class operations.

---

## 3. Core Principles

- **Restoration unit = lineage path**, not individual documents
- **Restore is append-only** — no history is erased
- **Thread deletion is soft-archive** — hidden from normal use, audit retained
- **Restore must preview downstream impact** before confirmation
- **Authority is path-scoped** — restoring a path restores its authority context

---

## 4. Key Concepts

### Lineage Path

A lineage path is the maximal set of documents connected by lineage edges where:

- Each document's lineage chain (`source_document_id`) traces to a selected checkpoint
- No document is invalidated due to upstream changes

### Active Path

The currently authoritative lineage path for the project.

### Checkpoint

A specific historical document version used as a restore anchor.

### Thread

A branch of history defined by:

- A rewind or restore event as its root
- All descendant artifacts until another rewind/restore diverges the path

### Thread Archive

A soft-deleted thread that:

- Is excluded from normal navigation and restore
- Retains an audit stub

---

## 5. Restore Semantics

When restoring to a checkpoint:

### 5.1 Path Selection

- Identify the lineage path containing the checkpoint
- Include only downstream artifacts derived from the same lineage branch
- Exclude artifacts from other branches

### 5.2 Promotion

- Promote the selected path to the active authoritative path
- Mark all documents in that path as current according to stage rules
- Demote previously active documents to superseded or stale

### 5.3 Authority Restoration

- Authority records are scoped to lineage paths
- Restoring a path implicitly restores the authority context associated with that path

### 5.4 Append-Only Event

- Create a restore event in lineage history
- Do not overwrite or delete any prior artifacts

### 5.5 Validation

#### v1 (Advisory)

The system SHOULD evaluate and surface the following conditions before restore:

- Documents in the path with known schema or QA issues
- Missing upstream artifacts
- Gaps or breaks in lineage continuity
- Potential dependency inconsistencies

These are presented to the operator as warnings but do not block restore.

#### v2 (Enforced — Future)

Restore MUST be blocked if:

- Any document in the path fails schema or QA validation
- Required upstream artifacts are missing
- Lineage continuity is broken
- Dependency constraints are violated

### 5.6 Operator Preview (Required)

Before confirmation, the system MUST display:

- Resulting active path
- Artifacts to be reactivated
- Artifacts to be demoted
- Downstream invalidation effects

### 5.7 Non-Behavior

Restore does NOT:

- Delete or overwrite history
- Bypass downstream invalidation rules
- Silently reactivate artifacts

---

## 6. Thread Deletion Semantics

A thread may be archived when:

- It is not part of the active path
- The operator explicitly confirms deletion

### Archived Threads

Archived threads:

- Do not appear in normal lineage navigation
- Cannot be restored
- Do not participate in certification

### Audit Stub (Required)

An archived thread MUST retain:

- Thread ID
- Root checkpoint
- Creation timestamp
- Deletion timestamp
- Actor

### Safety Rule

A thread containing the active path MUST NOT be archived.

### Hard Delete

Hard delete is not supported. All history remains append-only.

---

## 7. Timeline Viewer Requirements

The viewer MUST provide:

### 7.1 History View

Chronological list of:

- Document versions
- Rewind events
- Restore events

### 7.2 Status Indicators

Each item must show:

- Current / active
- Stale
- Superseded
- Archived

### 7.3 Path Awareness

Clear indication of active path vs historical threads.

### 7.4 Restore Interaction

- Ability to select a checkpoint
- Preview restore impact (Section 5.6)
- Confirm restore

---

## 8. Relationships

| ADR | Relationship |
|-----|-------------|
| ADR-063 | Defines rewind, which creates threads |
| ADR-064 | Authority is scoped to lineage paths |

---

## 9. Implementation Notes

This ADR implies:

- Deterministic lineage path computation
- Atomic restore operations
- Complete lineage tracking
- Explicit source-document binding across stages

---

## 10. Future Work

- Diff summaries between checkpoints (e.g., "IP v6 changed WPC count from 5 to 6")
- Visual branch/thread graph (non-linear view)
- Lineage-aware authority record evolution
- Thread filtering and search
- v2 validation enforcement (Section 5.5)

---

## 11. Summary

The Combine operates on governed document chains, not individual artifacts.

This ADR formalizes:

- How chains are restored
- How branches are managed
- How history remains auditable while staying usable
