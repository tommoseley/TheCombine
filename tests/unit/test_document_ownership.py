"""
Tests for ADR-011-Part-2 Document Ownership (DocumentService extension).

Test Categories per ADR-011-Part-2 Section 8:
1. Hierarchy Creation - valid parent/child assignment
2. Cycle Prevention - self-ownership, ancestor loops
3. Scope Violation - child scope broader than parent
4. Workflow Ownership Violation - parent/child type not allowed
5. Deletion Guard - prevent deletion when children exist
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from app.api.services.document_service import (
    DocumentService,
    OwnershipError,
    CycleDetectedError,
    InvalidOwnershipError,
    IncomparableScopesError,
    ScopeViolationError,
    HasChildrenError,
)
from app.api.models.document import Document


# =============================================================================
# TEST FIXTURES
# =============================================================================

TEST_WORKFLOW = {
    "scopes": {
        "project": {"parent": None},
        "epic": {"parent": "project"},
        "task": {"parent": "epic"},
    },
    "document_types": {
        "project_discovery": {"scope": "project", "may_own": []},
        "epic_backlog": {"scope": "project", "may_own": ["epic"]},
        "epic_architecture": {"scope": "epic", "may_own": []},
        "task_backlog": {"scope": "epic", "may_own": ["task"]},
        "task_detail": {"scope": "task", "may_own": []},
    },
    "entity_types": {
        "epic": {"parent_doc_type": "epic_backlog", "creates_scope": "epic"},
        "task": {"parent_doc_type": "task_backlog", "creates_scope": "task"},
    },
}

BRANCHED_WORKFLOW = {
    "scopes": {
        "project": {"parent": None},
        "epic": {"parent": "project"},
        "task": {"parent": "project"},
    },
    "document_types": {
        "project_doc": {"scope": "project", "may_own": []},
        "epic_doc": {"scope": "epic", "may_own": []},
        "task_doc": {"scope": "task", "may_own": []},
    },
    "entity_types": {},
}


def make_mock_document(doc_id=None, doc_type_id="project_discovery", parent_id=None):
    """Create a mock Document for testing."""
    doc = MagicMock(spec=Document)
    doc.id = doc_id or uuid4()
    doc.doc_type_id = doc_type_id
    doc.parent_document_id = parent_id
    return doc

# =============================================================================
# CATEGORY 2: CYCLE PREVENTION (5 tests)
# =============================================================================

class TestCycleDetection:
    """Test cycle detection in ownership hierarchy."""
    
    @pytest.mark.asyncio
    async def test_self_ownership_rejected(self):
        """Document cannot own itself."""
        doc_id = uuid4()
        doc = make_mock_document(doc_id=doc_id)
        
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=doc)
        ))
        
        svc = DocumentService(mock_db)
        
        with pytest.raises(CycleDetectedError, match="cannot own itself"):
            await svc.validate_parent_assignment(doc_id, doc_id)
    
    @pytest.mark.asyncio
    async def test_direct_cycle_rejected(self):
        """A -> B exists, then B -> A rejected."""
        doc_a_id, doc_b_id = uuid4(), uuid4()
        doc_a = make_mock_document(doc_id=doc_a_id, parent_id=None)
        doc_b = make_mock_document(doc_id=doc_b_id, parent_id=doc_a_id)
        
        mock_db = AsyncMock()
        call_count = [0]
        
        async def mock_execute(query):
            result = MagicMock()
            if call_count[0] == 0:
                result.scalar_one_or_none = MagicMock(return_value=doc_a)
            elif call_count[0] == 1:
                result.scalar_one_or_none = MagicMock(return_value=doc_b)
            else:
                result.first = MagicMock(return_value=(doc_a_id,))
            call_count[0] += 1
            return result
        
        mock_db.execute = mock_execute
        svc = DocumentService(mock_db)
        
        with pytest.raises(CycleDetectedError, match="create cycle"):
            await svc.validate_parent_assignment(doc_a_id, doc_b_id)
    
    @pytest.mark.asyncio
    async def test_ancestor_loop_three_nodes_rejected(self):
        """A -> B -> C exists, then C -> A rejected."""
        ids = [uuid4() for _ in range(3)]
        doc_a = make_mock_document(doc_id=ids[0], parent_id=None)
        doc_c = make_mock_document(doc_id=ids[2], parent_id=ids[1])
        
        mock_db = AsyncMock()
        call_count = [0]
        
        async def mock_execute(query):
            result = MagicMock()
            if call_count[0] == 0:
                result.scalar_one_or_none = MagicMock(return_value=doc_a)
            elif call_count[0] == 1:
                result.scalar_one_or_none = MagicMock(return_value=doc_c)
            elif call_count[0] == 2:
                result.first = MagicMock(return_value=(ids[1],))
            elif call_count[0] == 3:
                result.first = MagicMock(return_value=(ids[0],))
            call_count[0] += 1
            return result
        
        mock_db.execute = mock_execute
        svc = DocumentService(mock_db)
        
        with pytest.raises(CycleDetectedError, match="create cycle"):
            await svc.validate_parent_assignment(ids[0], ids[2])
    
    @pytest.mark.asyncio
    async def test_no_cycle_valid_assignment(self):
        """Valid parent assignment (no cycle) succeeds."""
        parent_id, child_id = uuid4(), uuid4()
        parent = make_mock_document(doc_id=parent_id, parent_id=None)
        child = make_mock_document(doc_id=child_id, parent_id=None)
        
        mock_db = AsyncMock()
        call_count = [0]
        
        async def mock_execute(query):
            result = MagicMock()
            if call_count[0] == 0:
                result.scalar_one_or_none = MagicMock(return_value=child)
            elif call_count[0] == 1:
                result.scalar_one_or_none = MagicMock(return_value=parent)
            call_count[0] += 1
            return result
        
        mock_db.execute = mock_execute
        svc = DocumentService(mock_db)
        await svc.validate_parent_assignment(child_id, parent_id)
    
    @pytest.mark.asyncio
    async def test_deep_chain_no_cycle(self):
        """Deep chain A->B->C->D, adding E as child of D succeeds."""
        # Chain: A(0) -> B(1) -> C(2) -> D(3), adding E(4) as child of D
        ids = [uuid4() for _ in range(5)]
        
        mock_db = AsyncMock()
        call_count = [0]
        
        async def mock_execute(query):
            result = MagicMock()
            if call_count[0] == 0:
                # get_by_id for child E
                result.scalar_one_or_none = MagicMock(
                    return_value=make_mock_document(doc_id=ids[4], parent_id=None)
                )
            elif call_count[0] == 1:
                # get_by_id for parent D (D's parent is C)
                result.scalar_one_or_none = MagicMock(
                    return_value=make_mock_document(doc_id=ids[3], parent_id=ids[2])
                )
            elif call_count[0] == 2:
                # Query C's parent -> B
                result.first = MagicMock(return_value=(ids[1],))
            elif call_count[0] == 3:
                # Query B's parent -> A
                result.first = MagicMock(return_value=(ids[0],))
            elif call_count[0] == 4:
                # Query A's parent -> None (root)
                result.first = MagicMock(return_value=None)
            call_count[0] += 1
            return result
        
        mock_db.execute = mock_execute
        svc = DocumentService(mock_db)
        await svc.validate_parent_assignment(ids[4], ids[3])


# =============================================================================
# CATEGORY 3: SCOPE VIOLATION (9 tests)
# =============================================================================

class TestScopeMonotonicity:
    """Test scope depth validation."""
    
    def test_child_scope_narrower_accepted(self):
        """Child with narrower scope (higher depth) is valid."""
        parent = make_mock_document(doc_type_id="task_backlog")
        child = make_mock_document(doc_type_id="task_detail")
        svc = DocumentService(AsyncMock())
        svc._check_scope_monotonicity(child, parent, TEST_WORKFLOW)
    
    def test_child_scope_broader_rejected(self):
        """Child with broader scope (lower depth) is invalid."""
        parent = make_mock_document(doc_type_id="task_detail")
        child = make_mock_document(doc_type_id="epic_architecture")
        svc = DocumentService(AsyncMock())
        with pytest.raises(ScopeViolationError, match="broader than"):
            svc._check_scope_monotonicity(child, parent, TEST_WORKFLOW)
    
    def test_same_scope_accepted(self):
        """Same scope is valid (depth equal)."""
        parent = make_mock_document(doc_type_id="epic_architecture")
        child = make_mock_document(doc_type_id="task_backlog")
        svc = DocumentService(AsyncMock())
        svc._check_scope_monotonicity(child, parent, TEST_WORKFLOW)
    
    def test_root_scope_to_root_scope_accepted(self):
        """Root scope to root scope is valid."""
        parent = make_mock_document(doc_type_id="project_discovery")
        child = make_mock_document(doc_type_id="epic_backlog")
        svc = DocumentService(AsyncMock())
        svc._check_scope_monotonicity(child, parent, TEST_WORKFLOW)
    
    def test_project_to_task_accepted(self):
        """Project to task (multi-level jump) is valid."""
        parent = make_mock_document(doc_type_id="project_discovery")
        child = make_mock_document(doc_type_id="task_detail")
        svc = DocumentService(AsyncMock())
        svc._check_scope_monotonicity(child, parent, TEST_WORKFLOW)
    
    def test_task_to_project_rejected(self):
        """Task to project (reverse direction) is invalid."""
        parent = make_mock_document(doc_type_id="task_detail")
        child = make_mock_document(doc_type_id="project_discovery")
        svc = DocumentService(AsyncMock())
        with pytest.raises(ScopeViolationError, match="broader than"):
            svc._check_scope_monotonicity(child, parent, TEST_WORKFLOW)
    
    def test_incomparable_scopes_rejected(self):
        """Scopes not on same ancestry chain are rejected."""
        parent = make_mock_document(doc_type_id="epic_doc")
        child = make_mock_document(doc_type_id="task_doc")
        svc = DocumentService(AsyncMock())
        with pytest.raises(IncomparableScopesError, match="not comparable"):
            svc._check_scope_monotonicity(child, parent, BRANCHED_WORKFLOW)
    
    def test_missing_parent_scope_skips(self):
        """Missing parent scope info skips validation."""
        parent = make_mock_document(doc_type_id="unknown_type")
        child = make_mock_document(doc_type_id="task_detail")
        svc = DocumentService(AsyncMock())
        svc._check_scope_monotonicity(child, parent, TEST_WORKFLOW)
    
    def test_missing_child_scope_skips(self):
        """Missing child scope info skips validation."""
        parent = make_mock_document(doc_type_id="project_discovery")
        child = make_mock_document(doc_type_id="unknown_type")
        svc = DocumentService(AsyncMock())
        svc._check_scope_monotonicity(child, parent, TEST_WORKFLOW)


# =============================================================================
# CATEGORY 4: WORKFLOW OWNERSHIP VIOLATION (6 tests)
# =============================================================================

class TestOwnershipValidity:
    """Test workflow may_own rules."""
    
    def test_valid_may_own_accepted(self):
        """Parent that may_own child entity type is valid."""
        parent = make_mock_document(doc_type_id="epic_backlog")
        child = make_mock_document(doc_type_id="epic_architecture")
        svc = DocumentService(AsyncMock())
        svc._check_ownership_validity(child, parent, TEST_WORKFLOW)
    
    def test_empty_may_own_defers(self):
        """Empty may_own defers to scope check."""
        parent = make_mock_document(doc_type_id="project_discovery")
        child = make_mock_document(doc_type_id="epic_architecture")
        svc = DocumentService(AsyncMock())
        svc._check_ownership_validity(child, parent, TEST_WORKFLOW)
    
    def test_wrong_entity_type_rejected(self):
        """Parent may_own different entity type is invalid."""
        parent = make_mock_document(doc_type_id="task_backlog")
        child = make_mock_document(doc_type_id="epic_architecture")
        svc = DocumentService(AsyncMock())
        with pytest.raises(InvalidOwnershipError, match="cannot own"):
            svc._check_ownership_validity(child, parent, TEST_WORKFLOW)
    
    def test_task_backlog_owns_task_scope(self):
        """task_backlog can own documents with task scope."""
        parent = make_mock_document(doc_type_id="task_backlog")
        child = make_mock_document(doc_type_id="task_detail")
        svc = DocumentService(AsyncMock())
        svc._check_ownership_validity(child, parent, TEST_WORKFLOW)
    
    def test_unknown_parent_doc_type_skips(self):
        """Unknown parent doc_type skips ownership check."""
        parent = make_mock_document(doc_type_id="unknown_type")
        child = make_mock_document(doc_type_id="task_detail")
        svc = DocumentService(AsyncMock())
        svc._check_ownership_validity(child, parent, TEST_WORKFLOW)

    def test_unknown_child_with_parent_may_own_rejected(self):
        """Unknown child when parent has may_own is rejected."""
        parent = make_mock_document(doc_type_id="epic_backlog")
        child = make_mock_document(doc_type_id="unknown_type")
        svc = DocumentService(AsyncMock())
        with pytest.raises(InvalidOwnershipError, match="cannot own"):
            svc._check_ownership_validity(child, parent, TEST_WORKFLOW)


# =============================================================================
# CATEGORY 5: DELETION GUARD (5 tests)
# =============================================================================

class TestDeletionGuard:
    """Test deletion prevention for documents with children."""
    
    @pytest.mark.asyncio
    async def test_delete_with_one_child_rejected(self):
        """Cannot delete document with one child."""
        parent_id = uuid4()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=(uuid4(),))
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        svc = DocumentService(mock_db)
        with pytest.raises(HasChildrenError, match="has children"):
            await svc.validate_deletion(parent_id)
    
    @pytest.mark.asyncio
    async def test_delete_with_multiple_children_rejected(self):
        """Cannot delete document with multiple children."""
        parent_id = uuid4()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=(uuid4(),))
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        svc = DocumentService(mock_db)
        with pytest.raises(HasChildrenError, match="has children"):
            await svc.validate_deletion(parent_id)
    
    @pytest.mark.asyncio
    async def test_delete_leaf_accepted(self):
        """Can delete document without children."""
        doc_id = uuid4()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        svc = DocumentService(mock_db)
        await svc.validate_deletion(doc_id)
    
    @pytest.mark.asyncio
    async def test_delete_method_validates_first(self):
        """delete() calls validate_deletion first."""
        parent_id = uuid4()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=(uuid4(),))
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        svc = DocumentService(mock_db)
        with pytest.raises(HasChildrenError):
            await svc.delete(parent_id)
    
    @pytest.mark.asyncio
    async def test_delete_returns_false_for_missing_doc(self):
        """delete() returns False if document not found."""
        doc_id = uuid4()
        mock_db = AsyncMock()
        call_count = [0]
        
        async def mock_execute(query):
            result = MagicMock()
            if call_count[0] == 0:
                result.first = MagicMock(return_value=None)
            else:
                result.scalar_one_or_none = MagicMock(return_value=None)
            call_count[0] += 1
            return result
        
        mock_db.execute = mock_execute
        svc = DocumentService(mock_db)
        result = await svc.delete(doc_id)
        assert result is False


# =============================================================================
# CATEGORY 1: HIERARCHY CREATION (4 tests)
# =============================================================================

class TestHierarchyCreation:
    """Test valid parent/child assignment."""
    
    @pytest.mark.asyncio
    async def test_valid_ownership_with_workflow(self):
        """Valid assignment with workflow succeeds."""
        parent_id, child_id = uuid4(), uuid4()
        parent = make_mock_document(doc_id=parent_id, doc_type_id="epic_backlog")
        child = make_mock_document(doc_id=child_id, doc_type_id="epic_architecture")
        
        mock_db = AsyncMock()
        call_count = [0]
        
        async def mock_execute(query):
            result = MagicMock()
            if call_count[0] == 0:
                result.scalar_one_or_none = MagicMock(return_value=child)
            elif call_count[0] == 1:
                result.scalar_one_or_none = MagicMock(return_value=parent)
            call_count[0] += 1
            return result
        
        mock_db.execute = mock_execute
        svc = DocumentService(mock_db)
        await svc.validate_parent_assignment(child_id, parent_id, workflow=TEST_WORKFLOW)
    
    @pytest.mark.asyncio
    async def test_valid_ownership_without_workflow(self):
        """Valid assignment without workflow (cycle check only)."""
        parent_id, child_id = uuid4(), uuid4()
        parent = make_mock_document(doc_id=parent_id, parent_id=None)
        child = make_mock_document(doc_id=child_id, parent_id=None)
        
        mock_db = AsyncMock()
        call_count = [0]
        
        async def mock_execute(query):
            result = MagicMock()
            if call_count[0] == 0:
                result.scalar_one_or_none = MagicMock(return_value=child)
            elif call_count[0] == 1:
                result.scalar_one_or_none = MagicMock(return_value=parent)
            call_count[0] += 1
            return result
        
        mock_db.execute = mock_execute
        svc = DocumentService(mock_db)
        await svc.validate_parent_assignment(child_id, parent_id)
    
    @pytest.mark.asyncio
    async def test_document_not_found_raises(self):
        """Raises OwnershipError if document not found."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        svc = DocumentService(mock_db)
        with pytest.raises(OwnershipError, match="not found"):
            await svc.validate_parent_assignment(uuid4(), uuid4())
    
    @pytest.mark.asyncio
    async def test_root_document_assignment(self):
        """Root document (no parent) assignment works."""
        parent_id, child_id = uuid4(), uuid4()
        parent = make_mock_document(doc_id=parent_id, doc_type_id="project_discovery", parent_id=None)
        child = make_mock_document(doc_id=child_id, doc_type_id="epic_backlog", parent_id=None)
        
        mock_db = AsyncMock()
        call_count = [0]
        
        async def mock_execute(query):
            result = MagicMock()
            if call_count[0] == 0:
                result.scalar_one_or_none = MagicMock(return_value=child)
            elif call_count[0] == 1:
                result.scalar_one_or_none = MagicMock(return_value=parent)
            call_count[0] += 1
            return result
        
        mock_db.execute = mock_execute
        svc = DocumentService(mock_db)
        await svc.validate_parent_assignment(child_id, parent_id, workflow=TEST_WORKFLOW)


