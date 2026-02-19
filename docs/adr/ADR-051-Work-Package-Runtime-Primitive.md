# ADR-051 -- Work Package as Runtime Primitive

**Status:** Accepted
**Date:** 2026-02-18
**Accepted:** 2026-02-18
**Decision Type:** Architectural / Ontological

**Related ADRs:**
- ADR-050 -- Work Statement Verification Constitution
- ADR-048 -- Intake POW and Workflow Routing
- ADR-045 -- System Ontology: Primitives, Composites, and Configuration Taxonomy

**Related Policies:**
- POL-WS-001 -- Standard Work Statements

---

## 1. Context

ADR-050 established Work Statements (WS) as the atomic, verifiable unit of execution. However, a flat list of WS instances does not provide sufficient structure for:

- **Planning** -- grouping related changes into coherent capability boundaries
- **Dependency management** -- ordering work at a level above individual WS
- **Progress tracking** -- answering "how far along is this capability?"
- **Promotion gating** -- enforcing that a coherent bundle of work meets its Definition of Done before downstream work proceeds

The previous Epic/Feature hierarchy (borrowed from Agile) is replaced with a more execution-aligned model. Epics are value-sliced, story-driven, and estimation-influenced. The Combine needs capability-coherent, dependency-aware, state-change-defined groupings.

---

## 2. Decision

**Work Packages (WP) are first-class runtime objects within The Combine.**

The planning hierarchy becomes:

```
Implementation Plan ? Work Packages ? Work Statements
```

- **Implementation Plan** defines the strategic decomposition and dependency graph
- **Work Packages** are the trackable units of progress with promotion gates
- **Work Statements** are the executable, verifiable atomic units

This replaces Epics, Features, and Stories. Work Statements are the only atomic unit. Work Packages are the only progress-tracked unit.

---

## 3. Work Package Definition

A Work Package groups related Work Statements into a coherent capability boundary.

Each Work Package contains:

| Field | Purpose |
|-------|---------|
| **Scope boundary** | What is in and out of this package |
| **Rationale** | Why this bundle exists (may reference an ADR, may not) |
| **Dependencies** | Other Work Packages that must complete first |
| **Definition of Done** | Higher-level completion criteria beyond individual WS |
| **Work Queue** | Dynamic set of child WS instances |
| **Governance pins** | ADR/policy versions pinned at instantiation |

---

## 4. Dynamic Work Queue

Work Statements are **not** statically bound to a Work Package. They are spawned into a dynamic queue.

This is necessary because:

- WS may fail and be respawned
- WS may split into multiple smaller WS
- WS may merge when overlap is discovered
- WS may produce Verification Debt WS (Mode B mechanization plans)

The Work Package does not care about the specific WS instances. It cares about whether its **Definition of Done** is satisfied.

This mirrors the relationship between POWs and DCWs -- the POW tracks required outcomes, not specific document instances.

---

## 5. Work Package States

Work Packages progress through explicit states:

```
PLANNED ? READY ? IN_PROGRESS ? AWAITING_GATE ? DONE
```

| State | Meaning |
|-------|---------|
| **PLANNED** | Defined in IP, not yet ready for execution |
| **READY** | Dependencies satisfied, work can begin |
| **IN_PROGRESS** | Child WS instances are being executed |
| **AWAITING_GATE** | All child WS complete, promotion criteria being evaluated |
| **DONE** | Definition of Done verified, promoted |

---

## 6. Promotion Gate

A Work Package is a **promotion gate**, not merely an organizational container.

Promotion from AWAITING_GATE to DONE requires:

1. All child WS instances completed
2. No outstanding Mode B verification debt (or explicitly accepted with justification)
3. Tier 0 clean across the full WP scope
4. Definition of Done mechanically verified where possible

This is a mechanical check, not a judgment call.

---

## 7. Governance Pinning

Governance artifacts (ADRs, policies, schemas) applicable to a Work Package are **pinned at instantiation**.

This ensures:

- Replayability -- the same WP executed later produces the same constraints
- No mid-flight drift -- governance changes do not retroactively alter in-progress work
- Auditability -- the exact governance context is recorded

Governance changes apply to **future** Work Packages, not in-flight ones.

---

## 8. Relationship to Implementation Plans

The IPP/IPF schemas will evolve:

- `epic_candidates[]` becomes `work_package_candidates[]`
- Each candidate defines scope, rationale, dependencies, and Definition of Done
- Individual Work Statements are **not** enumerated in the IP -- they are authored at execution time

The IP plans Work Packages. Work Packages spawn Work Statements. This is the correct decomposition boundary.

---

## 9. Consequences

### Positive

- **Epics, Features, and Stories are eliminated** -- replaced by a cleaner, execution-aligned hierarchy
- **Progress is trackable** at a meaningful level above individual WS
- **Dependencies are enforceable** between capability bundles
- **Promotion gating prevents premature advancement** -- incomplete bundles cannot proceed
- **Governance pinning preserves replayability**

### Tradeoffs

- **New runtime object** -- Work Packages require state management infrastructure
- **Schema migration** -- IPP/IPF schemas must evolve from epic-based to WP-based
- **Deferred implementation** -- WP as runtime objects will be built when WS volume demands it

---

## 10. Non-Goals

This ADR does NOT:

- Define the Work Package schema (implementation work)
- Define the WP state machine implementation details
- Deprecate existing epic-based IP documents (they remain valid as historical artifacts)
- Require immediate implementation -- current implicit grouping (ADR prefix, capability affinity) is sufficient at present volume

---

## 11. Acceptance Criteria

ADR-051 is considered satisfied when:

1. Work Package exists as a runtime object with state tracking
2. IPP/IPF schemas use `work_package_candidates[]` instead of `epic_candidates[]`
3. At least one Work Package has been promoted through the full state lifecycle
4. Governance pinning is implemented (WP records applicable ADR/policy versions)
5. The dynamic work queue supports WS spawn, split, and debt tracking

---

## 12. Implementation Sequencing

This ADR is intentionally forward-looking. The implementation sequence is:

1. **Now**: Continue executing WS under ADR-050 with implicit WP grouping
2. **When WS volume demands it**: Implement WP as runtime objects
3. **When WP runtime exists**: Migrate IPP/IPF schemas from epics to work packages
4. **When self-hosting**: Work Packages become the unit The Combine tracks for its own development

Build the bridge when you need to cross it. The decision is recorded so it is not lost.

---

_End of ADR-051_
