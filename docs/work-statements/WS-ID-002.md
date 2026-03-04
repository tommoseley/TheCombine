# WS-ID-002: Minting Service + Prefix Resolution

## Status: Accepted

## Parent: WP-ID-001
## Governing ADR: ADR-055
## Depends On: WS-ID-001

## Objective

Create the `mint_display_id()` function that generates sequential `{TYPE}-{NNN}` display IDs, and the `resolve_display_id()` function that resolves a display_id prefix to its `doc_type_id` via the `display_prefix` registry.

## Scope

### In Scope

- New service file: `app/domain/services/display_id_service.py`
- `mint_display_id(db, space_id, doc_type_id) -> str` — mints next sequential ID
- `resolve_display_id(db, display_id) -> tuple[str, str]` — returns `(doc_type_id, display_id)`
- `parse_display_id(display_id) -> tuple[str, str]` — pure function, splits prefix and number
- Tier-1 tests for all three functions

### Out of Scope

- Wiring into creation paths (WS-ID-003)
- Changes to existing services (WS-ID-004)
- Database queries for minting (minting function signature accepts db session but tier-1 tests use mocks)

## Implementation

### Step 1: Create display_id_service.py

**File:** `app/domain/services/display_id_service.py`

```python
import re
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.document import Document
from app.api.models.document_type import DocumentType

_DISPLAY_ID_PATTERN = re.compile(r'^([A-Z]{2,4})-(\d{3,})$')


def parse_display_id(display_id: str) -> tuple[str, str]:
    """Parse a display_id into (prefix, number_str).

    'WPC-001' -> ('WPC', '001')
    'PD-001' -> ('PD', '001')

    Raises ValueError if format is invalid.
    """
    match = _DISPLAY_ID_PATTERN.match(display_id)
    if not match:
        raise ValueError(f"Invalid display_id format: {display_id!r}. Expected {{TYPE}}-{{NNN}}.")
    return match.group(1), match.group(2)


async def resolve_display_id(db: AsyncSession, display_id: str) -> str:
    """Resolve a display_id prefix to its doc_type_id.

    'WPC-001' -> 'work_package_candidate'
    'PD-001' -> 'project_discovery'

    Raises ValueError if prefix not found in registry.
    """
    prefix, _ = parse_display_id(display_id)
    result = await db.execute(
        select(DocumentType.doc_type_id).where(
            DocumentType.display_prefix == prefix
        )
    )
    doc_type_id = result.scalar()
    if not doc_type_id:
        raise ValueError(f"Unknown display_id prefix: {prefix!r}. Not in document_types registry.")
    return doc_type_id


async def mint_display_id(db: AsyncSession, space_id: UUID, doc_type_id: str) -> str:
    """Mint the next sequential display_id for a document type in a space.

    Minting requires serialized access within a transaction.
    Uses SELECT MAX to find the current highest sequence number.
    """
    result = await db.execute(
        select(DocumentType.display_prefix).where(
            DocumentType.doc_type_id == doc_type_id
        )
    )
    prefix = result.scalar()
    if not prefix:
        raise ValueError(f"Document type {doc_type_id!r} has no display_prefix.")

    result = await db.execute(
        select(func.max(Document.display_id))
        .where(
            Document.space_id == space_id,
            Document.doc_type_id == doc_type_id,
        )
    )
    max_id = result.scalar()

    if max_id:
        _, num_str = parse_display_id(max_id)
        next_num = int(num_str) + 1
    else:
        next_num = 1

    return f"{prefix}-{next_num:03d}"
```

## Tier-1 Tests

**File:** `tests/tier1/services/test_display_id_service.py`

### parse_display_id tests:
- `parse_display_id("WPC-001")` → `("WPC", "001")`
- `parse_display_id("PD-001")` → `("PD", "001")`
- `parse_display_id("EP-042")` → `("EP", "042")`
- `parse_display_id("wp_wb_001")` → raises ValueError (wrong format)
- `parse_display_id("WS-WB-001")` → raises ValueError (too many segments — this is the OLD format)
- `parse_display_id("")` → raises ValueError
- `parse_display_id("X-1")` → raises ValueError (prefix too short, number too short)

### resolve_display_id tests (mock db):
- `resolve_display_id(db, "WPC-001")` with prefix "WPC" in registry → returns "work_package_candidate"
- `resolve_display_id(db, "ZZ-001")` with no match → raises ValueError

### mint_display_id tests (mock db):
- First mint in empty space → returns `"{PREFIX}-001"`
- Mint after existing `WPC-003` → returns `"WPC-004"`
- Mint with no display_prefix for doc_type → raises ValueError

## Allowed Paths

```
app/domain/services/display_id_service.py
tests/tier1/services/test_display_id_service.py
```

## Prohibited

- Do not modify any existing service files
- Do not modify any router files
- Do not modify any model files
- Do not wire minting into any creation path (WS-ID-003)

## Verification

- All tier-1 tests pass
- `parse_display_id` rejects old formats (`wp_wb_001`, `WS-WB-001`)
- `mint_display_id` produces sequential `{TYPE}-{NNN}` IDs