# =============================================================================
# QUERY METHODS (3 tests)
# =============================================================================

class TestQueryMethods:
    """Test get_children and get_subtree methods."""
    
    @pytest.mark.asyncio
    async def test_get_children_returns_list(self):
        """get_children returns list of child documents."""
        parent_id = uuid4()
        child1 = make_mock_document(doc_id=uuid4(), parent_id=parent_id)
        child2 = make_mock_document(doc_id=uuid4(), parent_id=parent_id)
        
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[child1, child2])
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        svc = DocumentService(mock_db)
        children = await svc.get_children(parent_id)
        
        assert len(children) == 2
        assert child1 in children
        assert child2 in children
    
    @pytest.mark.asyncio
    async def test_get_children_empty_list(self):
        """get_children returns empty list for leaf."""
        leaf_id = uuid4()
        
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        svc = DocumentService(mock_db)
        children = await svc.get_children(leaf_id)
        assert children == []
    
    @pytest.mark.asyncio
    async def test_get_subtree_flat(self):
        """get_subtree returns all descendants."""
        parent_id = uuid4()
        child1 = make_mock_document(doc_id=uuid4(), parent_id=parent_id)
        child2 = make_mock_document(doc_id=uuid4(), parent_id=parent_id)
        
        mock_db = AsyncMock()
        call_count = [0]
        
        async def mock_execute(query):
            result = MagicMock()
            mock_scalars = MagicMock()
            if call_count[0] == 0:
                mock_scalars.all = MagicMock(return_value=[child1, child2])
            else:
                mock_scalars.all = MagicMock(return_value=[])
            result.scalars = MagicMock(return_value=mock_scalars)
            call_count[0] += 1
            return result
        
        mock_db.execute = mock_execute
        svc = DocumentService(mock_db)
        subtree = await svc.get_subtree(parent_id)
        
        assert len(subtree) == 2
        assert child1 in subtree
        assert child2 in subtree


