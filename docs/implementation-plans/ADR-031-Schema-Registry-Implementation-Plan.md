# ADR-031 Implementation Plan: Canonical Schema Types and Schema Registry

**Created:** 2026-01-06  
**ADR Version:** Draft  
**Status:** Ready for Review

---

## Summary

Implement a DB-backed schema registry with canonical types and a resolver that produces self-contained schema bundles for LLM generation and validation.

**Goal:** LLM callers receive resolved schema bundles only. No filesystem access, no unresolved `$ref`.

---

## Reuse Analysis

Per the Reuse-First Rule:

| Option | Artifact | Decision | Rationale |
|--------|----------|----------|-----------|
| Extend | `app/api/models/` | **Extend** | Add `SchemaArtifact` model |
| Extend | `app/api/services/` | **Extend** | Add `SchemaRegistryService` |
| Create | `app/domain/services/schema_resolver.py` | **Create** | New capability, nothing to reuse |
| Extend | `app/domain/services/llm_execution_logger.py` | **Extend** | Add schema tracking per ADR-010 |
| Extend | `DocumentBuilder` | **Extend** | Integrate resolved bundles |

---

## Phase 1: Database Migration

**New File:** `alembic/versions/20260106_001_add_schema_artifact.py`

**Table: `schema_artifact`**

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `schema_id` | VARCHAR(100) | NOT NULL, UNIQUE with version |
| `version` | VARCHAR(20) | NOT NULL, default '1.0' |
| `kind` | VARCHAR(20) | NOT NULL (type / document / envelope) |
| `status` | VARCHAR(20) | NOT NULL (draft / accepted / deprecated) |
| `schema_json` | JSONB | NOT NULL |
| `sha256` | VARCHAR(64) | NOT NULL |
| `governance_refs` | JSONB | ADRs, policies |
| `created_at` | TIMESTAMP | NOT NULL |
| `created_by` | VARCHAR(100) | |
| `updated_at` | TIMESTAMP | |

**Indexes:**
- `idx_schema_artifact_schema_id_version` UNIQUE on (schema_id, version)
- `idx_schema_artifact_status` on (status)
- `idx_schema_artifact_kind` on (kind)

**Estimated Time:** 30 min

---

## Phase 2: ORM Model

**New File:** `app/api/models/schema_artifact.py`

```python
class SchemaArtifact(Base):
    __tablename__ = "schema_artifacts"
    
    id: Mapped[UUID]
    schema_id: Mapped[str]          # e.g., "OpenQuestionV1"
    version: Mapped[str]            # e.g., "1.0"
    kind: Mapped[str]               # "type" | "document" | "envelope"
    status: Mapped[str]             # "draft" | "accepted" | "deprecated"
    schema_json: Mapped[dict]       # The actual JSON Schema
    sha256: Mapped[str]             # Hash of schema_json
    governance_refs: Mapped[dict]   # {"adrs": ["ADR-031"], "policies": [...]}
    created_at: Mapped[datetime]
    created_by: Mapped[Optional[str]]
    updated_at: Mapped[Optional[datetime]]
```

**Update:** `app/api/models/__init__.py` to export

**Estimated Time:** 30 min

---

## Phase 3: Schema Registry Service

**New File:** `app/api/services/schema_registry_service.py`

**Responsibilities:**
- CRUD operations for schema artifacts
- Status lifecycle management
- Hash computation on save
- Lookup by schema_id (latest accepted) or schema_id + version

**Methods:**

```python
class SchemaRegistryService:
    async def create(self, schema_id: str, version: str, kind: str, 
                     schema_json: dict, governance_refs: dict = None) -> SchemaArtifact
    
    async def get_by_id(self, schema_id: str, version: str = None) -> SchemaArtifact | None
        # If version is None, returns latest accepted
    
    async def get_accepted(self, schema_id: str) -> SchemaArtifact | None
        # Returns latest accepted version
    
    async def set_status(self, schema_id: str, version: str, status: str) -> SchemaArtifact
    
    async def list_by_kind(self, kind: str, status: str = None) -> List[SchemaArtifact]
    
    def compute_hash(self, schema_json: dict) -> str
        # Deterministic JSON serialization + SHA256
```

