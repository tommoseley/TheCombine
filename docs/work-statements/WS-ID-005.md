# WS-ID-005: DB Reset + Pipeline Validation

## Status: Accepted

## Parent: WP-ID-001
## Governing ADR: ADR-055
## Depends On: WS-ID-003, WS-ID-004

## Objective

Reset dev/test databases to clear pre-identity-standard data, run migrations, and validate that the full pipeline produces documents with conformant `display_id` values.

## Scope

### In Scope

- Reset dev database (`CONFIRM_ENV=dev ops/scripts/db_reset.sh dev`)
- Reset test database (`CONFIRM_ENV=test ops/scripts/db_reset.sh test`)
- Run `alembic upgrade head` on both
- Seed document types with correct `display_prefix` values
- Create a test project and verify pipeline produces conformant display_ids
- Run full Tier-0 verification

### Out of Scope

- Code changes (all code changes completed in WS-ID-001 through WS-ID-004)
- SPA changes (none needed for identity — routing is WP-ROUTE-001)

## Implementation

### Step 1: Reset databases

```bash
CONFIRM_ENV=dev ops/scripts/db_reset.sh dev
CONFIRM_ENV=test ops/scripts/db_reset.sh test
```

### Step 2: Run migrations

```bash
ops/scripts/db_migrate.sh dev --seed
ops/scripts/db_migrate.sh test --seed
```

### Step 3: Verify schema

Connect to dev DB and confirm:
```sql
-- display_prefix populated
SELECT doc_type_id, display_prefix, cardinality FROM document_types ORDER BY doc_type_id;

-- display_id is NOT NULL
SELECT column_name, is_nullable FROM information_schema.columns
WHERE table_name = 'documents' AND column_name = 'display_id';

-- Unified index exists
SELECT indexname FROM pg_indexes WHERE tablename = 'documents' AND indexname = 'idx_documents_latest_display';

-- Old indexes gone
SELECT indexname FROM pg_indexes WHERE tablename = 'documents' AND indexname LIKE 'idx_documents_latest_%';
```

### Step 4: Pipeline validation

Create a project via the API or UI. Run the pipeline to generate at least:
- Project Discovery → verify `display_id = "PD-001"`
- Technical Architecture → verify `display_id = "TA-001"`
- Implementation Plan → verify `display_id = "IP-001"`

If WPC import is tested:
- Import candidates → verify `display_id = "WPC-001"`, `"WPC-002"`, etc.

### Step 5: Run Tier-0

```bash
ops/scripts/tier0.sh --frontend
```

## Tier-1 Tests

No new tests — this WS validates the integration of WS-ID-001 through WS-ID-004.

## Allowed Paths

```
ops/scripts/
tests/
```

## Prohibited

- Do not modify application code (all changes completed in prior WSs)
- Do not modify migration files (WS-ID-001)
- Do not skip database reset (existing data predates identity standard)

## Verification

- Dev and test databases reset and migrated successfully
- `display_prefix` column populated for all doc types
- `display_id` is NOT NULL
- Unified unique index exists, old indexes removed
- Pipeline produces conformant display_ids
- Tier-0 passes (pytest + lint + typecheck + SPA build)

## Definition of Done

All verification items pass. WP-ID-001 is complete.
