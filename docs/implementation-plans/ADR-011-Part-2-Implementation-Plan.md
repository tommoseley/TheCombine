# ADR-011-Part-2 Implementation Plan

**Created:** 2026-01-05  
**ADR Version:** 0.93  
**Status:** Ready for implementation

---

## Summary of Changes

**ADR Update:** Replace fixed scope ranks with workflow-derived ordering  
**Implementation:** Two-layer validation (ownership validity + scope monotonicity)

---

## Phase 1: ADR Text Update (Complete)

**File:** `docs/adr/011-part-2-documentation-ownership-impl/ADR-011-Part-2-Document-Ownership-Model-Implementation-Enforcement.md`

**Completed:** Section 3.3 and 3.4 updated to reflect workflow-derived scope ordering.

---

## Phase 2: Schema Migration

**New File:** `alembic/versions/20260105_001_add_parent_document_id.py`

```python
"""Add parent_document_id for document ownership (ADR-011-Part-2)

Revision ID: 20260105_001
Revises: 20251231_004_add_llm_execution_logging
Create Date: 2026-01-05
"""
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
        sa.ForeignKey('documents.id', ondelete='RESTRICT'),
        nullable=True,
        comment='Parent document for ownership hierarchy (ADR-011)'
    ))
    
    op.create_index(
        'idx_documents_parent',
        'documents',
        ['parent_document_id'],
        postgresql_where=sa.text('parent_document_id IS NOT NULL')
    )

def downgrade() -> None:
    op.drop_index('idx_documents_parent', table_name='documents')
    op.drop_column('documents', 'parent_document_id')
```

---

## Phase 3: ORM Model Update

**File:** `app/api/models/document.py`

**Add to OWNERSHIP section (after space_id):**

```python
# DOCUMENT OWNERSHIP (ADR-011-Part-2)
parent_document_id: Mapped[Optional[UUID]] = Column(
    PG_UUID(as_uuid=True),
    ForeignKey("documents.id", ondelete="RESTRICT"),
    nullable=True,
    index=True,
    doc="Parent document ID for ownership hierarchy (ADR-011)"
)
```

**Add to RELATIONSHIPS section:**

```python
# Ownership hierarchy (ADR-011-Part-2)
parent: Mapped[Optional["Document"]] = relationship(
    "Document",
    remote_side=[id],
    foreign_keys=[parent_document_id],
    back_populates="children",
)

children: Mapped[List["Document"]] = relationship(
    "Document",
    foreign_keys="Document.parent_document_id",
    back_populates="parent",
)
```

**Add helper methods:**

```python
def get_ancestor_chain(self) -> List["Document"]:
    """Walk parent chain upward. Returns [parent, grandparent, ...] or []."""
    chain = []
    current = self.parent
    while current is not None:
        chain.append(current)
        current = current.parent
    return chain

def has_children(self) -> bool:
    """Check if document has any children."""
    return len(self.children) > 0
```
---

## Phase 4: Ownership Service

**New File:** `app/domain/services/ownership_service.py`

```python
"""
Document Ownership Service - ADR-011-Part-2 enforcement.

Two-layer validation:
1. Ownership validity (graph-based, primary) - may_own check
2. Scope monotonicity (derived, secondary) - depth comparison
"""

from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.models.document import Document
from app.api.models.document_type import DocumentType
from app.domain.workflow.scope import ScopeHierarchy


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


class OwnershipService:
    """
    Enforces document ownership rules per ADR-011-Part-2.
    
    Validations (in order):
    1. Cycle detection (DAG enforcement)
    2. Ownership validity (may_own from workflow)
    3. Scope monotonicity (depth comparison)
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def validate_parent_assignment(
        self,
        child_id: UUID,
        proposed_parent_id: UUID,
        workflow: Optional[dict] = None,
    ) -> None:
        """Validate that setting child.parent_document_id = proposed_parent_id is allowed."""
        child = await self._load_document_with_type(child_id)
        parent = await self._load_document_with_type(proposed_parent_id)
        
        if not child or not parent:
            raise OwnershipError("Document not found")
        
        await self._check_no_cycle(child, parent)
        
        if workflow:
            self._check_ownership_validity(child, parent, workflow)
            self._check_scope_monotonicity(child, parent, workflow)
    
    async def validate_deletion(self, document_id: UUID) -> None:
        """Check if document can be deleted (has no children)."""
        query = select(Document.id).where(
            Document.parent_document_id == document_id
        ).limit(1)
        result = await self.db.execute(query)
        
        if result.first():
            raise HasChildrenError(f"Cannot delete document {document_id}: has children")
    
    async def get_children(self, document_id: UUID) -> list[Document]:
        """Get all direct children of a document."""
        query = (
            select(Document)
            .where(Document.parent_document_id == document_id)
            .order_by(Document.created_at)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_subtree(self, document_id: UUID) -> list[Document]:
        """Get entire subtree rooted at document."""
        subtree = []
        children = await self.get_children(document_id)
        for child in children:
            subtree.append(child)
            subtree.extend(await self.get_subtree(child.id))
        return subtree
```

