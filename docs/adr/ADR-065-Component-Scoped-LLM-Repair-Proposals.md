# ADR-065 — Component-Scoped LLM Repair Proposals for Canonical Artifacts

| | |
|---|---|
| **Status** | Draft |
| **Version** | 0.3 |
| **Date** | 2026-03-27 |
| **Origin** | WS-EVAL-005A |
| **Contributors** | Tom, ChatGPT, Claude |

---

## 1. Purpose

Define a governed pattern for repairing defects in canonical artifacts using LLMs while preserving:

- Determinism
- Auditability
- Operator control
- Strict separation of evaluation and mutation

This ADR introduces **component-scoped repair proposals** as a reusable Combine primitive.

---

## 2. Context

- **WS-EVAL-003** → mechanical validation (`validate_ta_owns()`)
- **WS-EVAL-005A** → findings surfaced in binder

**Gap:** Findings are visible, but no governed remediation exists.

**Constraints:**

- Canonical artifacts are LLM-generated
- Evaluators are mechanical (ADR-058 layer 2)
- LLM interactions must be explicit and governed (ADR-049)
- Execution must be logged and replayable (ADR-010)
- Authority must be durable and traceable (ADR-064)

---

## 3. Scope Boundary (Initial Implementation)

- Applies only to **Technical Architecture (TA)**
- Extension to other artifact types is deferred

---

## 4. Problem

There is no mechanism to:

- Repair a specific TA component
- Use LLM assistance without:
  - Full regeneration
  - Manual editing

**Result:**

- Visible defects
- No governed remediation path

---

## 5. Decision

Introduce: **Component-Scoped LLM Repair Proposal**

---

## 6. Ontology Placement (ADR-045)

`RepairProposal` is introduced as a **new first-class concept** not currently defined in ADR-045.

It is:

- **Not** a Primitive (prompt fragments, schemas)
- **Not** a canonical document
- **Not** an evaluator

It behaves as:

- A governed, decision-bearing proposal to mutate a canonical artifact

**Characteristics:**

- Persisted
- Auditable
- Tied to a triggering finding
- Produces a reviewable structured output

**Note:** ADR-045 will require extension to formally classify `RepairProposal` (likely as a new Composite or authority-bearing construct). This ADR does not force-fit it into the current taxonomy.

---

## 7. Core Properties

### 7.1 Proposal-Based Mutation

- LLM output is never directly applied
- All changes are represented as `RepairProposal`
- Requires operator acceptance

### 7.2 Component Scope

- Target = single TA component
- `component_identifier` = `component.name`
- Assumes uniqueness by TA convention

### 7.3 Evaluator Separation

Evaluators (ADR-058 layer 2):

- Detect defects
- Never repair

### 7.4 Governed Interaction

Repair is a **task-level LLM interaction** using existing role structure.

**Prompt governance:**

- **Role:** `prompt:role:technical_architect:1.0.0`
- **Task:** `prompt:task:repair_ta_component:1.0.0`
- **Stored in:** `combine-config/prompts/`
- Version pinned per invocation

Must:

- Reference TA schema
- Enforce repair constraints (e.g., non-empty `owns[]`)
- Produce structured output

All interactions logged per ADR-010.

### 7.5 Reviewable Proposal

Each proposal includes:

- **before** (current component)
- **after** (proposed component)

Operator actions:

- Accept
- Reject
- Regenerate

### 7.6 Mutation Path (Deferred)

Post-stabilization mutation does not currently exist.

This ADR establishes the need for:

- A governed mutation path for canonical artifacts

Design is deferred.

### 7.7 Auditability

Record:

- Originating finding
- Repair request
- LLM input/output hash (ADR-010)
- Proposal state transitions
- Operator decision
- Reevaluation result

---

## 8. Constraints

Repair proposals **MUST NOT:**

- Modify document structure
- Add/remove components
- Affect unrelated components
- Bypass schema validation
- Bypass lifecycle governance

They **MAY:**

- Modify fields within a single component

---

## 9. Proposal Model

### RepairProposal

| Field | Description |
|-------|-------------|
| `proposal_id` | Unique identifier |
| `artifact_id` | Target document ID |
| `artifact_type` | `"TA"` (initial scope) |
| `component_identifier` | `component.name` |
| `trigger_finding` | Finding that triggered the repair |
| `proposed_payload` | Proposed component content |
| `status` | `pending` / `accepted` / `rejected` / `superseded` |
| `created_at` | Timestamp |
| `created_by` | Actor |
| `decision_at` | Decision timestamp |
| `decision_by` | Deciding actor |

---

## 10. Lifecycle Considerations

**Open:**

- Draft vs stabilized applicability
- Acceptance behavior:
  - Restabilize?
  - Re-QA?

Deferred to future design.

---

## 11. Alternatives

| Alternative | Decision |
|-------------|----------|
| Direct auto-fix | Rejected — violates ADR-049, removes operator control |
| Manual editing | Rejected — breaks LLM-first model |
| Full regeneration | Rejected — non-local, destabilizing |

---

## 12. Consequences

**Positive:**

- Localized repair
- Preserves evaluator determinism
- Strong audit trail
- Reusable pattern

**Negative:**

- New concept outside current ontology
- Requires mutation model
- Lifecycle complexity

---

## 13. Relationships

| ADR | Relationship |
|-----|-------------|
| ADR-010 | LLM execution logging |
| ADR-045 | Ontology (extension required) |
| ADR-049 | No black boxes |
| ADR-058 | Evaluation layer separation |
| ADR-064 | Durable authority |

---

## 14. Future Work

1. Extend ADR-045 to include `RepairProposal`
2. Define mutation path for canonical artifacts
3. Implement proposal persistence
4. Implement repair interaction
5. Extend to other artifact types

---

## 15. Summary

Repair is **proposal-based, component-scoped, LLM-governed, and operator-approved**.

- Evaluators detect
- LLMs propose
- Operators decide
- System records and reevaluates