**Estimated Time:** 1 hour

---

## Phase 4: Schema Resolver Service

**New File:** `app/domain/services/schema_resolver.py`

**Responsibilities:**
- Resolve `$ref: "schema:<id>"` references
- Detect and reject circular references
- Produce self-contained bundle with `$defs`
- Compute bundle hash
- Track dependencies

**Data Classes:**

```python
@dataclass
class ResolvedSchemaBundle:
    root_schema_id: str
    root_schema_version: str
    bundle_json: dict              # Self-contained schema with $defs
    bundle_sha256: str
    dependencies: List[SchemaDependency]

@dataclass
class SchemaDependency:
    schema_id: str
    version: str
    sha256: str
```

**Methods:**

```python
class SchemaResolver:
    def __init__(self, registry: SchemaRegistryService):
        self.registry = registry
    
    async def resolve_bundle(self, root_schema_id: str, 
                              version: str = None) -> ResolvedSchemaBundle:
        # 1. Load root schema
        # 2. Find all $ref: "schema:<id>" references
        # 3. Recursively resolve each (detect cycles)
        # 4. Inline into $defs
        # 5. Rewrite $ref to "#/$defs/<id>"
        # 6. Compute bundle hash
        # 7. Return bundle
    
    def _find_schema_refs(self, schema: dict) -> List[str]:
        # Walk schema, find all $ref: "schema:..." 
    
    def _detect_cycle(self, schema_id: str, visited: Set[str]) -> bool:
        # Cycle detection during resolution
    
    def _inline_to_defs(self, root: dict, resolved: Dict[str, dict]) -> dict:
        # Build $defs and rewrite $ref targets
```

**Estimated Time:** 2 hours

---

## Phase 5: Seed Canonical Types

**New File:** `app/domain/registry/seed_schema_artifacts.py`

**Initial Canonical Types:**

| schema_id | kind | Description |
|-----------|------|-------------|
| `OpenQuestionV1` | type | Questions with blocking, options, why_it_matters |
| `RiskV1` | type | Risk with description, impact, affected items |
| `ScopeListV1` | type | List of in-scope / out-of-scope items |
| `DependencyV1` | type | Dependency reference with reason |

**OpenQuestionV1 Schema:**

```json
{
  "$id": "schema:OpenQuestionV1",
  "type": "object",
  "required": ["id", "text", "blocking", "why_it_matters"],
  "properties": {
    "id": { "type": "string", "minLength": 1 },
    "text": { "type": "string", "minLength": 2 },
    "blocking": { "type": "boolean", "default": false },
    "why_it_matters": { "type": "string", "minLength": 2 },
    "priority": { 
      "type": "string", 
      "enum": ["must", "should", "could"], 
      "default": "should" 
    },
    "options": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "label"],
        "properties": {
          "id": { "type": "string", "minLength": 1 },
          "label": { "type": "string", "minLength": 1 },
          "description": { "type": "string" }
        },
        "additionalProperties": false
      },
      "default": []
    },
    "default_response": {
      "type": "object",
      "properties": {
        "option_id": { "type": "string" },
        "free_text": { "type": "string" }
      },
      "additionalProperties": false
    },
    "notes": { "type": "string" }
  },
  "additionalProperties": false
}
```

**Seed Function:**

```python
async def seed_schema_artifacts(db: AsyncSession) -> int:
    # Create canonical types with status="accepted"
```

**Estimated Time:** 1 hour

---

## Phase 6: Extend LLM Execution Logging

**Modify:** `app/domain/services/llm_execution_logger.py`

**Add to log record:**
- `root_schema_id`
- `bundle_sha256`

**Modify:** `app/api/models/llm_execution_log.py` (if needed)

**Add columns:**
- `schema_id` VARCHAR(100)
- `schema_bundle_hash` VARCHAR(64)

**Migration:** Add columns to `llm_execution_logs` table

**Estimated Time:** 45 min

---

## Phase 7: Integrate with DocumentBuilder

**Modify:** `app/domain/services/document_builder.py`