See full implementation in Phase 4 section of the plan for complete method implementations.
---

## Phase 5: Integrate with DocumentService

**File:** `app/api/services/document_service.py`

**Add import:**

```python
from app.domain.services.ownership_service import (
    OwnershipService,
    OwnershipError,
    HasChildrenError,
)
```

**Update `create_document` signature:**

```python
async def create_document(
    self,
    # ... existing params ...
    parent_document_id: Optional[UUID] = None,  # NEW
    workflow: Optional[dict] = None,  # NEW
) -> Document:
```

**Add deletion guard:**

```python
async def delete(self, document_id: UUID) -> bool:
    """Delete a document (hard delete). Raises HasChildrenError if has children."""
    ownership_svc = OwnershipService(self.db)
    await ownership_svc.validate_deletion(document_id)
    
    doc = await self.get_by_id(document_id)
    if not doc:
        return False
    
    await self.db.delete(doc)
    await self.db.commit()
    return True
```

---

## Phase 6: Tests

**New File:** `tests/domain/test_ownership_service.py`

Test categories per ADR-011-Part-2 Section 8:

| Test Category | Description |
|---------------|-------------|
| **Hierarchy Creation** | Valid parent/child assignment |
| **Cycle Prevention** | Self-ownership, ancestor loops |
| **Scope Violation** | Child scope exceeding parent |
| **Workflow Ownership Violation** | Parent/child type not allowed by workflow |
| **Deletion Guard** | Prevent deletion when children exist |

Key test cases:
- `test_self_ownership_rejected` - Document cannot own itself
- `test_ancestor_loop_rejected` - A -> B -> C, then C -> A rejected
- `test_child_scope_narrower_accepted` - Epic doc can own story doc
- `test_child_scope_broader_rejected` - Story doc cannot own epic doc
- `test_delete_with_children_rejected` - Cannot delete document with children
- `test_delete_leaf_accepted` - Can delete document without children
- `test_valid_ownership_accepted` - Valid parent/child assignment succeeds

---

## Phase 7: Implementation Order

| Step | File(s) | Est. Time | Status |
|------|---------|-----------|--------|
| 1 | Update ADR-011-Part-2 text | 15 min | Complete |
| 2 | Create migration | 15 min | Pending |
| 3 | Update document.py model | 30 min | Pending |
| 4 | Create ownership_service.py | 45 min | Pending |
| 5 | Update document_service.py | 30 min | Pending |
| 6 | Create test_ownership_service.py | 45 min | Pending |
| 7 | Run tests, fix issues | 30 min | Pending |

**Total Estimated Time:** ~3.5 hours

---

## Key Design Decisions

1. **Workflow-derived scope ordering** - No fixed rank constants; depth computed from workflow scopes

2. **Two-layer validation:**
   - Layer 1 (Primary): Ownership validity via `may_own`
   - Layer 2 (Secondary): Scope monotonicity via depth comparison

3. **Comparability check** - Scopes must be on same ancestry chain; incomparable scopes rejected

4. **Enforcement scope:**
   - Hard invariants (single parent, no cycles): Always enforced
   - Workflow constraints: Enforced only during workflow execution

5. **No global policing** - Outside workflow context, only hard invariants apply

---

## Files to Create/Modify

| Action | File |
|--------|------|
| Modified | `docs/adr/.../ADR-011-Part-2-Document-Ownership-Model-Implementation-Enforcement.md` |
| Create | `alembic/versions/20260105_001_add_parent_document_id.py` |
| Modify | `app/api/models/document.py` |
| Create | `app/domain/services/ownership_service.py` |
| Modify | `app/api/services/document_service.py` |
| Create | `tests/domain/test_ownership_service.py` |

---

_Last updated: 2026-01-05_