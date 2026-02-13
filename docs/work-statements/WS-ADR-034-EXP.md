# WS-ADR-034-EXP: Container Block Proof of Concept — OpenQuestionsBlockV1

| | |
|---|---|
| **Work Statement** | WS-ADR-034-EXP |
| **Title** | Container Block Proof of Concept — OpenQuestionsBlockV1 |
| **Related ADRs** | ADR-034, ADR-033, ADR-031 |
| **Status** | Complete |
| **Expected Scope** | Small multi-commit |
| **Owner** | Tom |
| **Primary Risk** | Introducing a structural abstraction that adds complexity without clear value |
| **Created** | 2026-01-08 |

---

## Purpose

Prove that the Combine can render a section-level container block that contains a list of existing item components, using the ADR-034 composition pipeline and ADR-033 rendering model—without schema drift, prompt duplication, or HTML leakage.

This experiment validates **rendering composition only**, not prompt-generation generalization.

---

## Design Decisions (Explicit for This WS)

### D1 — Document Definition Versioning

A new document definition version will be introduced:

- ``docdef:EpicBacklog:1.1.0``

The existing ``docdef:EpicBacklog:1.0.0`` remains unchanged to allow comparison.

### D2 — Shape Semantics

A new section shape is introduced for this experiment only:

```
"shape": "container"
```

Behavior:
- A ``container`` section produces **one** RenderBlock
- No implicit repetition
- No automatic wrapping based on schema inspection

### D3 — Fragment Delegation Mechanism

Container fragments may render child items by:
- Using Jinja ``{% include %}`` to include the item fragment
- Fragment resolution performed via ``FragmentRegistryService``

No new fragment execution model is introduced.

### D4 — Context Propagation

- Context is passed to the container block
- Container fragment is responsible for explicitly passing context to item fragments during iteration
- No implicit context inheritance is introduced

### D5 — Prompt Assembly Scope

For this WS:
- **Container blocks are render-only**
- PromptAssembler behavior is unchanged
- Prompt bullets continue to be collected from item-level components (``OpenQuestionV1``)
- Container component guidance may be minimal and is **not used** for prompt assembly

---

## Scope

### In Scope

1. **Canonical container schema**
   - Add ``schema:OpenQuestionsBlockV1``
   - Contains:
     - ``items: OpenQuestionV1[]``
     - Optional derived metadata (non-authoritative)

2. **Canonical container component**
   - Add ``component:OpenQuestionsBlockV1:1.0.0``
   - Web fragment binding defined
   - Minimal generation guidance

3. **RenderModelBuilder support**
   - Emit a single ``RenderBlockV1`` for container sections
   - Block type = ``schema:OpenQuestionsBlockV1``

4. **Document definition**
   - Introduce ``docdef:EpicBacklog:1.1.0``
   - Uses ``shape: "container"`` for Open Questions rendering
   - Prompt assembly remains aligned with item-level sections

5. **Web rendering**
   - Container fragment renders section and delegates item rendering to ``OpenQuestionV1``

6. **Tests**
   - Schema validation
   - RenderModel validation
   - Rendering correctness
   - No regressions

### Out of Scope

- No general container framework or pattern documentation
- No prompt traversal changes
- No reuse validation across other schemas
- No new UI behaviors
- No persistence or lineage changes

---

## Acceptance Criteria

1. **Canonical artifacts**
   - ``schema:OpenQuestionsBlockV1`` exists and is ``accepted``
   - ``component:OpenQuestionsBlockV1:1.0.0`` exists with:
     - Correct schema reference
     - Generation guidance present (minimal)
     - Web fragment binding defined

2. **Render model correctness**
   - Render preview includes a single ``RenderBlockV1`` with:
     - ``type = schema:OpenQuestionsBlockV1``
     - ``data.items[]`` conforming to ``schema:OpenQuestionV1``
   - RenderModel validation passes

3. **Rendering composition**
   - Web UI renders Open Questions as one container section
   - Item rendering is delegated to the existing OpenQuestion fragment
   - No HTML appears in JSON payloads

4. **Regression safety**
   - Existing documents and previews continue to function
   - Automated tests pass

---

## Success Criteria Beyond Acceptance (Decision Gate)

After completion, we must be able to answer:

- Did container blocks reduce template-level orchestration logic?
- Did they clarify section-level semantics?
- Did they avoid hidden coupling in RenderModelBuilder?

**If the benefit is unclear, container blocks should not be generalized.**

---

## Non-binding Note

A subsequent Work Statement may validate reuse of this container block across other document contexts where ``open_questions`` appears, without renderer changes.

---

## Rollback Plan

