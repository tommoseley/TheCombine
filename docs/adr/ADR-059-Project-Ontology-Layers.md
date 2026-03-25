# ADR-059 — Project Ontology Layers and Translation Boundaries

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-03-19 |
| **Owner** | Combine Architecture |
| **Applies To** | All Combine projects (project-level semantics) |

---

## 1. Context

Combine-generated artifacts frequently express concepts at different semantic layers within a project domain.

Example (APAM):

- **Decision Layer** (portfolio intent): ADD_20, REMOVE_ALL, HOLD
- **Execution Layer** (order side): buy, sell

These layers are already implicitly present in generated binders, but are not formally defined or enforced. This can lead to:

- Vocabulary leakage across layers (e.g., buy/sell in decision logic)
- Inconsistent modeling across artifacts (IP vs TA vs WP/WS)
- Ambiguity in translation between intent and execution

This is not a Combine system ontology concern (e.g., Prompt Fragments, Schemas per ADR-045/057), but a project-level semantic concern.

---

## 2. Decision

The Combine will support project-level ontology definitions with explicit:

### 2.1 Semantic Layers

Projects may define one or more semantic layers (e.g., Decision, Execution).

Each layer:

- owns a distinct vocabulary
- represents a specific level of abstraction (intent, planning, execution, etc.)

### 2.2 Vocabulary Ownership

Each vocabulary term must belong to exactly one semantic layer.

Example:

- `ADD_20` → Decision Layer
- `buy` → Execution Layer

### 2.3 Translation Boundaries

Projects must define explicit translation points between layers.

Example:

- Decision → Execution:
  - `ADD_20` → `buy` with computed quantity
  - `REMOVE_ALL` → `sell` with full position size

Translation logic must be localized and not implicitly distributed across artifacts.

### 2.4 Cross-Layer Leakage

Artifacts **should not** use vocabulary from another layer outside defined translation points. Violations are detected and reported; enforcement level is configurable per project (see Section 3).

Examples of violations:

- Decision-layer WS using `buy`/`sell` → leakage
- Execution-layer WS using `ADD_20` as an order side → leakage

---

## 3. Enforcement Model

### 3.1 Evaluator Check (Phase 1 — Required)

The Combine will implement an evaluator that:

- scans artifacts (WP, WS, TA, etc.)
- detects vocabulary usage by layer
- flags cross-layer leakage and inconsistencies
- produces structured findings with evidence

This check is:

- **advisory** (non-blocking) by default
- included in evaluation reports and binder evidence

### 3.2 Optional Gate Enforcement (Phase 2 — Configurable)

Projects may opt-in to enforce ontology consistency as a promotion invariant.

When enabled:

- cross-layer violations may block stabilization or promotion
- violations are treated as HARD_STOP conditions

---

## 4. Scope Boundaries

This ADR:

- **DOES** define how project-level semantics are structured and validated
- **DOES NOT** define domain vocabularies themselves (project-owned)
- **DOES NOT** modify Combine system ontology (ADR-045, ADR-057)

---

## 5. Rationale

This approach:

- preserves Combine's domain-agnostic design
- allows projects to define their own semantics
- ensures semantic consistency across artifacts
- enables mechanical detection of modeling errors
- supports gradual adoption (advisory → enforceable)

---

## 6. Consequences

**Positive:**

- clearer separation of intent vs execution
- reduced ambiguity in generated artifacts
- improved evaluator signal quality
- foundation for future deterministic enforcement
- versioned ontology per project enables replay stability

**Negative / Trade-offs:**

- requires explicit ontology definition per project
- adds evaluator complexity
- may surface new classes of "violations" in existing binders

---

## 7. Example (APAM)

**Layers:**

- Decision Layer: `ADD_20`, `REMOVE_ALL`, `HOLD`
- Execution Layer: `buy`, `sell`

**Translation:**

- `ADD_20` → `buy` (20% allocation)
- `REMOVE_ALL` → `sell` (full position)

**Violation Example:**

- WS uses `buy` directly in decision logic → flagged by evaluator

---

## 8. Implementation Notes

### 8.1 Ontology Must Be Declared, Not Inferred

Project ontology definitions must be explicitly declared in project configuration. The evaluator does not infer vocabulary ownership from schemas, prompts, or generated content.

Declaration format (minimum):

```yaml
ontology:
  layers:
    decision:
      vocabulary: [ADD_20, REMOVE_ALL, HOLD]
    execution:
      vocabulary: [buy, sell]
  translations:
    - from: decision
      to: execution
```

### 8.2 No Ontology = No Check

If a project does not declare an ontology, the evaluator check is **skipped with explicit notice** in the evaluation report. The evaluator does not guess, assume, or silently pass.

### 8.3 Finding Structure

Findings should include:

- artifact location (document type, field path)
- offending term
- expected layer
- context snippet

### 8.4 Determinism

The evaluator must operate deterministically with no LLM dependency. Vocabulary matching is mechanical string comparison against the declared sets.

---

## 9. Status and Next Steps

1. Define ontology for APAM (first project instance)
2. Implement evaluator check for vocabulary consistency
3. Observe findings across replay runs
4. Consider optional gate enforcement based on maturity

---

*End of ADR-059*
