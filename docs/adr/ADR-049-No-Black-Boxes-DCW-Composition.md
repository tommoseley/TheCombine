# ADR-049 -- No Black Boxes: Explicit DCW Composition

**Status:** Accepted
**Date:** 2026-02-09
**Decision Type:** Architectural / Principle

**Related ADRs:**
- ADR-039 -- Document Interaction Workflow Model
- ADR-045 -- System Ontology: Primitives, Composites, and Configuration Taxonomy
- ADR-047 -- Mechanical Operations
- ADR-048 -- Intake POW and Workflow Routing

---

## 1. Context

The Concierge Intake workflow (v1.4.0) forced an architectural reckoning. To support its multi-pass structure (LLM classification → mechanical extraction → operator entry → mechanical pinning), we introduced:

- Gate Profiles with explicit internal passes
- Mechanical Operations as first-class primitives (ADR-047)
- Entry operations for operator interaction

This decomposition made Concierge transparent: every pass is visible, configurable, and auditable.

However, other DCWs -- Project Discovery, Technical Architecture, Implementation Plan -- remain opaque. They appear in the workflow editor as single "Generate" steps that hide:

- PGC (clarification question generation)
- Operator answer entry
- Answer merging
- Document generation
- QA evaluation
- Remediation loops

This inconsistency creates problems:

1. **Cognitive dishonesty** -- Concierge is "different" when it shouldn't be
2. **UI confusion** -- Some workflows show internals, others are black boxes
3. **Governance gaps** -- Hidden passes cannot be individually audited or configured
4. **Extensibility friction** -- Adding new gates (risk, compliance, cost) requires inventing new patterns

The principle should be:

> Every meaningful step is a composed workflow, not a monolith.
> Some are simple. Some are complex. But none are magic.

---

## 2. Decision

The Combine adopts the **No Black Boxes** principle:

1. **Every DCW is explicitly composed** of gates, interaction passes, and mechanical operations
2. **"Generate" is deprecated** as a user-visible abstraction -- it hides too much
3. **DCWs are first-class workflows**, not "steps inside a POW"
4. **Composition is always visible**, even if collapsed by default in the UI

---

## 3. Two-Tier Workflow Architecture

### 3.1 POW (Production-Oriented Workflow)

What users think they're running. Orchestrates outcomes at the project level.

**Responsibilities:**
- Sequences DCW invocations
- Manages routing and spawning
- Owns project-level lineage
- Reacts to DCW terminal outcomes (stabilized, blocked, abandoned)

**Examples:**
- `intake_and_route` -- Front-door POW
- `software_product_development` -- Main delivery POW

**POWs do NOT:**
- Manage internal document loops
- Interpret intermediate document states
- Bypass document QA or stabilization

### 3.2 DCW (Document Creation Workflow)

Produces one stabilized document. Internally composed of gates, passes, and mechanicals.

**Responsibilities:**
- Owns the complete lifecycle of a single document type
- Explicitly defines all interaction passes
- Contains gates (PGC, QA, risk, compliance) as configured
- Produces terminal outcomes consumed by POWs

**Examples:**
- `concierge_intake` -- Intake classification and routing decision
- `project_discovery` -- Discovery document with PGC and QA
- `implementation_plan` -- Planning document with QA (no PGC)
- `technical_architecture` -- Architecture document with PGC and QA

**DCWs are NOT:**
- Opaque "steps" inside POWs
- Single LLM calls wrapped in a workflow
- Magic black boxes

---

## 4. DCW Composition Patterns

**Terminology note:** A **Gate** is a composite structure containing multiple interaction passes with evaluation logic. A **Gate Profile** is a reusable configuration of a gate's internal passes. PGC Gate and QA Gate are gate types; Concierge's intake classification uses a specific Gate Profile configuration.

### 4.1 Full Pattern (PGC + Generation + QA)

Used when clarification improves generation quality.

```
DCW: project_discovery
 ├── PGC Gate
 │    ├── LLM Pass: Question Generation
 │    ├── Entry: Operator Answers
 │    └── Mechanical: Merge Answers into Context
 │
 ├── LLM Pass: Document Generation
 │
 ├── QA Gate
 │    ├── LLM Pass: Quality Evaluation
 │    └── Mechanical: Remediation Loop (if needed)
 │
 └── Produce: project_discovery document
```

### 4.2 QA-Only Pattern (Generation + QA)

Used when inputs are sufficient without clarification.

```
DCW: implementation_plan
 ├── LLM Pass: Plan Generation (using upstream artifacts)
 │
 ├── QA Gate
 │    ├── LLM Pass: Quality Evaluation
 │    └── Mechanical: Remediation Loop (if needed)
 │
 └── Produce: implementation_plan document
```

### 4.3 Gate Profile Pattern (Multi-Pass Classification)

Used for complex decision workflows.

