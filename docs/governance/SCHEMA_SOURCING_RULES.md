# Schema Sourcing Rules v1.0

> **Frozen**: Governs how the system resolves document structures.

## Philosophy

> **"The document knows its own schema."**

Schema drift breaks old projects. The `schema_bundle_sha256` persisted in the document record is the only schema used for rendering that specific instance.

## The Schema Drift Problem

Without pinned schemas:
1. Component schema updated (v1 → v2)
2. Old document still contains v1 data
3. Viewer loads "latest" schema (v2)
4. Rendering fails or produces incorrect output

## Solution: Hash-Based Schema Resolution

### At Generation Time

```python
# 1. Collect all component schemas used in docdef
schemas = [schema_registry.get(component_id) for component_id in docdef.components]

# 2. Compute deterministic hash
bundle = json.dumps(sorted(schemas, key=lambda s: s["$id"]), sort_keys=True)
schema_bundle_sha256 = "sha256:" + hashlib.sha256(bundle.encode()).hexdigest()

# 3. Persist with document
document.schema_bundle_sha256 = schema_bundle_sha256
```

### At Render Time

```python
# 1. Check document for persisted hash
if document.schema_bundle_sha256:
    # Use exact schemas from generation time
    schemas = schema_registry.get_by_hash(document.schema_bundle_sha256)
else:
    # Legacy document: fall back to latest (with warning)
    logger.warning(f"Document {document.id} has no schema hash, using latest")
    schemas = schema_registry.get_latest(docdef.components)
```

## Schema Bundle Hash Algorithm

```python
def compute_schema_bundle_sha256(schema_ids: list[str]) -> str:
    """Compute deterministic hash for a set of schemas."""
    schemas = sorted([get_schema(id) for id in schema_ids], key=lambda s: s["$id"])
    bundle = json.dumps(schemas, sort_keys=True, separators=(',', ':'))
    return "sha256:" + hashlib.sha256(bundle.encode()).hexdigest()
```

## Database Schema

```sql
-- documents table
schema_bundle_sha256 VARCHAR(100)  -- "sha256:abc123..."

-- Index for hash lookups
CREATE INDEX idx_documents_schema_bundle ON documents(schema_bundle_sha256);
```

## Invariants

1. **Same schema_ids → same bundle SHA256** - Deterministic hashing
2. **Schema changes require new semver** - Never modify in place
3. **No inline schemas anywhere** - All schemas in registry
4. **All schemas have `$id` matching schema_id** - Canonical identifier
5. **Documents without hash use latest** - Graceful degradation for legacy

## Schema Lifecycle

| Action | Schema Impact |
|--------|---------------|
| New document created | Current schemas hashed and persisted |
| Document regenerated | New schemas hashed, old hash overwritten |
| Schema updated | New version in registry, old documents unchanged |
| Document viewed | Uses persisted hash, not latest |

## Migration Path for Legacy Documents

Documents created before Phase 2 have `NULL` schema_bundle_sha256:

1. **At render time**: Fall back to latest schemas
2. **On regeneration**: Compute and persist hash
3. **No bulk migration**: Hash populated on next generation

## Governance Boundary

| Change | Requires WS/ADR? |
|--------|------------------|
| Add new schema | No |
| Update schema (new version) | No |
| Change hash algorithm | Yes |
| Change fallback behavior | Yes |
| Add schema validation | Yes |

## Anti-Patterns (Avoid)

1. **Modifying schemas in place** - Always create new version
2. **Hardcoded schema references** - Use registry lookups
3. **Assuming "latest" schema** - Always check document hash first
4. **Inline schemas in documents** - Reference registry only

---

_Frozen: 2026-01-12 (WS-DOCUMENT-SYSTEM-CLEANUP Phase 2)_