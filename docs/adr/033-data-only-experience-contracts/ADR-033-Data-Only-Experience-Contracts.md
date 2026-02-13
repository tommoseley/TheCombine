# ADR-033: Data-Only Experience Contracts and Render Model Standard

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-01-06 |
| **Decision Owner** | Product Owner |
| **Applies To** | All Experience/BFF JSON contracts and multi-channel viewers |
| **Related Artifacts** | ADR-030, ADR-031, ADR-032, ADR-010, POL-WS-001 |
| **Execution State** | null |

---

## 1. Context

The Combine is evolving toward schema-driven, document-centric UX where canonical types (ADR-031) unify generation, validation, and viewing. ADR-030 establishes the BFF/Experience boundary so UX does not consume core domain models directly. ADR-032 establishes schema-driven composition and fragment-based rendering for the web channel.

Recent implementation work introduced HTML-bearing fields in ViewModels (e.g., `rendered_open_questions`), which couples experience contracts to web rendering and blocks multi-channel reuse.

The Combine requires:

- Data-only Experience contracts
- A Render Model standard that is channel-neutral
- Web rendering that remains schema-driven (ADR-032) but does not leak HTML into contracts
- Auditability that ties view data back to the schema bundle used (ADR-031)

---

## 2. Decision

### 2.1 Data-Only Contract Rule

**Hard rule (law):**
All Experience/BFF JSON responses MUST be data-only. They MUST NOT include HTML or other rendered markup.

This rule applies to:

- Experience/BFF endpoints returning JSON
- Any structured JSON contract consumed by a client renderer (web/mobile/CLI)

This rule does not apply to:

- Server-rendered page routes that return complete HTML documents (see 2.6)

### 2.2 Render Model Is the Canonical Experience Contract

The Experience/BFF layer SHALL return a canonical Render Model representation that is:

- channel-neutral JSON
- composed of typed blocks aligned to canonical schema types
- ordered and titled via governed display metadata
- auditable via schema bundle identity

Clients render from the Render Model; they do not interpret raw stored document JSON or ORM models.

### 2.3 Render Model Structure

A Render Model MUST contain:

**Provenance**
- `render_model_version`
- `document_id`
- `document_type`
- `schema_id`
- `schema_bundle_sha256` (from ADR-031 bundle resolution)

**View framing**
- `title` (optional `subtitle`)
- `sections[]` ordered deterministically

**Typed content**
- each section contains `blocks[]`
- each block has:
  - `type` (canonical type id, e.g., `schema:OpenQuestionV1`)
  - `data` (conforms to that canonical type)

**Actions (optional)**
- `actions[]` with `id`, `label`, `method`, `href`

**Normative shape (conceptual):**

```json
{
  "render_model_version": "1.0",
  "document_id": "…",
  "document_type": "epic_backlog",
  "schema_id": "schema:EpicBacklogV2",
  "schema_bundle_sha256": "sha256:…",
  "title": "Epic Backlog",
  "sections": [
    {
      "id": "open_questions",
      "title": "Open Questions",
      "order": 40,
      "blocks": [
        { "type": "schema:OpenQuestionV1", "data": { /* OpenQuestionV1 */ } }
      ]
    }
  ],
  "actions": [
    { "id": "build", "label": "Build", "method": "POST", "href": "/bff/…" }
  ]
}
```

### 2.4 Mapping Responsibility and Legacy Compatibility

The Experience/BFF layer is responsible for mapping:

> Stored Document Content (including legacy shapes during migration)
> → into Render Model blocks that conform to canonical types.

**Rule:** clients MUST NOT be required to interpret legacy storage formats.

This is the sanctioned place for compatibility adapters during migration.

### 2.5 Relationship to ADR-032 (Fragment-Based Rendering)

ADR-032 defines schema-driven fragment rendering for the web channel.

Under ADR-033:

- Experience/BFF returns Render Model (data-only)
- Web rendering consumes blocks and renders HTML using web templates/fragments
- Fragment rendering is a web channel concern, not an Experience contract concern

**Normative implication:**
The FragmentRenderer MUST NOT be invoked inside Experience/BFF endpoints that produce JSON contracts.

### 2.6 Page Routes vs Experience API Endpoints

This ADR governs Experience/BFF JSON contracts.

Server-rendered page routes that return complete HTML documents (e.g., Jinja templates) are permitted and are not constrained by the "no HTML in contracts" rule, because they are not Experience contracts—they are rendered views.

However, page routes MUST still respect ADR-030 boundaries:

- they must not consume domain models directly
- they should render from Experience/BFF-provided data models (Render Model or equivalent)

### 2.7 ViewModels vs Generic Blocks

Typed ViewModels are permitted only if they are:

- data-only
- derived from canonical schema types
- equivalent in expressiveness to blocks (i.e., representable as `blocks[]`)

**Preference (target direction):**
Experience contracts should converge on the generic Render Model structure (`sections[]` + `blocks[]`) for maximum reuse and consistent rendering across channels.

### 2.8 Render Model Versioning

`render_model_version` is governed.

- Backward-compatible changes increment minor (e.g., 1.1)
- Breaking changes require major (e.g., 2.0)
- Breaking major versions require explicit migration and compatibility strategy via Work Statements

### 2.9 Separation of Concerns (Hard Rule)

Experience/BFF APIs return data-only Render Models; rendering is performed by the channel.

---

## 3. Consequences

### Positive

- Contracts become channel-neutral and reusable
- Web no longer dictates architectural shape
- Canonical types unify LLM output, validation, and viewing
- Blocks become testable and replayable
- Prevents "HTML creep" into API contracts

### Trade-offs

- Web rendering must iterate blocks and call its renderer
- Requires explicit Render Model spec/versioning discipline
- Short-term refactor required to remove HTML-bearing contract fields

---

## 4. Resolution of Current Conflict (Normative)

Any HTML-bearing fields introduced into Experience/BFF JSON contracts (e.g., `rendered_open_questions`) violate this ADR.

**Required remediation pattern:**

1. Replace HTML fields with typed blocks (data-only)
2. Render HTML in the web layer by iterating blocks and invoking the web renderer

---

## 5. Acceptance Criteria

ADR-033 is satisfied when:

1. At least one Experience/BFF JSON endpoint returns a Render Model response including:
   - `schema_bundle_sha256`
   - at least one block conforming to a canonical type (e.g., `OpenQuestionV1`)

2. No Experience/BFF JSON endpoint includes HTML in its contract.

3. The web channel renders at least one document view from Render Model blocks by iterating blocks and rendering them using web templates/fragments.

4. Render Model versioning rules are documented and enforced for at least one backward-compatible change.

---

## 6. Out of Scope

- Design tokens, styling systems
- Interactive editing
- Component authoring tools
- Non-web renderers beyond proof-of-concept

---

*End of ADR-033*