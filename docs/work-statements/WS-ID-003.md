# WS-ID-003: Wire Minting into Document Creation Paths

## Status: Accepted

## Parent: WP-ID-001
## Governing ADR: ADR-055
## Depends On: WS-ID-002
## Parallelizable With: WS-ID-004

## Objective

Update all document creation paths to call `mint_display_id()` and set the new `display_id` column. After this WS, every new document gets a `{TYPE}-{NNN}` identity at creation time.

## Scope

### In Scope

- Update `plan_executor.py` parent document creation to mint and set `display_id`
- Update `plan_executor.py` child document spawning to mint and set `display_id`
- Update `project_creation_service.py` (concierge_intake document creation)
- Update `intents.py` (intent_packet document creation)
- Update `document_service.py` generic `create()` to accept/require `display_id`
- Tier-1 tests

### Out of Scope

- Work Binder routes (WPC import, WP promote, WS create/propose) — covered by WS-ID-004
- Changes to `derive_wp_id` or `generate_ws_id` — covered by WS-ID-004
- The `display_id_service.py` module itself — created in WS-ID-002
- `instance_id` column — not modified

## Implementation

### Step 1: Update plan_executor parent document creation

**File:** `app/domain/workflow/plan_executor.py`

In `_execute_node_steps()` (around line 1776), before creating the Document, mint a display_id:

```python
from app.domain.services.display_id_service import mint_display_id

did = await mint_display_id(self._db_session, UUID(state.project_id), state.document_type)

document = Document(
    space_type="project",
    space_id=UUID(state.project_id),
    doc_type_id=state.document_type,
    title=doc_title,
    content=doc_content,
    version=1,
    is_latest=True,
    status="draft",
    created_by=None,
    display_id=did,  # <-- ADD
)
```

### Step 2: Update plan_executor child document spawning

**File:** `app/domain/workflow/plan_executor.py`

In `_spawn_or_update_child()` (around line 1897), mint a display_id for the child:

```python
did = await mint_display_id(self._db_session, UUID(state.project_id), spec["doc_type_id"])

child_doc = Document(
    ...
    display_id=did,  # <-- ADD (instance_id left as-is for existing logic)
)
```

### Step 3: Update project_creation_service

**File:** `app/api/services/project_creation_service.py`

In `create_project()` (around line 158), mint display_id for concierge_intake:

```python
did = await mint_display_id(db, project.id, "concierge_intake")

intake_doc = Document(
    ...
    display_id=did,  # <-- ADD
)
```

Note: concierge_intake `display_prefix` (`CI`) is registered in WS-ID-001 migration.

### Step 4: Update intent_packet creation

**File:** `app/api/v1/routers/intents.py`

In `create_intent_packet()` (around line 72):

```python
did = await mint_display_id(db, UUID(request.project_id), "intent_packet")

doc = Document(
    ...
    display_id=did,  # <-- ADD
)
```

Note: intent_packet `display_prefix` (`INT`) is registered in WS-ID-001 migration.

### Step 5: Update document_service.create()

**File:** `app/api/services/document_service.py`

The generic `create()` function should accept a required `display_id` parameter and set it on the Document.

## Tier-1 Tests

- Document creation in plan_executor sets `display_id`
- Document creation in project_creation_service sets `display_id`
- Intent creation sets `display_id`
- All display_ids follow `{TYPE}-{NNN}` format
- Sequential minting produces incrementing numbers

## Allowed Paths

```
app/domain/workflow/plan_executor.py
app/api/services/project_creation_service.py
app/api/services/document_service.py
app/api/v1/routers/intents.py
tests/tier1/
```

## Prohibited

- Do not modify work_binder.py (WS-ID-004)
- Do not modify wp_promotion_service.py (WS-ID-004)
- Do not modify ws_crud_service.py (WS-ID-004)
- Do not modify `instance_id` on any document

## Verification

- All new document creations set `display_id` to a minted value
- No document creation path leaves `display_id` unset
- All existing tests pass
