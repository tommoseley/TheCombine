# ADR-071 -- Binder Management & Presentation System

- **Status:** Accepted
- **Date:** 2026-04-08
- **Owner:** Tom

---

## 1. Purpose

Define the architecture for binder management and presentation, establishing how project documents are composed, rendered, and navigated as a coherent system.

This ADR ensures that:

- Documents remain canonical and governed
- Binders provide composition and navigation, not alternate rendering
- Presentation remains consistent across system and UI
- Links are stable, traceable, and user-friendly

---

## 2. Context

The Combine produces structured documents (PD, TA, WS, etc.) that collectively define a project.

Recent evolution introduced:

- Operator-facing pipeline stages (Work Items -> Review & Resolve -> Work Plan)
- Decision support workflows referencing multiple documents
- Need for a final, readable Work Plan artifact

Current state:

- Documents render via IA + block components
- References are text-based (e.g., WS-142)
- Binder concept is implicit and not formally defined
- Rendering exists in both server (markdown) and client (UI), but without an explicit unifying contract

This creates risk of:

- Dual rendering systems
- Inconsistent navigation
- Loss of traceability across document versions
- Unreadable or fragmented final artifacts

---

## 3. Decision

### 3.1 Single Viewer Model

All documents, including binders and the Work Plan, are rendered through the existing IA + block rendering system.

There is no separate binder-specific renderer.

### 3.2 Binder = Composition Layer

A binder is defined as:

> A document that composes and organizes other documents.

Binders:

- Reference existing documents
- Provide grouping, sequencing, and context
- Do not re-render underlying document content differently

Any alternative presentation (e.g., summarized, compact, grouped views) must be implemented as reusable block types within the IA system, not binder-specific transformations.

### 3.3 Presentation via IA + Blocks

Presentation is governed through:

- IA section definitions
- `render_as` hints
- Block components

No template registry or secondary presentation system is introduced.

Enhancements occur through:

- New block types
- Improved IA definitions

### 3.4 First-Class Document Links

All document references are rendered as structured, navigable links:

- Display human-readable titles
- Resolve to governed documents
- Are interactive UI elements (not raw text)

### 3.5 Version-Pinned Link Resolution

Document links resolve to:

> The version used during construction of the referencing document.

Binders must store references as first-class structured fields within the document schema:

```json
{
  "referenced_documents": [
    {
      "document_id": "uuid-here",
      "version": 3,
      "display_id": "WS-142",
      "title": "Local Entity Extractor"
    }
  ]
}
```

Constraints:

- References must not be stored as ad-hoc text or inferred at render time
- This ensures traceability, reproducibility, and audit integrity

### 3.6 Modal Navigation Model

Opening a document link:

- Displays the referenced document in a modal overlay
- Uses the same document viewer
- Does not change the underlying navigation state

This preserves:

- Review context
- User focus
- Navigation simplicity

### 3.7 Dual Rendering Contract

Binder content must support two rendering paths:

**Server-side rendering:**
- Produces markdown for LLM workflows
- Traverses IA section definitions to generate structured text

**Client-side rendering:**
- Produces interactive UI via block components
- Traverses the same IA section definitions to render UI

**Contract:**

Both rendering paths must consume the same IA structure as the source of truth.

- IA defines structure and meaning
- Server renderer outputs markdown from IA
- Client renderer outputs UI from IA

No separate templates or divergent structures are permitted.

### 3.8 Work Plan as Final Binder Artifact

The Work Plan is defined as:

> A binder with an added summary layer.

It includes:

- Executive summary
- Grouped work items
- Decision log
- Dependency context

It is:

- Read-only
- Derived from stabilized documents
- Intended for human consumption

### 3.9 Binder Staleness Awareness

Binders are constructed against specific document versions.

When referenced documents evolve:

- The binder remains pinned to its original versions
- The system must be able to detect when newer versions exist

Future implementations may expose:

- Staleness indicators (e.g., "PD updated from v3 -> v5")
- Prompts to rebuild or refresh the binder

Constraints:

- Version differences between binder references and current documents must be detectable
- Staleness detection must be mechanical, not LLM-based -- it is a version number comparison (`binder_ref.version < current_doc.version`), not a semantic evaluation

---

## 4. Implications

### 4.1 No New Rendering System

- Existing IA/block system is extended
- Avoids duplication and divergence

### 4.2 Traceability is Preserved

- All references are version-pinned
- Users see the exact context used in decision-making

### 4.3 Improved Usability

- Documents become navigable and readable
- Relationships are visible without manual lookup
- Operators remain in context during exploration

### 4.4 Clear Responsibility Boundaries

| Concern | Responsibility |
|---------|---------------|
| Data | Canonical schemas |
| Rendering | IA + blocks |
| Composition | Binder documents |
| Navigation | Link resolution + modal |

### 4.5 Foundation for Future Work

Enables:

- Visualization blocks
- Comparison surfaces
- Enhanced decision embedding
- Richer Work Plan presentation

---

## 5. Constraints

- Canonical schemas remain authoritative
- No duplicate rendering systems
- Links must resolve via governed identity + version
- Binder views are read-only in this phase
- Presentation does not mutate data

---

## 6. Risks

| Risk | Mitigation |
|------|-----------|
| Server/UI rendering divergence | Shared IA structure as single source of truth |
| Overloading IA system | Keep blocks modular and scoped |
| Link resolution complexity | Centralized resolution logic |
| Scope creep into editing | Strict viewer boundary |

---

## 7. Alternatives Considered

**Separate Binder Renderer**
Rejected -- duplicates logic and increases divergence risk.

**Template Registry**
Rejected -- unnecessary abstraction over existing IA/block system.

**Latest-Version Link Resolution**
Rejected -- breaks traceability. Users must see the version that was used during construction.

---

## 8. Next Steps

1. Implement WPC-001: Link Resolution & Modal Navigation
2. Implement WPC-002: Binder Composition (via IA + blocks)
3. Implement WPC-003: Work Plan Viewer (binder + summary layer)

---

*Binders are documents. The viewer is singular. Composition, not duplication, is the model.*