# =============================================================================
# EDGE CASES (3 tests)
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_workflow_skips_checks(self):
        """Empty workflow skips ownership and scope checks."""
        parent = make_mock_document(doc_type_id="anything")
        child = make_mock_document(doc_type_id="anything_else")
        empty_workflow = {"scopes": {}, "document_types": {}, "entity_types": {}}
        
        svc = DocumentService(AsyncMock())
        svc._check_ownership_validity(child, parent, empty_workflow)
        svc._check_scope_monotonicity(child, parent, empty_workflow)
    
    def test_workflow_missing_entity_types(self):
        """Workflow without entity_types still validates."""
        parent = make_mock_document(doc_type_id="project_discovery")
        child = make_mock_document(doc_type_id="epic_architecture")
        partial_workflow = {
            "scopes": TEST_WORKFLOW["scopes"],
            "document_types": TEST_WORKFLOW["document_types"],
        }
        
        svc = DocumentService(AsyncMock())
        svc._check_ownership_validity(child, parent, partial_workflow)
    
    def test_workflow_missing_document_types(self):
        """Workflow without document_types skips checks."""
        parent = make_mock_document(doc_type_id="project_discovery")
        child = make_mock_document(doc_type_id="epic_architecture")
        partial_workflow = {
            "scopes": TEST_WORKFLOW["scopes"],
            "entity_types": TEST_WORKFLOW["entity_types"],
        }
        
        svc = DocumentService(AsyncMock())
        svc._check_ownership_validity(child, parent, partial_workflow)
        svc._check_scope_monotonicity(child, parent, partial_workflow)
