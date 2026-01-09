# Procedure: Add Component

**Status:** Frozen  
**Effective:** 2026-01-09  
**WS:** WS-ADR-034-COMPONENT-PROMPT-UX-COMPLETENESS

## Purpose

Step-by-step procedure for adding a new canonical component to The Combine.

## Prerequisites

- Component represents a reusable rendering unit
- No existing component serves the same purpose (check `INITIAL_COMPONENT_ARTIFACTS`)
- Component has clear schema boundaries

---

## Step 1: Create Schema

**File:** `app/domain/registry/seed_schema_artifacts.py`

```python
XXX_BLOCK_V1_SCHEMA = {
    "$id": "schema:XxxBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Xxx Block",
    "type": "object",
    "required": ["field1", "field2"],
    "properties": {
        "field1": {"type": "string", "description": "..."},
        "field2": {"type": "string", "description": "..."},
    },
    "additionalProperties": False,  # REQUIRED
    "description": "..."
}
```

**Checklist:**
- [ ] `$id` follows format `schema:XxxV1`
- [ ] `additionalProperties: false` (prevents drift)
- [ ] All required fields listed
- [ ] Descriptions provided
- [ ] Added to `INITIAL_SCHEMA_ARTIFACTS` list

---

## Step 2: Create Component

**File:** `app/domain/registry/seed_component_artifacts.py`

```python
XXX_BLOCK_V1_COMPONENT = {
    "component_id": "component:XxxBlockV1:1.0.0",
    "schema_id": "schema:XxxBlockV1",
    "generation_guidance": {
        "bullets": [
            "Declarative instruction 1.",
            "Declarative instruction 2.",
            "Keep instructions role-agnostic.",
        ]
    },
    "view_bindings": {
        "web": {
            "fragment_id": "fragment:XxxBlockV1:web:1.0.0"
        }
    },
    "status": "accepted"
}
```

**Checklist:**
- [ ] `component_id` follows format `component:XxxV1:1.0.0`
- [ ] `generation_guidance.bullets` is non-empty
- [ ] Bullets are declarative, imperative, role-agnostic
- [ ] `view_bindings.web.fragment_id` uses canonical format
- [ ] Added to `INITIAL_COMPONENT_ARTIFACTS` list

---

## Step 3: Create Fragment

**File:** `app/domain/registry/seed_fragment_artifacts.py`

```python
XXX_BLOCK_V1_FRAGMENT = """
<div class="xxx-block" data-block-type="XxxBlockV1">
  <p>{{ block.data.field1 }}</p>
  {% if block.data.field2 %}
  <span>{{ block.data.field2 }}</span>
  {% endif %}
</div>
"""
```

Add to list:
```python
{
    "fragment_id": "fragment:XxxBlockV1:web:1.0.0",
    "version": "1.0",
    "schema_type_id": "XxxBlockV1",
    "status": "accepted",
    "fragment_markup": XXX_BLOCK_V1_FRAGMENT,
},
```

**Checklist:**
- [ ] `fragment_id` uses canonical format
- [ ] Uses `block.data.*` for data access
- [ ] Uses `block.context.*` for context
- [ ] No computed values or hardcoded content
- [ ] Tailwind CSS styling
- [ ] Added to `INITIAL_FRAGMENT_ARTIFACTS` list

---

## Step 4: Seed Database

```bash
python -m app.domain.registry.seed_schema_artifacts
python -m app.domain.registry.seed_component_artifacts
python -m app.domain.registry.seed_fragment_artifacts
```

---

## Step 5: Add Tests

**Required tests:**

1. **Schema validation** (`tests/domain/test_seed_schema_artifacts.py`)
   - Update schema count assertion

2. **Fragment compiles** (automatic via `test_component_completeness.py`)
   - Runs automatically on all fragments

3. **Golden trace** (optional but recommended)
   - Add fixture using component in minimal docdef
   - Verify block output structure

---

## Step 6: Versioning Rules

| Change Type | Action |
|-------------|--------|
| New optional field | Bump patch (1.0.0 → 1.0.1) |
| New required field | Bump minor (1.0.0 → 1.1.0) |
| Breaking schema change | New version (1.0.0 → 2.0.0) |
| Never | Mutate accepted artifacts |

---

## Verification Checklist

- [ ] Schema in `INITIAL_SCHEMA_ARTIFACTS`
- [ ] Component in `INITIAL_COMPONENT_ARTIFACTS`
- [ ] Fragment in `INITIAL_FRAGMENT_ARTIFACTS`
- [ ] All tests pass: `python -m pytest tests/domain/test_component_completeness.py -v`
- [ ] DB seeded successfully
- [ ] Fragment resolves via `resolve_fragment_id()`