**Changes:**
1. Before LLM call, resolve schema bundle via `SchemaResolver`
2. Include `bundle_json` in LLM request context
3. Pass `root_schema_id` and `bundle_sha256` to logger

```python
# In build method:
bundle = await self.schema_resolver.resolve_bundle(doc_type.schema_id)
# Include bundle.bundle_json in LLM prompt/context
# Log bundle.root_schema_id and bundle.bundle_sha256
```

**Estimated Time:** 1 hour

---

## Phase 8: Tests

**New Files:**

| File | Tests |
|------|-------|
| `tests/api/test_schema_registry_service.py` | CRUD, status lifecycle, hash computation |
| `tests/domain/test_schema_resolver.py` | Resolution, cycle detection, bundle structure |
| `tests/domain/test_seed_schema_artifacts.py` | Seeding, canonical types valid |

**Test Categories:**

| Category | Count (est.) |
|----------|--------------|
| Registry CRUD | 6 |
| Status lifecycle | 4 |
| Hash determinism | 2 |
| Ref resolution | 5 |
| Cycle detection | 4 |
| Bundle structure | 3 |
| LLM logging integration | 2 |
| Seed validation | 3 |

**Estimated Tests:** ~30

**Estimated Time:** 2 hours

---

## Implementation Order

| Step | Phase | Est. Time | Depends On |
|------|-------|-----------|------------|
| 1 | Database Migration | 30 min | — |
| 2 | ORM Model | 30 min | Step 1 |
| 3 | Schema Registry Service | 1 hour | Step 2 |
| 4 | Schema Resolver Service | 2 hours | Step 3 |
| 5 | Seed Canonical Types | 1 hour | Steps 3-4 |
| 6 | Extend LLM Logging | 45 min | Step 2 |
| 7 | Integrate DocumentBuilder | 1 hour | Steps 4-6 |
| 8 | Tests | 2 hours | All |

**Total Estimated Time:** ~9 hours

---

## Files to Create/Modify

| Action | File |
|--------|------|
| Create | `alembic/versions/20260106_001_add_schema_artifact.py` |
| Create | `app/api/models/schema_artifact.py` |
| Modify | `app/api/models/__init__.py` |
| Create | `app/api/services/schema_registry_service.py` |
| Modify | `app/api/services/__init__.py` |
| Create | `app/domain/services/schema_resolver.py` |
| Create | `app/domain/registry/seed_schema_artifacts.py` |
| Modify | `app/domain/services/llm_execution_logger.py` |
| Modify | `app/api/models/llm_execution_log.py` |
| Create | `alembic/versions/20260106_002_add_schema_to_llm_log.py` |
| Modify | `app/domain/services/document_builder.py` |
| Create | `tests/api/test_schema_registry_service.py` |
| Create | `tests/domain/test_schema_resolver.py` |
| Create | `tests/domain/test_seed_schema_artifacts.py` |

---

## Verification Checklist

- [ ] `schema_artifact` table exists with all columns
- [ ] `SchemaArtifact` ORM model works
- [ ] Registry service CRUD operations work
- [ ] Status transitions enforced (draft → accepted → deprecated)
- [ ] SHA256 computed deterministically
- [ ] Resolver handles `$ref: "schema:<id>"` correctly
- [ ] Circular references rejected
- [ ] Bundle includes `$defs` with resolved schemas
- [ ] `OpenQuestionV1` seeded and accepted
- [ ] LLM logs include `schema_id` and `bundle_sha256`
- [ ] DocumentBuilder uses resolved bundles
- [ ] All tests pass

---

## Definition of Done

- [ ] All phases complete
- [ ] All verification checks pass
- [ ] ADR-031 acceptance criteria met
- [ ] 30+ tests passing
- [ ] Work Statement closed

---

## Risks

| Risk | Mitigation |
|------|------------|
| Existing document generation breaks | Phase 7 is incremental; existing inline schemas still work |
| Resolver performance | Cache resolved bundles by root_schema_id + hash |
| Complex schema cycles | Cycle detection is explicit; fail fast |

---

_Last updated: 2026-01-06_