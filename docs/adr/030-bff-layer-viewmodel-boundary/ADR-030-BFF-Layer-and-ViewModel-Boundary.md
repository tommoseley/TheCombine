# ADR-030: Backend-for-Frontend (BFF) Layer and ViewModel Boundary

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-01-06 |
| **Decision Owner** | Product Owner |
| **Applies To** | All UX surfaces consuming Combine domain data |

**Related Artifacts:**

- ADR-011: Document Ownership Model
- ADR-012: Interaction Model
- ADR-027: Workflow Definition & Governance
- ADR-028: Reference Document Management
- ADR-029: Contextual Document Resolution
- POL-WS-001: Standard Work Statements

---

## 1. Context

The Combine is evolving toward:

- Schema-driven, document-centric UX
- Multiple UX interaction patterns (gallery, drill-down, editor)
- Workflow-governed actions and state transitions
- LLM-assisted construction based on stable contracts
- Strong auditability and drift prevention

The existing implementation exhibits boundary violations:

- Web routes orchestrate domain services directly
- Jinja templates consume raw domain models and document JSON
- UX logic (classification, formatting, conditional behavior) leaks into templates
- No stable UX-facing contract exists for AI or human construction

These conditions:

- Inhibit UX flexibility
- Prevent safe refactoring of domain/workflow logic
- Increase the risk of architectural drift
- Make AI-assisted work unsafe and non-repeatable

A Backend-for-Frontend (BFF) layer with an explicit ViewModel boundary is required to restore separation of concerns.

---

## 2. Decision

### 2.1 Establish a Backend-for-Frontend (BFF) Layer

A BFF layer is established as the sole interface between UX and the Combine core.

**BFF responsibilities:**

- Orchestrate calls to domain and workflow services
- Shape core outputs into presentation-safe ViewModels
- Compute display-specific fields (labels, grouping, formatting)
- Provide UX-facing URLs and identifiers
- Return HTML (Jinja) and/or JSON to the UX

**BFF non-responsibilities:**

- Business rule enforcement
- Ownership or workflow decisions
- LLM provider communication
- Persistence

### 2.2 Enforce a ViewModel Boundary

All UX templates **MUST** consume ViewModels exclusively.

**Rules:**

- Templates may access `vm` and its child objects only
- Templates **MUST NOT** access:
  - ORM models
  - Raw domain DTOs
  - `document.content` or equivalent raw JSON
- All formatting and presentation shaping occurs in the BFF

**ViewModels are:**

- Immutable
- Presentation-shaped
- Explicit about empty and error states

### 2.3 Constrain Web Routes

Web routes are limited to:

- Detecting HTMX vs full-page requests
- Selecting templates
- Invoking BFF functions
- Passing `vm` to templates

Web routes **MUST NOT:**

- Instantiate or orchestrate domain/workflow services directly
- Perform classification, formatting, or conditional UX logic
- Decide available actions

### 2.4 Domain and Workflow Are HTML-Free

**Hard rule:**

> Domain and workflow services **MUST NEVER** return HTML.

Core services return:

- Domain models
- Structured DTOs
- Workflow-derived state and action availability

Presentation concerns are handled exclusively in the BFF.

---

## 3. Application via Standard Work Statements

Application of this ADR to any new or existing UX surface **MUST** be performed via a Standard Work Statement, as defined by POL-WS-001.

This requirement applies to:

- Refactoring an existing UX route or template to comply with this ADR
- Introducing a new UX surface that consumes Combine domain data
- Extending the BFF/ViewModel pattern to additional document types or views

**Direct, ad-hoc, or interpretive application of this ADR is prohibited.**

---

## 4. Incremental Adoption Strategy

This ADR is intentionally incremental.

**Initial proof scope:**

- Apply ADR-030 to one representative UX surface (Epic Backlog)
- Introduce a BFF function and ViewModel
- Preserve existing Jinja + HTMX behavior
- Do not require dynamic UI schemas or workflow-driven actions in the first pass

**Out of scope for this ADR:**

- Separate deployables for BFF and core
- JSON-defined UI schema formats
- Workflow action semantics
- Cross-client UX reuse

---

## 5. Acceptance Criteria

ADR-030 is considered satisfied when all of the following conditions are met:

1. One representative UX surface (Epic Backlog) has been refactored to:
   - Use a BFF function as the sole orchestration layer
   - Pass a ViewModel (`vm`) to templates
   - Eliminate template access to raw domain models or `document.content`
   - Preserve existing Jinja and HTMX behavior

2. A Standard Work Statement has been written and completed that applies ADR-030 to the representative UX surface.

3. The completed Standard Work Statement:
   - Explicitly references ADR-030 and POL-WS-001
   - Defines the required procedure for applying ADR-030 to a UX surface
   - Is designated as the mandatory mechanism for applying ADR-030 to future UX surfaces

4. No UX changes governed by ADR-030 are implemented outside of a Standard Work Statement.

---

## 6. Consequences

### Positive

- Clear separation between UX and business logic
- Stable UX-facing contracts suitable for AI and human consumers
- Reduced risk of architectural drift
- Incremental, low-risk migration path
- Foundation for schema-driven UI and workflow-derived actions

### Trade-offs

- Additional structure and boilerplate (BFF, ViewModels)
- Requires discipline during transition
- Some duplication of shaping logic by design

---

## 7. Notes

This ADR defines architectural law, not execution procedure.

- Execution discipline is governed by POL-WS-001.
- Procedural details belong exclusively in Standard Work Statements.

---

*End of ADR-030*