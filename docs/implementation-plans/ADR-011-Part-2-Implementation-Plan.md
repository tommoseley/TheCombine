# ADR-011-Part-2 Implementation Plan

**Created:** 2026-01-05  
**ADR Version:** 0.93  
**Status:** Ready for implementation

---

## Summary of Changes

**ADR Update:** Replace fixed scope ranks with workflow-derived ordering  
**Implementation:** Two-layer validation (ownership validity + scope monotonicity)

---

## Reuse Analysis

Per the Reuse-First Rule, before creating new artifacts:

| Option | Artifact | Decision | Rationale |
|--------|----------|----------|-----------|
| Extend | `DocumentService` | **Selected** | Ownership is document-level concern; avoids service proliferation |
| Extend | `ScopeHierarchy` | **Reuse** | Already has `is_ancestor`, `get_depth` methods |
| Create | `OwnershipService` | Rejected | Would duplicate patterns already in DocumentService |

**Decision:** Extend `DocumentService` with ownership validation methods.

---

## Phase 1: ADR Text Update (Complete)

**File:** `docs/adr/011-part-2-documentation-ownership-impl/ADR-011-Part-2-Document-Ownership-Model-Implementation-Enforcement.md`

Updated Section 3.3 and 3.4 to reflect workflow-derived scope ordering (v0.93).

---

## Phase 2: Schema Migration

**New File:** `alembic/versions/20260105_001_add_parent_document_id.py`

```python
"""Add parent_document_id for document ownership (ADR-011-Part-2)"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260105_001'
down_revision = '20251231_004_add_llm_execution_logging'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('documents', sa.Column(
        'parent_document_id',
        postgresql.UUID(as_uuid=True),
        nullable=True,
        comment='Parent document for ownership hierarchy (ADR-011)'
    ))
    op.create_foreign_key(
        'fk_documents_parent', 'documents', 'documents',
        ['parent_document_id'], ['id'], ondelete='RESTRICT'
    )
    op.create_index(
        'idx_documents_parent', 'documents', ['parent_document_id'],
        postgresql_where=sa.text('parent_document_id IS NOT NULL')
    )

def downgrade() -> None:
    op.drop_index('idx_documents_parent', table_name='documents')
    op.drop_constraint('fk_documents_parent', 'documents', type_='foreignkey')
    op.drop_column('documents', 'parent_document_id')
```

---

## Phase 3: ORM Model Update

**File:** `app/api/models/document.py`

**Add column (after space_id):**

```python
parent_document_id: Mapped[Optional[UUID]] = Column(
    PG_UUID(as_uuid=True),
    ForeignKey("documents.id", ondelete="RESTRICT"),
    nullable=True,
    index=True,
    doc="Parent document ID for ownership hierarchy (ADR-011)"
)
```

**Add relationships:**

```python
parent: Mapped[Optional["Document"]] = relationship(
    "Document", remote_side=[id],
    foreign_keys=[parent_document_id], back_populates="children",
)
children: Mapped[List["Document"]] = relationship(
    "Document", foreign_keys="Document.parent_document_id",
    back_populates="parent",
)
```

**Add helper methods:**

```python
def get_ancestor_chain(self) -> List["Document"]:
    chain = []
    current = self.parent
    while current is not None:
        chain.append(current)
        current = current.parent
    return chain

def has_children(self) -> bool:
    return len(self.children) > 0
```
---

## Phase 4: Extend DocumentService with Ownership Validation

**File:** `app/api/services/document_service.py`

**Add imports:**

```python
from app.domain.workflow.scope import ScopeHierarchy
```

**Add exception classes (top of file):**

```python
class OwnershipError(Exception):
    """Base class for ownership validation errors."""
    pass

class CycleDetectedError(OwnershipError):
    """Raised when setting parent would create a cycle."""
    pass

class InvalidOwnershipError(OwnershipError):
    """Raised when parent doc_type cannot own child doc_type."""
    pass

class IncomparableScopesError(OwnershipError):
    """Raised when parent and child scopes are not on same ancestry chain."""
    pass

class ScopeViolationError(OwnershipError):
    """Raised when child scope depth < parent scope depth."""
    pass

class HasChildrenError(OwnershipError):
    """Raised when attempting to delete a document with children."""
    pass
```

**Add validation methods to DocumentService class:**

