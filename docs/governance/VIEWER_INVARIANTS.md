# Viewer Invariants v1.0

> **Frozen**: The "Technical Constitution" of the document viewer.

## Philosophy

> **"The Viewer is a stateless renderer. It turns RenderModels into HTML. Nothing else."**

The viewer enforces the "Hourglass Waist" pattern: all complexity is compressed through a single data structure (RenderModelV1) that the viewer blindly renders.

## The Hourglass Waist

```
┌─────────────────────────────────────┐
│  Documents, DocDefs, Schemas, LLM   │  ← Complexity above
└─────────────────────────────────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  RenderModelV1  │  ← The waist (narrow contract)
        └─────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  Fragments, Templates, CSS, HTML    │  ← Complexity below
└─────────────────────────────────────┘
```

## Input Contract

The viewer ONLY accepts `RenderModelV1`:

```python
@dataclass
class RenderModelV1:
    render_model_version: str = "1.0"
    schema_id: str = "schema:RenderModelV1"
    document_ref: DocumentRef
    title: str
    tabs: list[TabDef]
    sections: list[SectionDef]
    blocks: list[BlockDef]
    metadata: dict
```

## What the Viewer NEVER Does

| Forbidden Action | Why |
|------------------|-----|
| Call the LLM | Viewer is read-only |
| Read raw documents | Only RenderModel |
| Parse docdefs | Already resolved by RenderModelBuilder |
| Perform business logic | Logic belongs in services |
| Access database | Stateless, receives all data |
| Modify document state | Read-only rendering |
| Cache rendered output | Caching is infrastructure concern |

## What the Viewer ALWAYS Does

| Required Behavior | Why |
|-------------------|-----|
| Render all provided blocks | No filtering by viewer |
| Use fragment registry for rendering | Consistent component lookup |
| Gracefully handle unknown block types | Never crash on bad data |
| Log warnings for missing fragments | Observability |
| Apply display variants via CSS | Data-driven styling |

## Document State Rendering

| State | Rendering |
|-------|-----------|
| `missing` | "Build" CTA only |
| `generating` | Skeleton UI with progress |
| `partial` | Available sections + "Continue" CTA |
| `complete` | Full document |
| `stale` | Full document + amber indicator |

## Fragment Contract

Each block is rendered by a fragment that receives:

```jinja2
{{ block.type }}     {# schema_id #}
{{ block.key }}      {# unique key #}
{{ block.data }}     {# actual content #}
{{ block.context }}  {# parent context, may be None #}
```

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Unknown block type | Render placeholder with type info |
| Missing fragment | Graceful degradation + warning log |
| Null data | Skip block silently |
| Template error | Error placeholder, never crash |
| Invalid RenderModel | 500 error with correlation_id |

## Rendering Invariants

1. **Unknown block types → placeholder** - Never crash on unknown data
2. **Missing fragments → graceful degradation** - Log warning, show fallback
3. **Null data → skip silently** - Empty blocks don't render
4. **Template errors → error placeholder** - Never crash the page
5. **RenderModel is immutable** - Viewer never modifies input

## Performance Constraints

| Constraint | Limit |
|------------|-------|
| Max blocks per render | 1000 |
| Max nesting depth | 10 |
| Fragment render timeout | 100ms per block |
| Total render timeout | 5s |

## Testing Strategy

1. **Golden Trace Tests**: Snapshot RenderModel → HTML output
2. **Fragment Unit Tests**: Each fragment renders in isolation
3. **Error Handling Tests**: All error paths covered
4. **Performance Tests**: Large document rendering stays under limits

## Governance Boundary

| Change | Requires WS/ADR? |
|--------|------------------|
| Add new fragment | No |
| Change fragment styling | No |
| Add display variant | No |
| Change RenderModel schema | Yes |
| Add viewer-side logic | Yes |
| Change error handling | Yes |

---

_Frozen: 2026-01-12 (ADR-033, WS-DOCUMENT-SYSTEM-CLEANUP)_