- Revert ``docdef:EpicBacklog:1.1.0``
- Remove container schema/component if needed
- No upstream schema or prompt behavior is retained

---

## Procedure

Execute phases in order.

---

### PHASE 1: Canonical Schema

#### Step 1.1: Add OpenQuestionsBlockV1 Schema

**Action:** Add to ``seed_schema_artifacts.py``

**Schema ID:** ``schema:OpenQuestionsBlockV1``

```python
OPEN_QUESTIONS_BLOCK_V1_SCHEMA = {
    "$id": "schema:OpenQuestionsBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "title": "Open Questions Block",
    "description": "Container block for a list of open questions within a section context.",
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "items": {"$ref": "schema:OpenQuestionV1"},
            "description": "List of open questions"
        },
        "total_count": {
            "type": "integer",
            "minimum": 0,
            "description": "Total count of questions (derived, non-authoritative)"
        },
        "blocking_count": {
            "type": "integer",
            "minimum": 0,
            "description": "Count of blocking questions (derived, non-authoritative)"
        }
    },
    "additionalProperties": false
}
```

Add to ``INITIAL_SCHEMA_ARTIFACTS``:
```python
{
    "schema_id": "OpenQuestionsBlockV1",
    "version": "1.0",
    "kind": "type",
    "status": "accepted",
    "schema_json": OPEN_QUESTIONS_BLOCK_V1_SCHEMA,
    "governance_refs": {
        "adrs": ["ADR-034"],
        "policies": []
    },
},
```

**Verification:** Schema definition valid, added to seed list.

---

### PHASE 2: Canonical Component

#### Step 2.1: Add OpenQuestionsBlockV1 Component

**Action:** Add to ``seed_component_artifacts.py``

```python
OPEN_QUESTIONS_BLOCK_V1_COMPONENT = {
    "component_id": "component:OpenQuestionsBlockV1:1.0.0",
    "schema_id": "schema:OpenQuestionsBlockV1",
    "generation_guidance": {
        "bullets": [
            "This is a container block for rendering; generation guidance is minimal.",
            "Item-level guidance is provided by OpenQuestionV1."
        ]
    },
    "view_bindings": {
        "web": {
            "fragment_id": "fragment:OpenQuestionsBlockV1:web:1.0.0"
        }
    },
    "status": "accepted"
}
```

Add to ``INITIAL_COMPONENT_ARTIFACTS``.

Add alias to ``fragment_registry_service.py``:
```python
FRAGMENT_ALIASES = {
    "fragment:OpenQuestionV1:web:1.0.0": "OpenQuestionV1Fragment",
    "fragment:OpenQuestionsBlockV1:web:1.0.0": "OpenQuestionsBlockV1Fragment",
}
```

**Verification:** Component definition valid, alias registered.

---

### PHASE 3: Container Fragment

#### Step 3.1: Add OpenQuestionsBlockV1 Fragment

**Action:** Add to ``seed_fragment_artifacts.py``

**Fragment ID:** ``OpenQuestionsBlockV1Fragment``

**Template Markup:**
```html
<div class="open-questions-block" data-block-type="OpenQuestionsBlockV1">
  {% if block.context %}
  <div class="block-context text-sm text-gray-500 mb-2">
    {% if block.context.epic_title %}Epic: {{ block.context.epic_title }}{% endif %}
  </div>
  {% endif %}
  
  <div class="questions-list space-y-4">
    {% for item in block.data.items %}
      {% set item_block = {"type": "schema:OpenQuestionV1", "data": item, "context": block.context} %}
      {% include "fragments/OpenQuestionV1Fragment.html" %}
    {% endfor %}
  </div>
  
  {% if block.data.items | length == 0 %}
  <p class="text-gray-400 italic">No open questions.</p>
  {% endif %}
</div>
```

**Verification:** Fragment registered, template syntax valid.

---

### PHASE 4: RenderModelBuilder Enhancement

#### Step 4.1: Add Container Shape Support

**Action:** Modify ``app/domain/services/render_model_builder.py``

In ``_process_section()``, add handling for ``shape == "container"``:

