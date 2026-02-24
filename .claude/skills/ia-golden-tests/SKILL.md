---
name: ia-golden-tests
description: Run and debug IA golden contract tests. Use when writing IA tests, diagnosing test failures, or generating IA coverage reports for document types.
---

# IA Golden Contract Tests

## Test File

`tests/tier1/test_information_architecture.py`

## Test Criteria

### Golden Contract Tests (C1-C5, parametrized across Tier-1 doc types)

- **C1**: Every binds path in IA sections resolves to a valid schema field
- **C2**: Every schema-required field appears in at least one IA section
- **C3**: Every section in rendering.detail_html tabs exists in IA sections
- **C4**: No IA section is unreferenced by any rendering target
- **C5**: Every entry in rendering.pdf.linear_order references a declared section ID

### Block Rendering Contract (C6-C9)

- **C6**: All `render_as` values must be in pinned vocabulary
- **C7**: Every `card-list` bind has `card` with `title` and `fields`
- **C8**: Every `table` bind has `columns` array with `field` + `label`
- **C9**: Every `nested-object` bind has `fields` with `path` + `render_as`

### No-Guessing Enforcement (C10-C13)

- **C10**: If schema type at path is object/array, `render_as` MUST be present
- **C11**: `render_as: paragraph` on object/array is a failure
- **C12**: Every sub-field in `card.fields` has its own `render_as`
- **C13**: 100% Level 2 coverage — every bind is an object with `render_as`

## Tier-1 Document Types

All require Level 2 IA:
- `technical_architecture`
- `project_discovery`
- `primary_implementation_plan`
- `implementation_plan`

## Coverage Report

The test suite generates per-document-type coverage:
- Document type name and version
- Total binds count
- Binds at Level 2 count
- Coverage percentage
- List of violations (if any)

## Debugging Guide

### "Bind path not in schema"
The IA bind references a field that doesn't exist in the output schema.
- Check `combine-config/document_types/<type>/releases/<ver>/schemas/output.schema.json`
- Ensure the path matches a top-level property name

### "Required field not covered"
A schema-required field has no IA bind.
- Add a bind for the field in the appropriate section of `package.yaml`
- System fields (`meta`) are excluded automatically

### "Invalid render_as"
A bind uses a `render_as` value not in the pinned vocabulary.
- Valid values: `paragraph`, `list`, `ordered-list`, `table`, `key-value-pairs`, `card-list`, `nested-object`

### "Complex type without render_as"
A bind references an object/array schema type but has no `render_as`.
- Add explicit `render_as` to the bind (must not be `paragraph` for complex types)

### "card-list missing card definition"
A `card-list` bind lacks the `card` sub-structure.
- Add `card: { title: <field>, fields: [...] }` with each field having `path` and `render_as`

### Running Tests

```bash
# Run all IA tests
python3 -m pytest tests/tier1/test_information_architecture.py -v

# Run only block rendering tests
python3 -m pytest tests/tier1/test_information_architecture.py -k "BlockRendering" -v

# Run coverage report tests
python3 -m pytest tests/tier1/test_information_architecture.py -k "CoverageReport" -v
```