```
DCW: concierge_intake
 ├── Gate: Intake Classification
 │    ├── LLM Pass: Classification
 │    ├── Mechanical: Extract + Normalize
 │    ├── Entry: Operator Confirmation
 │    └── Mechanical: Pin Decision
 │
 └── Produce: intake_record
```

---

## 5. Implications

### 5.1 "Generate" Is an Anti-Pattern

The word "Generate" as a step label implies a single LLM call producing a document. This is misleading.

**Before (hidden complexity):**
```
Step: "Generate Project Discovery"
  → [magic happens]
  → Document appears
```

**After (explicit composition):**
```
DCW: project_discovery
  → PGC Gate (questions → answers → merge)
  → Generation Pass (LLM with full context)
  → QA Gate (evaluation → remediation)
  → Stabilized document
```

UI labels should reflect the actual work:
- "Discovery" not "Generate Discovery"
- "Planning" not "Generate Implementation Plan"
- "Architecture" not "Generate Technical Architecture"

### 5.2 DCWs Are Independently Versioned

Because DCWs are first-class workflows:
- `project_discovery` v1.8.0 can evolve its gate composition without changing the POW
- Gate configurations (PGC prompts, QA criteria) are versioned within the DCW
- POWs reference DCWs by ID + version, not by embedding their structure

### 5.3 UI Shows Composition

The workflow editor and production floor should:
- Show DCW internal structure (gates, passes, mechanicals)
- Allow collapsing for overview, expanding for detail
- Never hide passes entirely -- transparency is the point

### 5.4 Same Primitives Everywhere

All DCWs use the same building blocks:
- **LLM Pass** -- Interaction Pass binding fragments + schema (ADR-045)
- **Mechanical Operation** -- Deterministic transformation (ADR-047)
- **Entry Operation** -- Operator input collection
- **Gate** -- Composite containing multiple passes with evaluation logic

No special cases. No DCW-specific magic.

---

## 6. Artifact State Alignment

The unified artifact state model (Blocked / In Progress / Ready / Stabilized) applies to documents, not to passes or gates.

- **Stabilized** = All gates passed, document is governed and immutable
- **Ready** = Gates passed, awaiting acceptance
- **In Progress** = Passes executing (queued or active)
- **Blocked** = Cannot proceed (missing inputs, failed QA, needs operator)

Execution state (which pass is running) is internal. Artifact state (document readiness) is what users see.

---

## 7. Migration Path

### 7.1 Immediate (No Code Change)

- Document this principle in ADR-049
- Update CLAUDE.md to reference the No Black Boxes principle

### 7.2 Short-Term

- Decompose `project_discovery` DCW to show explicit PGC + Generation + QA gates
- Decompose `technical_architecture` DCW similarly
- Update Admin Workbench to render DCW internals

### 7.3 Medium-Term

- Deprecate "Generate" as a step type in workflow definitions
- Migrate all DCWs to explicit composition
- Add UI support for collapsible gate detail

---

## 8. Consequences

### Positive

- **Consistency** -- Concierge is no longer "weird"; all DCWs follow the same model
- **Transparency** -- Every pass is visible, configurable, and auditable
- **Extensibility** -- Adding new gate types (risk, compliance, cost) doesn't require new patterns
- **Governance** -- Individual passes can be versioned, certified, and traced
- **UI sanity** -- One metaphor for all workflows

### Tradeoffs

- **More verbose definitions** -- DCW definitions are larger but clearer
- **Migration effort** -- Existing DCWs must be decomposed
- **Learning curve** -- Users must understand gates and passes (but this is the truth they were missing)

These tradeoffs are intentional. Hiding complexity is a liability, not a feature.

---

## 9. Non-Goals

This ADR does NOT:
- Change interaction mechanics (ADR-012)
- Change mechanical operation definitions (ADR-047)
- Introduce new primitive types
- Define specific gate configurations for each DCW (that's implementation work)

---

## 10. Summary

> Once you introduce gates and mechanicals for one workflow, keeping black boxes elsewhere becomes inconsistent.

ADR-049 establishes that:

1. Every DCW is explicitly composed of gates, passes, and mechanicals
2. "Generate" is deprecated as a user-visible abstraction
3. DCWs are first-class workflows, not opaque steps
4. The same primitives apply everywhere -- no special cases

This completes the architectural unboxing that Concierge began.

---

## 11. Acceptance Criteria

ADR-049 is considered satisfied when:

1. `project_discovery` DCW is decomposed into explicit PGC + Generation + QA gates
2. `technical_architecture` DCW is decomposed similarly
3. `implementation_plan` DCW shows explicit QA gate (no PGC)
4. Admin Workbench renders DCW internal structure
5. No DCW uses "Generate" as an opaque step type
6. CLAUDE.md references the No Black Boxes principle

---

_End of ADR-049_
