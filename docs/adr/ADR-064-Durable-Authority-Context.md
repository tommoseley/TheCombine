# ADR-064 — Durable Authority Context: PGC Answers as Project-Level Governed Inputs

**Status:** Draft
**Date:** 2026-03-22
**Owners:** Tom / Combine Architecture
**Coupled With:** ADR-063 (Pipeline Rewind)

---

## 1. Context

PGC (Pre-Generation Clarification) answers represent binding user decisions — "Python 3.12", "paper trading only", "limit orders with ±0.5% offset." These are not chat messages. They are project authority.

Currently, PGC answers are stored in `workflow_executions.context_state` — tied to a specific execution run. This causes:

- **Authority loss on regeneration**: new execution starts with empty context, QA can't audit
- **Repeated questions**: system re-asks what the user already answered
- **Inconsistent artifacts**: downstream documents may omit or contradict prior user declarations
- **Broken auditability**: no durable record of what the user said and when

ADR-063 established pipeline rewind. This ADR establishes its complement: **what persists when the pipeline rewinds.**

---

## 2. Problem Statement

The Combine treats authority the same as execution context. This is a model mismatch.

**Execution context** is transient — how a specific run is configured and what it produces.

**Authority context** is durable — what is true and binding for this project, as declared by the user or derived from governed inputs.

When rewind creates a new execution, authority must survive. When the user answers differently on a rewound path, the old answer must become historical, not lost.

---

## 3. Decision

### 3.1 PGC answers are project authority, not execution state

PGC answers are promoted from `workflow_executions.context_state` to a durable, project-scoped authority store. They persist across pipeline runs, rewinds, and regenerations.

### 3.2 Authority is path-aware

Authority is not global and cumulative. It is resolved against the current lineage path.

- Answers on the current accepted path are **current authority**
- Answers on abandoned/rewound paths are **historical authority** (auditable but not governing)
- When the user answers differently after rewind, the old answer becomes **superseded**

**Core principle:**

> Project authority is durable, auditable, and resolved against the current lineage path.

### 3.3 Authority persists across runs but current authority follows the accepted path

- All authoritative user answers persist permanently
- Current authority is determined by the active lineage path after rewind/regeneration
- The project authority goes with the accepted rewind path

### 3.4 Execution context is hydrated from authority

Every stage execution receives a stable authority bundle containing:

- Relevant PGC questions and answers (current)
- Bound constraints (current)
- Key decisions and overrides (current)
- Correlation/trace identifiers

Execution does not reconstruct authority from history. Authority is explicitly stored, versioned, and referenced.

### 3.5 QA must reference authority explicitly

QA gates validate against the authority bundle and can distinguish:

- "Document violates constraint X" (true noncompliance)
- "Constraint X is missing from authority bundle" (incomplete authority)
- "Constraint X was superseded by Y" (authority evolution)

---

## 4. Authority Model

### 4.1 Three Layers

| Layer | Purpose | Persistence | Mutability |
|-------|---------|-------------|------------|
| **Intent** | Why the project exists | Concierge Intake | Immutable after acceptance |
| **Authority Context** | What is true and binding | Project-scoped store | Versioned, path-aware |
| **Execution Context** | How a specific run executes | Execution state | Transient per run |

### 4.2 Authority Record Structure

```
authority_record:
  id: UUID
  project_id: UUID
  authority_type: "pgc_answer" | "bound_constraint" | "user_override"
  stage: PipelineStage (which stage this authority was established at)
  key: str (question_id, constraint_id, or override key)
  value: any (the user's answer or constraint value)
  source_execution_id: UUID (which execution produced this)
  lineage_event_id: UUID (which lineage path this belongs to)
  status: "current" | "superseded" | "historical"
  superseded_by: Optional[UUID] (points to the replacing record)
  created_at: datetime
  actor: str
```

### 4.3 Resolution Rules

1. **Current authority** = records where `status == "current"` for the project
2. **On rewind**: authority records from the abandoned path remain with `status: "historical"`
3. **On re-answer**: old record becomes `status: "superseded"`, new record becomes `status: "current"` with `superseded_by` link
4. **On regeneration without re-answer**: current authority is inherited — PGC phase is skipped

---

## 5. Interaction with ADR-063 (Rewind)

ADR-063 defines: what changes (artifacts become stale)
ADR-064 defines: what persists (authority remains addressable)

Together:

| Event | Artifacts | Authority |
|-------|-----------|-----------|
| **Rewind** | Downstream artifacts become stale | Authority stays current unless user re-answers |
| **Regeneration (same answers)** | New artifacts created | Authority inherited, PGC skipped |
| **Regeneration (new answers)** | New artifacts created | Old answers superseded, new answers current |
| **Full re-run** | All artifacts regenerated | All PGC phases re-execute, authority refreshed |

---

## 6. Consequences

### Positive

- User never has to re-answer settled questions
- QA can perform full compliance audits after regeneration
- Artifacts are provably governed by declared authority
- Authority evolution is traceable (who changed what, when, why)
- Foundation for future artifact intake (mockups, constraints become authority)

### Negative

- New persistence model required (authority records table)
- PGC flow must check for existing authority before asking questions
- Authority resolution adds query complexity
- Path-aware supersession logic must be correct or authority becomes ambiguous

---

## 7. What This Enables (Future)

- **Artifact intake**: uploaded mockups, standards, constraints become authority records
- **Authority diff**: show what changed between paths after rewind
- **Compliance certification**: QA can cite specific authority records as evidence
- **Authority dashboard**: user can inspect all binding decisions for a project

---

## 8. MVP Approach

1. Create `authority_records` table with the structure in 4.2
2. On PGC answer acceptance, persist as authority record
3. On stage execution start, hydrate authority bundle from current records
4. On rewind, mark authority on abandoned path as historical
5. On re-answer after rewind, supersede old record
6. QA receives authority bundle and can cite it

---

## 9. Open Questions

- Should authority records be immutable (append-only with status changes) or mutable?
- How do bound constraints from intake/discovery become authority records?
- Should authority records have their own display_ids for user-facing reference?
- How does authority interact with multi-instance documents (WP-level PGC)?

---

## 10. Recommendation

Adopt durable authority context as a first-class Combine primitive, co-equal with pipeline rewind (ADR-063).

Together they form the system's two foundational capabilities:

- **ADR-063**: What changes (time + causality)
- **ADR-064**: What persists (truth + governance)
