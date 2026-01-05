# ADR-011-Part-2 â€” Document Ownership Model (Implementation & Enforcement)

**Status:** Draft (v0.92)  
**Extends:** ADR-011 â€” Document Ownership Model  
**Related ADRs:**
- ADR-009 â€” Audit & Governance
- ADR-010 â€” LLM Execution Logging
- ADR-011 â€” Document Ownership Model (Conceptual)
- ADR-027 â€” Workflow Definition & Governance

---

## 1. Purpose

ADR-011 defines the conceptual ownership model: documents may own other documents, creating explicit scope boundaries.

This ADR completes that decision by defining:

- How ownership is persisted
- How ownership is enforced
- How ownership is queried
- What guarantees exist at runtime
- What remains intentionally out of scope for MVP

This ADR exists to make document ownership mechanically real, not merely conceptual.

---

## 2. Persistence Model

### 2.1 Canonical Ownership Field

Each document MAY be owned by at most one parent document.

Ownership is persisted using a self-referential foreign key:

```
documents.parent_document_id â†’ documents.id
```

**Properties:**
- Nullable (root documents have no owner)
- Enforces exclusivity (one owner maximum)
- Indexed for child traversal
- Ownership is directional and asymmetric

Ownership MUST NOT be represented using DocumentRelation. Typed relations remain for non-ownership edges only.

### 2.2 ORM Relationships

The Document model MUST expose:

- `document.parent`
- `document.children`

These relationships are authoritative for ownership traversal and UI rendering.

---

## 3. Ownership Enforcement Rules

Ownership enforcement occurs at the service layer. Database constraints alone are insufficient.

### 3.1 Exclusivity

A document MUST have at most one parent.

This is structurally enforced by the single `parent_document_id` field.

### 3.2 Acyclic Constraint (DAG)

Ownership relationships MUST form a Directed Acyclic Graph (DAG).

The system MUST reject any operation that would introduce a cycle.

**Minimum required write-time check (normative):**

On setting `child.parent_document_id = proposed_parent_id`, the system MUST walk the parent chain from `proposed_parent_id` upward.

If the chain contains `child.id`, the write MUST fail explicitly.

This prevents:
- Self-ownership
- Ancestor loops
- Any cycle formed via reassignment

**Depth guard (recommended, not required for correctness):**

Implementations MAY impose a maximum chain depth to prevent pathological structures from degrading performance.

### 3.3 Scope Consistency

Each document has a declared scope (e.g., project, epic, story). Scope ordering MUST be explicit.

#### 3.3.1 Canonical Scope Ordering

The system defines the following ordering:

| Scope | Rank | Notes |
|-------|------|-------|
| organization | 400 | Optional / if implemented |
| project | 300 | Root for most workflows |
| epic | 200 | Child of project |
| story | 100 | Child of epic |
| file | 0 | Leaf (code files, assets) |

**Rule:**

Child scope rank MUST be â‰¤ parent scope rank.

This prevents invalid structures such as a project document being owned by a story document.

Scope validation is enforced at write time.

### 3.4 Workflow-Declared Ownership

Workflow definitions (ADR-027) declare which document types may own others.

**Enforcement occurs in two layers:**

1. **Hard invariants** (always enforced):
   - Single parent
   - No cycles
   - Scope ordering

2. **Workflow constraints** (enforced when workflows are active):
   - Parent/child document types MUST conform to the active workflow's ownership rules

ADR-011-Part-2 does not define workflow schemas; it enforces their declared constraints.

---

## 4. Reference Constraints (Interaction with Ownership)

Ownership defines structural hierarchy. References define dependency edges.

This section governs generation/derivation dependencies, not UI display.

### 4.1 Dependency Rules (Generation / Derivation)

- Child â†’ Parent dependency: permitted
- Child â†’ Ancestor dependency: permitted
- Parent â†’ Child dependency: forbidden by default
- Sibling â†’ Sibling dependency: forbidden by default
- Cross-branch dependency: forbidden by default

### 4.2 Non-Dependency Usage (UI / Navigation)

This ADR does not forbid a parent document from:
- listing its children
- linking to its children
- showing child summaries in the UI

Those are navigation/display concerns, not derivation dependencies.

---

## 5. Deletion Semantics

Deletion of documents with children is restricted.

**Rules:**
- A document with one or more children MUST NOT be deleted by default
- Attempted deletion MUST fail explicitly with a structured error
- Cascading deletion MAY be introduced later via governed operations

### 5.1 Orphan Resistance and DB Constraints

The system MUST prevent orphaning via normal application operations.

**Database behavior selection (normative):**

`ON DELETE RESTRICT` (or equivalent) MUST be used for `parent_document_id` to prevent deleting a parent with children through normal DB operations.

**Defense-in-depth (recommended):**

Periodic orphan detection MAY exist as a maintenance operation to detect corruption caused by out-of-band DB changes.

---

## 6. Query & UI Requirements

The ownership model MUST support:

- Query: "all children of this document"
- Query: "entire subtree rooted at document X"
- UI traversal of ownership hierarchies

**Examples:**
- Epic Backlog â†’ Epics
- Epic â†’ Story Backlog
- Story Backlog â†’ Stories

These queries MUST rely on `parent_document_id`, not inference.

---

## 7. Migration Path

Adding ownership persistence introduces a transition period.

**Minimum safe migration rule:**

All existing documents MUST default to `parent_document_id = NULL` (root) unless explicitly assigned by governed operations.

Retroactive inference based on document type is not permitted by default because it introduces silent corrections and risks incorrect ownership assignment.

A governed, explicit migration MAY be introduced later if needed.

---

## 8. Required Tests

The following test categories are REQUIRED for compliance:

| Test Category | Description |
|---------------|-------------|
| **Hierarchy Creation** | Valid parent/child assignment |
| **Cycle Prevention** | Self-ownership, ancestor loops |
| **Scope Violation** | Child scope exceeding parent |
| **Workflow Ownership Violation** | Parent/child type not allowed by workflow |
| **Deletion Guard** | Prevent deletion when children exist |

Passing these tests is required to claim ADR-011 implementation completeness.

---

## 9. Out of Scope (Explicit)

This ADR does not define:

- UI rendering details
- Workflow schema design
- Reference graph enforcement beyond ownership + dependency rules stated here
- Bulk or cascading deletion semantics
- Visualization of DAGs beyond tree traversal

These concerns are governed elsewhere.

---

## 10. Completion Criteria

ADR-011 is considered fully implemented when:

1. Ownership is persisted via `parent_document_id`
2. DAG and scope enforcement exist
3. Deletion guard exists
4. Child traversal is queryable
5. Required tests pass

UI enhancements MAY follow independently.

---

## 11. Implementation Order (Non-Normative Guidance)

Recommended sequence:

1. Schema migration (`parent_document_id` + FK + index)
2. ORM relationships (`parent`, `children`)
3. Deletion guard
4. Cycle detection (write-time check)
5. Scope validation (requires canonical scope ordering)
6. Tests for all five categories
7. UI traversal queries

---

**Document Version:** 0.92  
**Last Updated:** 2026-01-05  
**Author:** Tom Moseley