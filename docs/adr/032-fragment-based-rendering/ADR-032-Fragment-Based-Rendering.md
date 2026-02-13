# ADR-032: Fragment-Based Rendering for Schema-Driven Documents

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-01-06 |
| **Decision Owner** | Product Owner |
| **Applies To** | All UX document viewers and schema-driven rendering |
| **Related Artifacts** | ADR-030, ADR-031, ADR-010, POL-WS-001 |
| **Execution State** | Complete |

---

## 1. Context

With ADR-031, The Combine standardizes canonical schema types stored in the database and resolved into deterministic bundles for LLM generation and validation.

With ADR-030, the Backend-for-Frontend (BFF) is established as the sole interface between UX and the core domain/workflow layers.

However, UX rendering today still relies on:

- document-specific templates,
- implicit knowledge of JSON structure,
- ad-hoc rendering logic per document type.

To support:

- schema-driven UX,
- reuse of canonical types,
- zero-drift rendering,
- and future dynamic document viewers,

documents must be rendered as compositions of canonical fragments, each fragment corresponding to a canonical schema type.

---

## 2. Decision

### 2.1 Canonical Types Drive Rendering

Every canonical schema type (`schema:<TypeId>`) MAY have a corresponding canonical rendering fragment.

Rendering decisions are based on type identity, not:

- document type,
- property name,
- or inferred JSON shape.

**Rule:**
Rendering logic MUST be determined by canonical schema type identity.

### 2.2 Fragment Registry (DB-Governed)

A Fragment Registry is established as a governed capability.

The registry maintains bindings between:

- `schema_type_id` → `fragment_id`

Fragments are versioned, auditable artifacts and are subject to the same governance expectations as schemas.

The registry enforces:

- one active fragment per (schema_type_id, version)
- explicit activation/deprecation

### 2.3 Flat Document Composition (Schema-Defined)

Documents are rendered from flat JSON objects, where structure is defined entirely by the document schema.

Example:

```json
{
  "epic_set_summary": {...},
  "epics": [...],
  "open_questions": [...],
  "risks_overview": [...]
}
```

The document schema defines:

- property presence
- cardinality (single vs array)
- canonical type via `$ref schema:<TypeId>`

Runtime section tagging (e.g., `sections: [{type,data}]`) is not permitted.

### 2.4 Display Metadata Is Schema-Governed

Document schemas MAY include deterministic display metadata using a namespaced extension:

```json
"x-combine-view": {
  "sections": [
    { "property": "epic_set_summary", "title": "Summary", "order": 10 },
    { "property": "epics", "title": "Epics", "order": 20 },
    { "property": "open_questions", "title": "Open Questions", "order": 40 }
  ]
}
```

**Clarification:**
This metadata lives on the document schema, not on canonical type schemas.

This metadata governs:

- section ordering
- section titles
- visibility rules (e.g., render if present)

Styling and interaction behavior are explicitly out of scope.

### 2.5 Fragment Granularity (Normative)

Fragments render one instance of a canonical type.

Examples:

- `OpenQuestionV1` fragment renders one question
- `RiskV1` fragment renders one risk
- Collection rendering is handled by the viewer, not the fragment

**Rule:**
Fragments MUST NOT assume collection semantics.

This enables reuse across:

- single-item contexts
- list contexts
- nested contexts

### 2.6 Nested Canonical Types

Canonical types MAY reference other canonical types via `$ref`.

Rendering rules:

- A fragment renders only its own type
- If a canonical type contains nested canonical types, the viewer:
  - iterates nested data
  - resolves the nested type
  - invokes the appropriate fragment recursively

Fragments MUST NOT call other fragments directly.

### 2.7 Relationship to BFF Layer (ADR-030)

Fragment-based rendering operates within the BFF boundary.

**Normative flow:**

1. BFF retrieves document data from core services
2. BFF resolves the document schema via SchemaResolver (ADR-031)
3. BFF invokes the Fragment Renderer to compose HTML fragments
4. BFF returns composed HTML to the template layer

**Rules:**

- Templates receive pre-composed HTML, not raw JSON
- Templates access ViewModels only (ADR-030)
- Templates do not perform fragment orchestration

This preserves ADR-030's boundary:

> UX templates are renderers, not orchestrators.

### 2.8 ViewModels vs Raw JSON

Fragments receive ViewModels, not raw domain JSON.

The BFF is responsible for:

- mapping raw domain data to ViewModels
- enforcing presentation-safe defaults

Fragment Renderer operates on ViewModels exclusively.

Fragments MUST NOT:

- access ORM models
- access raw document JSON
- perform business logic

### 2.9 Prohibition on Bespoke Document Templates

**Hard rule (law):**

New document types MUST NOT introduce bespoke document templates.

New document types are created by:

- composing canonical schema types
- reusing existing fragments
- optionally introducing new canonical types and fragments under governance

Exceptions require:

- an explicit ADR
- documented rationale

---

## 3. Migration Path (Non-Normative)

Existing document templates (e.g., `_epic_backlog_content.html`) will be:

- incrementally decomposed into canonical fragments
- reassembled through the Fragment Renderer

Migration is governed via Work Statements per POL-WS-001.

---

## 4. Consequences

### Positive

- New document types require zero new templates
- Rendering is deterministic and schema-driven
- UX, schema, and LLM output stay aligned
- Fragments are testable in isolation
- Eliminates template sprawl

### Trade-offs

- Requires upfront discipline in type definition
- Fragment registry adds governance overhead
- Some UI flexibility is intentionally constrained

---

## 5. Implementation Notes (Non-Normative)

Fragment storage may be implemented as:

- DB-stored markup (fully governed), or
- filesystem markup with DB-governed metadata and hashes

The governance requirement is traceability and versioning, not storage medium.

---

## 6. Acceptance Criteria

ADR-032 is satisfied when:

1. A Fragment Registry exists with:
   - fragment artifacts
   - bindings to canonical schema types

2. At least one canonical type (e.g., `OpenQuestionV1`) has:
   - an accepted schema (ADR-031)
   - an accepted fragment
   - an active binding

3. A document (e.g., Epic Backlog) is rendered by:
   - schema resolution
   - fragment composition
   - no document-specific template logic

4. Adding a new document type requires:
   - no new document template
   - only schema composition and (if needed) new canonical fragments

---

## 7. Out of Scope

- Styling systems and design tokens
- Rich interactivity beyond static rendering
- Fragment authoring tools
- Schema-driven editing (future ADR)

---

*End of ADR-032*