```python
async def validate_parent_assignment(
    self, child_id: UUID, proposed_parent_id: UUID,
    workflow: Optional[dict] = None,
) -> None:
    """Validate setting child.parent_document_id = proposed_parent_id."""
    child = await self.get_by_id(child_id)
    parent = await self.get_by_id(proposed_parent_id)
    
    if not child or not parent:
        raise OwnershipError("Document not found")
    
    await self._check_no_cycle(child, parent)
    
    if workflow:
        self._check_ownership_validity(child, parent, workflow)
        self._check_scope_monotonicity(child, parent, workflow)

async def _check_no_cycle(self, child: Document, proposed_parent: Document) -> None:
    """Walk parent chain. If child.id appears, reject."""
    if child.id == proposed_parent.id:
        raise CycleDetectedError(f"Document cannot own itself: {child.id}")
    
    visited = {child.id}
    current_id = proposed_parent.parent_document_id
    
    while current_id is not None:
        if current_id in visited:
            raise CycleDetectedError(
                f"Setting parent would create cycle: {child.id} -> {proposed_parent.id}"
            )
        visited.add(current_id)
        query = select(Document.parent_document_id).where(Document.id == current_id)
        result = await self.db.execute(query)
        row = result.first()
        current_id = row[0] if row else None

def _check_ownership_validity(self, child: Document, parent: Document, workflow: dict) -> None:
    """Check if parent's doc_type may_own child's doc_type per workflow."""
    doc_types = workflow.get("document_types", {})
    entity_types = workflow.get("entity_types", {})
    parent_config = doc_types.get(parent.doc_type_id, {})
    may_own = parent_config.get("may_own", [])
    
    if not may_own:
        return
    
    child_config = doc_types.get(child.doc_type_id, {})
    child_scope = child_config.get("scope")
    
    for entity_type_name in may_own:
        entity_config = entity_types.get(entity_type_name, {})
        if entity_config.get("creates_scope") == child_scope:
            return
    
    raise InvalidOwnershipError(
        f"Document type '{parent.doc_type_id}' cannot own '{child.doc_type_id}'"
    )

def _check_scope_monotonicity(self, child: Document, parent: Document, workflow: dict) -> None:
    """Check scope depth: child depth >= parent depth."""
    hierarchy = ScopeHierarchy.from_workflow(workflow)
    doc_types = workflow.get("document_types", {})
    parent_scope = doc_types.get(parent.doc_type_id, {}).get("scope")
    child_scope = doc_types.get(child.doc_type_id, {}).get("scope")
    
    if not parent_scope or not child_scope:
        return
    
    same = parent_scope == child_scope
    p_anc = hierarchy.is_ancestor(parent_scope, child_scope)
    c_anc = hierarchy.is_ancestor(child_scope, parent_scope)
    
    if not (same or p_anc or c_anc):
        raise IncomparableScopesError(
            f"Scopes '{parent_scope}' and '{child_scope}' are not comparable"
        )
    
    if hierarchy.get_depth(child_scope) < hierarchy.get_depth(parent_scope):
        raise ScopeViolationError(
            f"Child scope '{child_scope}' is broader than parent scope '{parent_scope}'"
        )

async def validate_deletion(self, document_id: UUID) -> None:
    """Check if document can be deleted (has no children)."""
    query = select(Document.id).where(Document.parent_document_id == document_id).limit(1)
    result = await self.db.execute(query)
    if result.first():
        raise HasChildrenError(f"Cannot delete document {document_id}: has children")

async def get_children(self, document_id: UUID) -> List[Document]:
    """Get all direct children of a document."""
    query = select(Document).where(Document.parent_document_id == document_id).order_by(Document.created_at)
    result = await self.db.execute(query)
    return list(result.scalars().all())

async def delete(self, document_id: UUID) -> bool:
    """Delete a document. Raises HasChildrenError if has children."""
    await self.validate_deletion(document_id)
    doc = await self.get_by_id(document_id)
    if not doc:
        return False
    await self.db.delete(doc)
    await self.db.commit()
    return True
```

---

## Phase 5: Tests

**New File:** `tests/services/test_document_ownership.py`

Test categories per ADR-011-Part-2 Section 8:

| Test Category | Test Cases |
|---------------|------------|
| **Hierarchy Creation** | `test_valid_ownership_accepted` |
| **Cycle Prevention** | `test_self_ownership_rejected`, `test_ancestor_loop_rejected` |
| **Scope Violation** | `test_child_scope_broader_rejected`, `test_child_scope_narrower_accepted` |
| **Workflow Ownership** | `test_may_own_violation_rejected` |
| **Deletion Guard** | `test_delete_with_children_rejected`, `test_delete_leaf_accepted` |

**Test Workflow Fixture:**

```python
TEST_WORKFLOW = {
    "scopes": {
        "project": {"parent": None},
        "epic": {"parent": "project"},
        "story": {"parent": "epic"},
    },
    "document_types": {
        "project_discovery": {"scope": "project", "may_own": []},
        "epic_backlog": {"scope": "project", "may_own": ["epic"]},
        "epic_architecture": {"scope": "epic", "may_own": []},
        "story_backlog": {"scope": "epic", "may_own": ["story"]},
        "story_implementation": {"scope": "story", "may_own": []},
    },
    "entity_types": {
        "epic": {"parent_doc_type": "epic_backlog", "creates_scope": "epic"},
        "story": {"parent_doc_type": "story_backlog", "creates_scope": "story"},
    },
}
```

---

## Implementation Order

| Step | File(s) | Est. Time | Status |
|------|---------|-----------|--------|
| 1 | Update ADR-011-Part-2 text | 15 min | Complete |
| 2 | Create migration | 15 min | Pending |
| 3 | Update `app/api/models/document.py` | 30 min | Pending |
| 4 | Extend `app/api/services/document_service.py` | 45 min | Pending |
| 5 | Create `tests/services/test_document_ownership.py` | 45 min | Pending |
| 6 | Run tests, fix issues | 30 min | Pending |

**Total Estimated Time:** ~3 hours

---

## Files to Create/Modify

| Action | File |
|--------|------|
| Modified | `docs/adr/.../ADR-011-Part-2-...` (v0.93) |
| Create | `alembic/versions/20260105_001_add_parent_document_id.py` |
| Modify | `app/api/models/document.py` |
| Modify | `app/api/services/document_service.py` |
| Create | `tests/services/test_document_ownership.py` |

---

_Last updated: 2026-01-05_
