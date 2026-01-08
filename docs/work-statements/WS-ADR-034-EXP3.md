# WS-ADR-034-EXP3: Stories Grouped Under Epics (Second Container Type)

| | |
|---|---|
| **Work Statement** | WS-ADR-034-EXP3 |
| **Title** | Stories Grouped Under Epics via StoriesBlockV1 (Second Container Type) |
| **Related ADRs** | ADR-034, ADR-034-B, ADR-033, ADR-031 |
| **Predecessor** | WS-ADR-034-EXP, WS-ADR-034-EXP2 |
| **Status** | Complete |
| **Expected Scope** | Small multi-commit |
| **Owner** | Tom |
| **Primary Risk** | Accidentally creating a docdef DSL (filters/wildcards) or reintroducing deep nesting requirements |
| **Created** | 2026-01-08 |

---

## Purpose

Prove that stories can be rendered grouped under epics using:

- Single-level nesting (`/epics[].stories[]`) — already supported
- A second container block type (`StoriesBlockV1`)
- Existing container composition (`shape: container` + `repeat_over: /epics`)

**Without** deep nested traversal, wildcard pointers, or filter DSL.

This validates that the container pattern **generalizes** beyond OpenQuestionsBlockV1.

---

## Design Clarification: "Flatten-First" Interpretation

Per ADR-034-B discussion:

> **"Flatten-first" = avoid deep nesting and wildcard traversal.** It does not mean "no nesting whatsoever."

Single-level nesting (`/epics[].stories[]`) is:
- Already supported by the builder boundary (proven in EXP1/EXP2)
- Avoids any docdef filter DSL
- Keeps stories queryable via `epic_id` on each story
- Keeps EXP3 focused on proving: **second container type generalizes**

---

## Canonical Payload Shape

```json
{
  "epics": [
    {
      "id": "E-001",
      "title": "Epic 1",
      "stories": [
        {"id": "S-001", "epic_id": "E-001", "title": "Story 1", "description": "...", "status": "draft"}
      ]
    }
  ]
}
```

---

## DocDef Section Configuration

```python
{
    "section_id": "epic_stories",
    "component_id": "component:StoriesBlockV1:1.0.0",
    "shape": "container",
    "source_pointer": "/stories",   # Relative to each epic
    "repeat_over": "/epics",
    "context": {"epic_id": "/id", "epic_title": "/title"}
}
```

No filters. No absolute-root deref. No DSL.

---

## Invariants

No changes to:
- RenderModel schemas
- PromptAssembler
- Container iteration boundary (one `repeat_over` level)
- OpenQuestionsBlockV1 schema/component/fragment

---

## Scope

### In Scope

1. **Canonical schemas**
   - `schema:StoryV1`
   - `schema:StoriesBlockV1`

2. **Canonical components**
   - `component:StoryV1:1.0.0` with generation guidance and web fragment binding
   - `component:StoriesBlockV1:1.0.0` (render-only container)

3. **Web fragments**
   - `StoryV1Fragment` — item display (card/row)
   - `StoriesBlockV1Fragment` — container that iterates and delegates

4. **Test docdef**
   - `docdef:StoryBacklogTest:1.0.0`
   - `repeat_over: /epics`, `source_pointer: /stories`, `shape: container`

5. **Tests + fixtures**
   - Fixture with 2 epics, 5 stories split across them
   - Validate correct grouping per epic
   - Full regression suite

### Out of Scope

- No deep nesting (`/epics/*/stories/*`) in canonical payload
- No docdef wildcard traversal
- No generalized filter language in docdef
- No story lifecycle workflows beyond rendering

---

## Acceptance Criteria

1. `schema:StoryV1` and `schema:StoriesBlockV1` exist and are accepted
2. `component:StoryV1:1.0.0` and `component:StoriesBlockV1:1.0.0` exist with web fragment bindings
3. Render preview shows:
   - For each epic, exactly one StoriesBlock container
   - Each StoriesBlock contains only stories from that epic
4. No HTML in JSON payloads
5. Existing docdefs remain unchanged
6. Full test suite passes

---

## Decision Gate

After completion, answer:

- Does the container pattern generalize to a second type?
- Is single-level nesting sufficient for hierarchical UX?
- Any pressure to introduce docdef filters/wildcards? If yes, why?

---

## Rollback Plan

Revert docdef + fragments + schema/component additions if needed.
Canonical artifacts from EXP1 remain unchanged.

---

## Procedure

### PHASE 1: Canonical Schemas

Add to `seed_schema_artifacts.py`:
- `STORY_V1_SCHEMA`
- `STORIES_BLOCK_V1_SCHEMA`

### PHASE 2: Canonical Components

Add to `seed_component_artifacts.py`:
- `STORY_V1_COMPONENT`
- `STORIES_BLOCK_V1_COMPONENT`

Add fragment aliases to `fragment_registry_service.py`.

### PHASE 3: Web Fragments

Add to `seed_fragment_artifacts.py`:
- `StoryV1Fragment`
- `StoriesBlockV1Fragment`

### PHASE 4: Test DocDef

Add `docdef:StoryBacklogTest:1.0.0` to `seed_component_artifacts.py`.

### PHASE 5: Tests

- Schema validation tests
- RenderModel container tests
- Integration tests with 2-epic/5-story fixture

### PHASE 6: Seed and Verify

Run seeds, test via preview endpoints.

### PHASE 7: Final Verification

Confirm acceptance criteria, answer decision gate questions.

---

## Findings

### Container Pattern Generalization: ✅ SUCCESS

**Result:** StoriesBlockV1 works identically to OpenQuestionsBlockV1 using the same machinery.

```json
{
  "document_def_id": "docdef:StoryBacklogTest:1.0.0",
  "blocks": [
    {
      "type": "schema:StoriesBlockV1",
      "key": "epic_stories:container:0",
      "data": {
        "items": [
          {"id": "S-001", "epic_id": "E-001", "title": "Login form", ...},
          {"id": "S-002", "epic_id": "E-001", "title": "Password reset", ...}
        ]
      },
      "context": {"epic_id": "E-001", "epic_title": "User Authentication"}
    },
    {
      "type": "schema:StoriesBlockV1",
      "key": "epic_stories:container:1",
      "data": {
        "items": [
          {"id": "S-003", "epic_id": "E-002", "title": "Metrics overview", ...}
        ]
      },
      "context": {"epic_id": "E-002", "epic_title": "Dashboard"}
    }
  ]
}
```

---

### Decision Gate Answers

| Question | Answer |
|----------|--------|
| Does the container pattern generalize to a second type? | **Yes.** StoriesBlockV1 required zero changes to RenderModelBuilder. |
| Is single-level nesting sufficient for hierarchical UX? | **Yes.** Stories grouped under epics renders correctly. |
| Any pressure to introduce docdef filters/wildcards? | **No.** Single-level nesting avoids the need for filters entirely. |

---

### Implementation Notes

**Behavior refinement during EXP3:** Container shape with `repeat_over` now produces **one block per parent** (not one block total). This is the correct semantic for "grouped by parent" display.

- `nested_list`: N blocks (one per item)
- `container` without `repeat_over`: 1 block (all items)
- `container` with `repeat_over`: N blocks (one per parent, each containing that parent's items)

This refinement was applied to RenderModelBuilder and all tests updated accordingly.

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-08 | Initial draft |

---

*End of Work Statement*

