# ADR-011 — Document Ownership Model

**Status:** Accepted  
**Date:** 2026-01-02  
**Supersedes:** ADR-011 (Project / Epic / Story Ownership & Organization – prior draft)  
**Related ADRs:**

- ADR-009 — Audit & Governance
- ADR-010 — LLM Execution Logging
- ADR-012 — Interaction Model
- ADR-027 — Workflow Definition & Governance

---

## 1. Decision Summary

The Combine adopts a generic document ownership model in which:

- Documents may own other documents.
- Ownership is explicit, exclusive, scoped, and enforced.
- Ownership relationships define scope boundaries for discovery, reference, execution, and governance.
- Specific ownership hierarchies are declared by workflows, not hard-coded into the platform.

**This ADR defines the ownership pattern.**  
**Workflow definitions (ADR-027) define ownership instances.**

---

## 2. Core Ownership Principles

### 2.1 Ownership Is Explicit

- A document MAY own zero or more child documents.
- Ownership relationships MUST be explicitly declared (via workflow definition).
- Implicit or inferred ownership is prohibited.

### 2.2 Ownership Is Exclusive

- A document MUST have at most one owner.
- A document MAY be a root (no owner).
- Shared ownership is not permitted.

### 2.3 Ownership Creates Scope

- Ownership establishes a scope boundary.
- A child document exists within the scope of its owner.
- Scope boundaries constrain:
  - Discovery
  - References
  - Execution context
  - Governance rules

### 2.4 Ownership Is Enforced

- Ownership rules MUST be mechanically enforced at runtime.
- Violations (invalid references, scope leaks, cycles) MUST result in explicit failure.
- Silent correction or inference is forbidden.

---

## 3. Structural Constraints

### 3.1 Ownership Graph Rules

- Document ownership relationships MUST form a directed acyclic graph (DAG).
- Cycles are prohibited.
- Recursive ownership is permitted, subject to workflow definition.

### 3.2 Scope Containment

- A child document's scope MUST NOT exceed its parent's scope.
- Descendant documents inherit the constraints of all ancestors.

---

## 4. Relationship to Workflows (ADR-027)

**This ADR defines the ownership model.**  
**ADR-027 defines workflow-specific ownership declarations.**

Specifically:

Workflows declare:

- Which document types exist
- Which document types may own others
- How collections of child documents are represented

This ADR defines the invariants that all workflows must obey.

**The platform MUST validate workflow definitions against the ownership rules defined here.**

---

## 5. Reference Rules (Generic)

Ownership governs what documents may reference one another.

### 5.1 Permitted References

- Child → Parent: Permitted
- Child → Ancestor: Permitted

### 5.2 Restricted References

- Sibling → Sibling: Forbidden by default
- Cross-branch references: Forbidden

Exceptions MUST be explicitly declared by workflow definition.

### 5.3 Parent → Child

- Parents own children but MUST NOT depend on child content.
- Ownership does not imply reverse reference.

---

## 6. Discovery Scope (Generic)

Discovery behavior is constrained by ownership.

- Discovery MAY occur only at documents that own child documents.
- Leaf documents (documents that own nothing) MUST NOT generate discovery questions.
- Discovery scope is inherited:
  - Child documents may refine but not redefine parent constraints.

The determination of which document types generate discovery is workflow-defined.

---

## 7. Architecture and Constraints (Generic)

Architecture, constraints, and invariants are scoped by ownership.

- Parent documents define constraints that child documents MUST respect.
- Child documents MAY specialize or refine within inherited boundaries.
- Contradicting parent constraints is forbidden.

**The meaning of "architecture" is domain- and workflow-specific and is not defined by this ADR.**

---

## 8. Enforcement & Governance

Ownership rules defined here are subject to:

**ADR-009 (Audit & Governance):**
- Ownership relationships must be traceable and inspectable.

**ADR-010 (LLM Execution Logging):**
- Ownership context must be part of execution records.

Ownership violations MUST surface as explicit errors.

---

## 9. Out of Scope

This ADR intentionally does not define:

- Specific document hierarchies (e.g., Project/Epic/Story)
- Domain vocabulary
- Workflow sequencing
- Task prompts or role behavior
- Interaction mechanics (see ADR-012)

---

## 10. Rationale

Separating the ownership model from workflow instances enables:

- Multiple domains (software, construction, strategy, research)
- Arbitrary depth of document hierarchies
- Reusable execution and governance machinery
- Clear enforcement of scope and responsibility boundaries

Hard-coding a single hierarchy would prematurely constrain the platform and conflict with governed workflows.

---

## 11. Consequences

### Positive

- Enables composable, recursive workflows
- Eliminates ambiguity about scope and authority
- Aligns ownership with auditability and enforcement
- Clean separation of pattern vs. instance

### Tradeoffs

- Requires workflow definitions to be explicit
- Slightly higher upfront rigor in schema and validation