```python
elif shape == "container":
    # Container shape: produce ONE block containing all items
    # source_pointer resolves to array, becomes block.data.items
    items = self._resolve_pointer(document_data, source_pointer)
    
    if repeat_over:
        # For nested containers: iterate parents, collect all items
        parents = self._resolve_pointer(document_data, repeat_over)
        all_items = []
        contexts = []
        if parents and isinstance(parents, list):
            for parent in parents:
                if isinstance(parent, dict):
                    parent_items = self._resolve_pointer(parent, source_pointer)
                    if parent_items and isinstance(parent_items, list):
                        context = self._build_context(parent, context_mapping)
                        for item in parent_items:
                            all_items.append(item)
                            contexts.append(context)
        
        if all_items:
            # Single container block with all items
            blocks.append(RenderBlock(
                type=schema_id,
                key=f"{section_id}:container",
                data={"items": all_items},
                context=contexts[0] if contexts else None,  # First parent context
            ))
    else:
        # Simple container: items directly from source_pointer
        if items and isinstance(items, list):
            blocks.append(RenderBlock(
                type=schema_id,
                key=f"{section_id}:container",
                data={"items": items},
                context=None,
            ))
```

**Verification:** Container shape produces single block with items array.

---

### PHASE 5: Document Definition

#### Step 5.1: Add EpicBacklog v1.1.0

**Action:** Add to ``seed_component_artifacts.py``

```python
EPIC_BACKLOG_V1_1_DOCDEF = {
    "document_def_id": "docdef:EpicBacklog:1.1.0",
    "document_schema_id": None,
    "prompt_header": {
        "role": "You are a Business Analyst creating an Epic Backlog for a software project.",
        "constraints": [
            "Output valid JSON matching the document schema.",
            "Be specific and actionable.",
            "Do not invent requirements not supported by inputs.",
            "Each epic must have at least one open question if unknowns exist."
        ]
    },
    "sections": [
        {
            "section_id": "epic_open_questions",
            "title": "Open Questions",
            "description": "Questions requiring human decision before implementation",
            "order": 10,
            "component_id": "component:OpenQuestionsBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/open_questions",
            "repeat_over": "/epics",
            "context": {
                "epic_id": "/id",
                "epic_title": "/title"
            }
        }
    ],
    "status": "accepted"
}
```

Add to ``INITIAL_DOCUMENT_DEFINITIONS``.

**Note:** prompt_header identical to v1.0.0 — prompt assembly unchanged per D5.

**Verification:** DocDef seeds correctly, uses container shape.

---

### PHASE 6: Tests

#### Step 6.1: Schema Validation Test

**Action:** Add to ``tests/domain/test_seed_schema_artifacts.py`` or create new test file.

```python
def test_open_questions_block_schema_valid():
    """OpenQuestionsBlockV1 schema is well-formed."""
    schema = OPEN_QUESTIONS_BLOCK_V1_SCHEMA
    assert schema["$id"] == "schema:OpenQuestionsBlockV1"
    assert "items" in schema["properties"]
    assert schema["properties"]["items"]["type"] == "array"
```

#### Step 6.2: RenderModel Container Test

**Action:** Add to ``tests/domain/test_render_model_builder.py``

```python
@pytest.mark.asyncio
async def test_build_container_shape(self, builder, mock_docdef_service, mock_component_service):
    """Test building RenderModel with container shape."""
    # Setup docdef with container shape
    # Verify single block with items array
    pass  # Full implementation
```

#### Step 6.3: Integration Test

**Action:** Add to ``tests/integration/test_adr034_proof.py``

```python
@pytest.mark.asyncio
async def test_epic_backlog_v1_1_container_rendering():
    """EpicBacklog v1.1.0 produces container block."""
    pass  # Full implementation
```

**Verification:** All new tests pass, existing tests unaffected.

---

### PHASE 7: Seed and Verify

#### Step 7.1: Seed New Artifacts

**Action:** Run seed scripts

```bash
python -m app.domain.registry.seed_schema_artifacts
python -m app.domain.registry.seed_fragment_artifacts
python -m app.domain.registry.seed_component_artifacts
```

#### Step 7.2: Preview Verification

**Action:** Test render preview with v1.1.0

```
POST /api/admin/composer/preview/render/docdef:EpicBacklog:1.1.0
```

Verify response contains single container block with items array.

#### Step 7.3: Run Full Test Suite

**Action:** ``python -m pytest tests/ -v``

**Verification:** All tests pass.

---

### PHASE 8: Final Verification

#### Step 8.1: Acceptance Criteria Check

- [ ] ``schema:OpenQuestionsBlockV1`` exists and accepted
- [ ] ``component:OpenQuestionsBlockV1:1.0.0`` exists with fragment binding
- [ ] Render preview shows single container block with items
- [ ] No HTML in JSON payloads
- [ ] Existing v1.0.0 docdef unchanged and functional
- [ ] All tests pass

#### Step 8.2: Decision Gate Evaluation

Document answers to:
- Did container blocks reduce template-level orchestration logic?
- Did they clarify section-level semantics?
- Did they avoid hidden coupling in RenderModelBuilder?

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-08 | Initial draft |

---

*End of Work Statement*


