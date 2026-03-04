# ADR-055 -- Document Identity Standard

**Status:** Accepted
**Date:** 2026-03-04
**Related:** ADR-052, WS-INSTANCE-ID-001

---

## Context

The Combine has three incompatible document identity formats:

| Doc Type | Current Format | Convention | Example |
|----------|---------------|------------|---------|
| Work Package Candidate | `WPC-NNN` | Uppercase, dashes | `WPC-001` |
| Work Package | `wp_wb_NNN` | Lowercase, underscores | `wp_wb_001` |
| Work Statement | `WS-PREFIX-NNN` | Uppercase, dashes, parent-derived | `WS-WB-001` |
| Project Discovery | _(none)_ | UUID only | `550e8400-...` |
| Technical Architecture | _(none)_ | UUID only | `550e8400-...` |
| Implementation Plan | _(none)_ | UUID only | `550e8400-...` |

Problems:

1. **Format breaks on promotion.** `WPC-001` becomes `wp_wb_001` via `derive_wp_id()`. An operator who remembers the candidate ID cannot find the promoted work package by name.

2. **Tier-1 documents have no human identity.** Project Discovery, Technical Architecture, and Implementation Plan are identifiable only by UUID. There is no pasteable, speakable reference.

3. **Inconsistent casing.** WPC and WS use `UPPER-DASH`. WP uses `lower_snake`. These coexist in the same `documents` table and `instance_id` column.

4. **Deep linking is blocked.** Without a stable, predictable identity format, URLs cannot encode document references. The SPA has no deep links today.

5. **Cross-project ambiguity.** `WPC-001` exists in every project that has an Implementation Plan. The ID is only unique within a project scope, but this scoping is implicit.

Since no production data exists (greenfield), we can fix this cleanly.

This ADR is a deliberate schema change. It adds a new `display_id` column and supporting infrastructure. `instance_id` is left untouched — it has a different semantic on `workflow_instances` (UUID FK for workflow execution identity), and reusing the name for document identity would plant a semantic landmine. One noun, one meaning.

---

## Decision

### 1. Universal Display ID Format

Every document in The Combine SHALL have a `display_id` following this format:

```
{TYPE}-{NNN}
```

Where:
- `{TYPE}` is an uppercase abbreviation (2-4 chars) registered in the document type configuration
- `{NNN}` is a zero-padded sequential number, unique per `(space_id, doc_type_id)`
- Separator is always a hyphen (`-`)

### 2. Registered Type Prefixes (Examples)

| doc_type_id | Prefix | Example |
|-------------|--------|---------|
| `project_discovery` | `PD` | `PD-001` |
| `technical_architecture` | `TA` | `TA-001` |
| `implementation_plan` | `IP` | `IP-001` |
| `work_package_candidate` | `WPC` | `WPC-001` |
| `work_package` | `WP` | `WP-001` |
| `work_statement` | `WS` | `WS-001` |

The authoritative prefix registry is `document_types.display_prefix`, seeded from `package.yaml` configuration. All registered doc types MUST have a non-null `display_prefix`. The complete mapping is a delivery artifact of the implementing Work Statement, not normative ADR content.

New document types MUST register a prefix before their first use.

### 3. Single-Instance Documents Get display_id Too

Single-instance types (PD, TA, IP) always have `display_id = "{PREFIX}-001"` since there is exactly one per project. If a future ADR changes cardinality, the numbering naturally extends.

**Note:** "Single-instance" is current business policy, not an identity system constraint. The identity system is cardinality-agnostic — PD-002 is a valid display_id if a future ADR permits multiple Project Discovery documents per project.

### 4. display_id Is a New Column (Not instance_id)

A new `display_id` column is added to the `documents` table:

```sql
ALTER TABLE documents ADD COLUMN display_id VARCHAR(20) NOT NULL;
```

- `display_id` stores the human-readable identity for ALL document types
- Single-instance docs: `display_id = "PD-001"`, `"TA-001"`, etc.
- Multi-instance docs: `display_id = "WPC-001"`, `"WP-001"`, etc.

The existing `instance_id` column is **left untouched**. It remains nullable, stores whatever it stores today, and will be deprecated in a future cleanup. The term "instance" is reserved for workflow execution identity (`WorkflowInstance.instance_id`), not document identity.

A new unique index enforces one latest document per display_id within a space:

```sql
CREATE UNIQUE INDEX idx_documents_latest_display
ON documents (space_type, space_id, doc_type_id, display_id)
WHERE is_latest = TRUE;
```

### 5. display_id Is Minted at Creation, Immutable After

- Assigned when a document is first created (version 1)
- Never changes, even if the document is versioned, renamed, or reparented
- Sequence is per `(space_id, doc_type_id)`: the next available number
- Minting requires serialized access. Current implementation uses `SELECT MAX` under a transaction. If concurrent document creation becomes a requirement, replace with a sequence table.

### 6. display_id Prefix Stored in document_types

Add a `display_prefix` column to `document_types`:

```sql
ALTER TABLE document_types ADD COLUMN display_prefix VARCHAR(4) NOT NULL;
```

