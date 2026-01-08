# ADR-034-B: Flatten-First Canonical Data, Hierarchy as View

| | |
|---|---|
| **Amendment** | ADR-034-B |
| **Parent ADR** | ADR-034 (Document Composition Manifest) |
| **Status** | Accepted |
| **Type** | Design Decision Clarification |
| **Date** | 2026-01-08 |
| **Predecessor** | WS-ADR-034-EXP2 (Structural Variety + Deep-Nesting Probe) |

---

## Decision

The Combine will prefer **flat canonical data structures with explicit references** over deeply nested hierarchical arrays when modeling related work items (e.g., Epics ↔ Stories, Epics ↔ Open Questions, Risks, Dependencies).

Hierarchy (e.g., "stories under an epic") is treated as a **presentation and composition concern**, produced by RenderModelBuilder + container blocks, not as a requirement of canonical payload shape.

---

## Rationale

### 1. Separation of Concerns

- **Generation (LLM)** produces structured data — that's where intelligence belongs
- **Rendering/composition** remains mechanical and deterministic
- Avoids pushing "intelligence" into RenderModelBuilder

### 2. Canonical Reuse

- Item schemas (e.g., `OpenQuestionV1`, future `StoryV1`) should not depend on parent document structures
- Container blocks can group items by reference without nesting
- Same container block can appear in multiple document contexts

### 3. Queryability and Defensibility

- Flat structures support cross-cutting queries and audits (e.g., "all blocking questions across epics") without complex traversal
- Avoids hidden coupling created by nested hierarchies
- Better for audit, search, and future UI features (filter/sort)

### 4. Avoiding a DocDef DSL Trap

- Extending document definition semantics toward recursive iteration and wildcard traversal increases complexity and governance risk
- The system favors explicit, minimal composition semantics
- Nested `repeat_over` is one step from conditionals, which is one step from loops

---

## Clarification: Section 8.6 Compatibility

ADR-034 Section 8.6 states: *"Flattening domain data to satisfy rendering is prohibited."*

This amendment is **compatible** with that constraint. The distinction:

| Constraint | Meaning |
|------------|---------|
| **8.6 (original)** | Do not take existing hierarchical domain data and flatten it post-hoc to satisfy a rendering limitation |
| **Flatten-first (this amendment)** | Generate flat canonical structures *from the start* as the authoritative output format |

The LLM produces flat structures with explicit references as the **canonical form**. This is not "flattening to satisfy rendering" — it is defining the canonical schema shape. Container blocks then produce hierarchical *views* during rendering.

**Key distinction:** The hierarchy exists in the *view layer*, not the *canonical data layer*. Domain relationships are preserved via explicit references (e.g., `story.epic_id`), not via nested containment.

---

## Documented Boundary (from WS-ADR-034-EXP2)

Per WS-ADR-034-EXP2 findings:

> **Container sections support at most one level of parent iteration via `repeat_over`.**
>
> `source_pointer` resolves relative to the `repeat_over` parent and does not support nested array wildcard traversal (e.g., `/epics/*/capabilities/*/...`) in the current design boundary.

This boundary is **intentional** and aligns with the flatten-first decision.

---

## Implications

### For Multi-Level Structures

For structures like Epics → Story Backlogs → Stories, canonical output should be **flat with references**:

```json
{
  "epics": [
    {"id": "E-001", "title": "User Authentication"}
  ],
  "stories": [
    {"id": "S-001", "epic_id": "E-001", "title": "Login form"},
    {"id": "S-002", "epic_id": "E-001", "title": "Password reset"}
  ]
}
```

### For Rendering

Container blocks (e.g., `StoriesBlockV1`) present hierarchical views by grouping/filtering mechanically during render model construction, without requiring deep nested traversal.

The mental model shift is in the **implementation**, not the **user experience** — users still see hierarchy in the UI.

---

## Non-Goals

- No changes to PromptAssembler
- No changes to RenderModelBuilder to support recursive iteration or wildcard traversal
- No docdef extensions (e.g., nested `repeat_over`) are introduced by this decision

---

## Future Considerations

If a concrete use case emerges requiring true multi-level nesting, options include:

1. **Flatten upstream** — LLM pre-groups into single-level nesting during generation
2. **Nested repeat_over syntax** — e.g., `repeat_over: ["/epics", "/capabilities"]` (cautioned against)
3. **Builder enhancement** — Support recursive iteration in RenderModelBuilder (cautioned against)

Option 1 is preferred per this decision.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-08 | Initial amendment based on WS-ADR-034-EXP2 findings |

---

*End of Amendment*

