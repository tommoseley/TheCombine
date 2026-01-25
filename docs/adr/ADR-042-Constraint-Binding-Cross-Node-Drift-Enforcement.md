# ADR-042: Constraint Binding & Cross-Node Drift Enforcement

## Status

**Accepted**

## Context

The Combine uses a multi-step, multi-agent workflow to transform user intent into structured artifacts (e.g., Project Discovery, Architecture, Epics, QA plans).

Early workflow stages—particularly the Clarification Question Protocol (PGC) and Concierge Intake—collect explicit user decisions (e.g., target platform, scope exclusions, compliance requirements). Some of these decisions are definitive and intended to constrain all downstream reasoning.

The current architecture treats these decisions as contextual inputs rather than binding constraints, resulting in observable failure modes:

- Previously resolved decisions are reintroduced as open questions
- Downstream artifacts contradict explicit user selections
- QA passes locally while missing cross-node intent drift
- Decision traceability degrades across workflow steps

This ADR formalizes how certain user decisions become bound constraints, how they propagate across workflow nodes, and how all downstream QA stages must enforce them.

## Decision

### 1. Introduce the Concept of Bound Constraints

A **bound constraint** is a user-provided decision that:

- Is explicitly resolved
- Is not subject to reinterpretation
- Constrains all downstream workflow nodes
- May only be changed through explicit renegotiation

**Bound constraints are facts, not recommendations or heuristics.**

Examples:

- Platform selection (e.g., web-only)
- Explicit exclusions ("no mobile", "no offline mode")
- Regulatory or compliance requirements
- Declared scope limits

### 2. Canonical Representation: `pgc_clarifications`

PGC questions and answers MUST be mechanically merged into a single, self-contained structure before downstream use.

Canonical structure:

```json
{
  "pgc_clarifications": [
    {
      "id": "TARGET_PLATFORM",
      "text": "What platform should the app target?",
      "priority": "must",
      "answer_type": "single_choice",
      "choices": [
        { "id": "web", "label": "Web browser" },
        { "id": "mobile", "label": "Mobile application" }
      ],
      "user_answer": "web",
      "user_answer_label": "Web browser",
      "resolved": true,
      "binding": true
    }
  ]
}
```

This structure MUST be injected verbatim into all downstream LLM prompts and QA evaluations.

### 3. Binding Derivation Rules

A clarification becomes `binding = true` if any of the following apply:

- `priority == "must"` and `user_answer` is not null or "undecided"
- The user explicitly marks the decision as a hard constraint
- The clarification represents an explicit exclusion (e.g., "no mobile", "no integrations")

A clarification is `binding = false` (informational only) if:

- `priority == "should"` or `priority == "could"`
- The answer is null or "undecided"
- The clarification represents a preference rather than a requirement

**Binding is derived mechanically, not inferred by the LLM.**

### 4. Constraint Propagation Rules

Bound constraints:

- MUST be propagated unchanged to all downstream workflow nodes
- MUST NOT be reinterpreted, reweighted, or reopened
- MUST be treated as authoritative facts

Downstream nodes:

- MAY elaborate on implications
- MAY optimize within constraints
- MUST NOT present alternatives that violate constraints

### 5. Cross-Node Drift Enforcement (Requirement)

All QA nodes MUST validate outputs against all bound constraints, regardless of where the constraint originated.

QA MUST fail if any of the following occur:

- A bound constraint is contradicted
- A previously excluded option is reintroduced
- Language implies undecided status for a resolved constraint
- Recommendations conflict with bound facts
- Decision points are presented for already-resolved topics

This requirement applies uniformly across:

- Discovery QA
- Architecture QA
- Backlog QA
- Epics / Stories QA
- Any future artifact QA

### 6. Formal Definition of Drift

**Constraint Drift** is defined as:

> Any output that weakens, contradicts, reopens, or bypasses a bound constraint without explicit user authorization.

Drift includes:

- Direct contradiction
- Suggestive alternatives ("could also consider...")
- Reframing settled decisions as open
- Recommending incompatible architectures or features

**Drift detection is mandatory.**

### 7. Re-Negotiation of Constraints

Bound constraints may only be modified if:

1. The system explicitly enters a **constraint renegotiation mode**
2. The existing constraint is presented verbatim
3. The user explicitly changes or revokes it

**Silent reinterpretation is forbidden.**

## Implementation Requirements

### Mechanical Merge

On PGC submission, the workflow engine MUST merge questions and answers into `pgc_clarifications`.

### Invariant Propagation

All `binding = true` clarifications MUST be propagated as invariants to downstream nodes (e.g., `context_state["pgc_invariants"]`).

### Prompt Injection

Generation templates MUST include a canonical injection point (e.g., `$$PGC_CLARIFICATIONS`).

### Constraint Drift Validation

QA MUST implement constraint drift checks (e.g., QA-PGC-001 through QA-PGC-004) against all invariants.

## Schema

The canonical schema for merged clarifications is defined in:

```
seed/schemas/pgc_clarifications.v1.json
```

## Intake as a Constraint Source

PGC is not the only source of binding constraints.

Concierge Intake and other pre-PGC stages MAY also emit binding constraints. Any such constraints MUST conform to the same representation, propagation, and enforcement rules defined in this ADR.

## Consequences

### Positive

- Strong intent preservation across workflow nodes
- Elimination of "decision amnesia"
- QA becomes a system-wide enforcement layer
- Clear separation of responsibility:
  - **ADR-024**: How questions are asked
  - **ADR-042**: What answers mean
  - **ADR-014**: How QA enforces compliance

### Tradeoffs

- Increased rigor in context management
- Slightly larger prompt payloads
- Requires deterministic (non-LLM) merge logic

These tradeoffs are intentional.

## Related ADRs

- **ADR-024** — Clarification Question Protocol
- **ADR-014** — Quality Assurance Modes & Authority

## Non-Goals

This ADR does not:

- Define UI rendering
- Define question authoring rules
- Replace ADRs for architectural decisions
- Infer constraints from ambiguous language

## Summary

ADR-042 establishes **constraint binding** as a first-class system invariant.

Once bound, user decisions are no longer advisory. They are **enforced facts** that shape every downstream artifact—and every QA node is responsible for defending them.

This closes a critical architectural gap and makes The Combine's intent preservation mechanical, auditable, and non-negotiable.