Populated from `package.yaml` configuration. The `instance_key` column (from WS-INSTANCE-ID-001) is dropped — `display_id` is the universal identity key.

### 7. derive_wp_id() Is Eliminated

Work Package promotion no longer transforms the ID format. Instead:

- WPC-001 is promoted → a new WP document is created with `display_id = "WP-001"` (next available WP sequence in that project)
- The WP's `source_candidate_ids` field links back to `["WPC-001"]`
- No format transformation. No `wp_wb_001`.

### 8. WS Numbering Is Per-WP, Stored in display_id

Work Statements are numbered sequentially per work package:

- First WS under WP-001: `display_id = "WS-001"`
- Second: `WS-002`

The parent relationship is captured by `parent_document_id`, not by encoding the parent's ID in the child's display_id. `WS-WB-001` format is eliminated.

### 9. Project Slug (Project-Level Identity)

The existing `project_id` column on the `projects` table already follows the `{TYPE}-{NNN}` convention (e.g., `HWCA-001`, `APAM-002`). It is unique, immutable after creation, and human-readable. **No new column is needed.**

`project_id` serves as the project-level equivalent of `display_id` and is used in URLs instead of UUIDs (see ADR-056).

### 10. Fully Qualified Reference (For Cross-Project Use)

When referencing a document across projects, use:

```
{PROJECT_SLUG}/{DISPLAY_ID}
```

Example: `HWCA-001/WP-001`, `APAM-002/WPC-003`

This format is for human communication and URLs — not stored in the database.

### 11. Prefix Resolution Contract

The `display_prefix` column in `document_types` is the authoritative registry for resolving a `display_id` to its document type. Given a `display_id`:

1. Split on the last hyphen: `"WPC-001"` → prefix `"WPC"`, number `"001"`
2. Look up prefix in `document_types.display_prefix` → resolves to `doc_type_id = "work_package_candidate"`
3. Query `documents` by `(space_id, doc_type_id, display_id)` to find the document

This resolution is the binding contract between ADR-055 (identity) and ADR-056 (routing). Backend endpoints that accept a `display_id` in a URL path MUST use this resolution path — never hardcoded prefix-to-type mappings.

---

## Consequences

### Positive

- **One format everywhere.** `TYPE-NNN` is the only ID format. No translation needed.
- **Every document is addressable.** Tier-1 docs get `PD-001`, `TA-001`, `IP-001`.
- **Deep linking unblocked.** URLs can use `/{project_slug}/{display_id}` to address any document.
- **Promotion is clean.** WPC-001 stays WPC-001. WP-001 is a new document with lineage, not a renamed candidate.
- **Speakable.** "Open WP-003" is unambiguous within a project context.

### Negative

- **Sequence generation requires a query.** Minting a new display_id needs `SELECT MAX(...)` or equivalent. This is a single query at creation time — acceptable.
- **Single-instance docs always show "-001".** `PD-001` looks odd when there can only be one. Acceptable for consistency.

### Schema Changes

This ADR intentionally changes schema:

1. Adds `display_id` column to `documents` (NOT NULL VARCHAR(20))
2. Adds `display_prefix` column to `document_types` (NOT NULL VARCHAR(4))
3. Adds unique index `idx_documents_latest_display` on `(space_type, space_id, doc_type_id, display_id) WHERE is_latest = TRUE`
4. Drops `instance_key` column from `document_types`

`instance_id` is **not modified**. No changes to the `projects` table — `project_id` already serves as the slug.

### Data Migration

**Dev/test databases are reset.** Existing documents (PD, TA, IP, WPCs from Hello World and APAM pipelines) predate this identity standard and will not be backfilled. Run `db_reset.sh dev` and `db_reset.sh test` after the schema migration, then regenerate pipeline data under the new identity scheme. This validates the new pipeline end-to-end.

---

## Implementation Notes

### display_id Minting Function

```python
async def mint_display_id(db: AsyncSession, space_id: UUID, doc_type_id: str) -> str:
    """Mint the next sequential display_id for a document type in a space."""
    doc_type = await get_document_type(db, doc_type_id)
    prefix = doc_type.display_prefix

    result = await db.execute(
        select(func.max(Document.display_id))
        .where(
            Document.space_id == space_id,
            Document.doc_type_id == doc_type_id,
        )
    )
    max_id = result.scalar()

    if max_id:
        current_num = int(max_id.split("-")[-1])
        next_num = current_num + 1
    else:
        next_num = 1

    return f"{prefix}-{next_num:03d}"
```

### URL Pattern (Feeds ADR-056)

```
/projects/{project_slug}/docs/{display_id}
```

Example: `/projects/HWCA-001/docs/WP-001`

---

## Governance Boundary

| Change | Requires WS/ADR? |
|--------|------------------|
| Register new doc type prefix | No (add to document_types) |
| Change existing prefix | Yes (breaks references) |
| Change display_id format | Yes |
| Change sequence scoping | Yes |
| Change project slug format | Yes |

---

_Draft: 2026-03-04_
