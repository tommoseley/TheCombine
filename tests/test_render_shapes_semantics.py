"""
Render Shape Semantics - Frozen Invariant Tests

These tests validate the authoritative semantics defined in:
docs/governance/RENDER_SHAPES_SEMANTICS.md

These are NOT implementation tests - they are CONTRACT tests.
If any of these fail, it means the semantic contract has been violated.

Changes to these tests require governance approval.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from app.domain.services.render_model_builder import RenderModelBuilder


class TestRenderShapeSemantics:
    """
    Frozen semantic invariants for render shapes.
    
    DO NOT modify these tests without governance approval.
    These define the contract, not the implementation.
    """
    
    # =========================================================================
    # INVARIANT 1: container without repeat_over => exactly 1 block
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_container_no_repeat_over_produces_exactly_one_block(self):
        """
        FROZEN INVARIANT: container shape without repeat_over produces exactly 1 block.
        
        Governance: RENDER_SHAPES_SEMANTICS.md Section 4
        """
        mock_docdef_service = AsyncMock()
        mock_component_service = AsyncMock()
        
        docdef = MagicMock()
        docdef.document_def_id = "docdef:Test:1.0.0"
        docdef.sections = [{
            "section_id": "root_container",
            "order": 10,
            "component_id": "component:TestV1:1.0.0",
            "shape": "container",
            "source_pointer": "/items"
            # NO repeat_over
        }]
        
        component = MagicMock()
        component.schema_id = "schema:TestV1"
        
        mock_docdef_service.get.return_value = docdef
        mock_component_service.get.return_value = component
        
        builder = RenderModelBuilder(
            docdef_service=mock_docdef_service,
            component_service=mock_component_service,
        )
        
        document_data = {
            "items": [
                {"id": "1", "value": "a"},
                {"id": "2", "value": "b"},
                {"id": "3", "value": "c"},
            ]
        }
        
        result = await builder.build("docdef:Test:1.0.0", document_data)
        
        # INVARIANT: exactly 1 block
        assert len(result.blocks) == 1, \
            f"SEMANTIC VIOLATION: container without repeat_over must produce exactly 1 block, got {len(result.blocks)}"
        
        # Block contains all items
        assert len(result.blocks[0].data["items"]) == 3
    
    # =========================================================================
    # INVARIANT 2: container + repeat_over => exactly N blocks (per parent)
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_container_with_repeat_over_produces_n_blocks_per_parent(self):
        """
        FROZEN INVARIANT: container shape with repeat_over produces 1 block per parent.
        
        Governance: RENDER_SHAPES_SEMANTICS.md Section 4
        """
        mock_docdef_service = AsyncMock()
        mock_component_service = AsyncMock()
        
        docdef = MagicMock()
        docdef.document_def_id = "docdef:Test:1.0.0"
        docdef.sections = [{
            "section_id": "parent_containers",
            "order": 10,
            "component_id": "component:TestV1:1.0.0",
            "shape": "container",
            "source_pointer": "/children",
            "repeat_over": "/parents",
            "context": {"parent_id": "/id"}
        }]
        
        component = MagicMock()
        component.schema_id = "schema:TestV1"
        
        mock_docdef_service.get.return_value = docdef
        mock_component_service.get.return_value = component
        
        builder = RenderModelBuilder(
            docdef_service=mock_docdef_service,
            component_service=mock_component_service,
        )
        
        document_data = {
            "parents": [
                {"id": "P1", "children": [{"c": 1}, {"c": 2}]},
                {"id": "P2", "children": [{"c": 3}]},
                {"id": "P3", "children": [{"c": 4}, {"c": 5}, {"c": 6}]},
            ]
        }
        
        result = await builder.build("docdef:Test:1.0.0", document_data)
        
        # INVARIANT: exactly 3 blocks (one per parent)
        assert len(result.blocks) == 3, \
            f"SEMANTIC VIOLATION: container + repeat_over must produce 1 block per parent, got {len(result.blocks)}"
        
        # Each block has correct context
        assert result.blocks[0].context["parent_id"] == "P1"
        assert result.blocks[1].context["parent_id"] == "P2"
        assert result.blocks[2].context["parent_id"] == "P3"
        
        # Each block has correct item count
        assert len(result.blocks[0].data["items"]) == 2
        assert len(result.blocks[1].data["items"]) == 1
        assert len(result.blocks[2].data["items"]) == 3
    
    # =========================================================================
    # INVARIANT 3: nested_list => N blocks (per item across all parents)
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_nested_list_produces_n_blocks_per_item(self):
        """
        FROZEN INVARIANT: nested_list shape produces 1 block per item across all parents.
        
        Governance: RENDER_SHAPES_SEMANTICS.md Section 3
        """
        mock_docdef_service = AsyncMock()
        mock_component_service = AsyncMock()
        
        docdef = MagicMock()
        docdef.document_def_id = "docdef:Test:1.0.0"
        docdef.sections = [{
            "section_id": "nested_items",
            "order": 10,
            "component_id": "component:TestV1:1.0.0",
            "shape": "nested_list",
            "source_pointer": "/items",
            "repeat_over": "/parents",
            "context": {"parent_id": "/id"}
        }]
        
        component = MagicMock()
        component.schema_id = "schema:TestV1"
        
        mock_docdef_service.get.return_value = docdef
        mock_component_service.get.return_value = component
        
        builder = RenderModelBuilder(
            docdef_service=mock_docdef_service,
            component_service=mock_component_service,
        )
        
        document_data = {
            "parents": [
                {"id": "P1", "items": [{"x": 1}, {"x": 2}]},      # 2 items
                {"id": "P2", "items": [{"x": 3}]},                 # 1 item
                {"id": "P3", "items": [{"x": 4}, {"x": 5}]},       # 2 items
            ]
        }
        
        result = await builder.build("docdef:Test:1.0.0", document_data)
        
        # INVARIANT: 5 blocks (one per item: 2 + 1 + 2)
        assert len(result.blocks) == 5, \
            f"SEMANTIC VIOLATION: nested_list must produce 1 block per item, got {len(result.blocks)}"
        
        # First 2 blocks have P1 context
        assert result.blocks[0].context["parent_id"] == "P1"
        assert result.blocks[1].context["parent_id"] == "P1"
        
        # Third block has P2 context
        assert result.blocks[2].context["parent_id"] == "P2"
        
        # Last 2 blocks have P3 context
        assert result.blocks[3].context["parent_id"] == "P3"
        assert result.blocks[4].context["parent_id"] == "P3"
    
    # =========================================================================
    # INVARIANT 4: Deep nesting boundary - produces empty (intentional)
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_deep_nesting_boundary_produces_no_blocks(self):
        """
        FROZEN BOUNDARY: Deep nesting (3+ levels) is not supported and produces no blocks.
        
        This is BY DESIGN. Do not "fix" this without governance approval.
        
        Governance: RENDER_SHAPES_SEMANTICS.md "Documented Boundary"
        """
        mock_docdef_service = AsyncMock()
        mock_component_service = AsyncMock()
        
        docdef = MagicMock()
        docdef.document_def_id = "docdef:Test:1.0.0"
        docdef.sections = [{
            "section_id": "deep_items",
            "order": 10,
            "component_id": "component:TestV1:1.0.0",
            "shape": "container",
            "source_pointer": "/deep_items",  # This doesn't exist directly under parents
            "repeat_over": "/parents",
            "context": {"parent_id": "/id"}
        }]
        
        component = MagicMock()
        component.schema_id = "schema:TestV1"
        
        mock_docdef_service.get.return_value = docdef
        mock_component_service.get.return_value = component
        
        builder = RenderModelBuilder(
            docdef_service=mock_docdef_service,
            component_service=mock_component_service,
        )
        
        # Deep structure: /parents/*/children/*/deep_items
        # But source_pointer only resolves one level: /parents/*/deep_items (doesn't exist)
        document_data = {
            "parents": [
                {
                    "id": "P1",
                    "children": [
                        {"id": "C1", "deep_items": [{"d": 1}]},
                        {"id": "C2", "deep_items": [{"d": 2}]},
                    ]
                }
            ]
        }
        
        result = await builder.build("docdef:Test:1.0.0", document_data)
        
        # BOUNDARY: No blocks produced (deep_items not found at parent level)
        assert len(result.blocks) == 0, \
            f"BOUNDARY VIOLATION: Deep nesting should produce 0 blocks, got {len(result.blocks)}. " \
            "If this fails, someone may have added wildcard traversal without governance approval."
    
    # =========================================================================
    # INVARIANT 5: source_pointer resolves relative to parent when repeat_over present
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_source_pointer_relative_resolution_with_repeat_over(self):
        """
        FROZEN INVARIANT: When repeat_over is present, source_pointer resolves
        relative to each parent, NOT from document root.
        
        Governance: RENDER_SHAPES_SEMANTICS.md "Pointer Resolution Rules"
        """
        mock_docdef_service = AsyncMock()
        mock_component_service = AsyncMock()
        
        docdef = MagicMock()
        docdef.document_def_id = "docdef:Test:1.0.0"
        docdef.sections = [{
            "section_id": "relative_test",
            "order": 10,
            "component_id": "component:TestV1:1.0.0",
            "shape": "container",
            "source_pointer": "/items",  # Same path exists at root AND under parents
            "repeat_over": "/parents",
            "context": {"parent_id": "/id"}
        }]
        
        component = MagicMock()
        component.schema_id = "schema:TestV1"
        
        mock_docdef_service.get.return_value = docdef
        mock_component_service.get.return_value = component
        
        builder = RenderModelBuilder(
            docdef_service=mock_docdef_service,
            component_service=mock_component_service,
        )
        
        document_data = {
            "items": [{"root": True}, {"root": True}, {"root": True}],  # 3 at root (should be ignored)
            "parents": [
                {"id": "P1", "items": [{"parent": "P1"}]},              # 1 under P1
                {"id": "P2", "items": [{"parent": "P2"}, {"parent": "P2"}]},  # 2 under P2
            ]
        }
        
        result = await builder.build("docdef:Test:1.0.0", document_data)
        
        # INVARIANT: 2 blocks (from parents), NOT using root items
        assert len(result.blocks) == 2, \
            f"SEMANTIC VIOLATION: Expected 2 blocks (one per parent), got {len(result.blocks)}"
        
        # P1 block has 1 item (not 3 from root)
        assert len(result.blocks[0].data["items"]) == 1
        assert result.blocks[0].data["items"][0].get("parent") == "P1"
        
        # P2 block has 2 items
        assert len(result.blocks[1].data["items"]) == 2


class TestNonFeatureGuards:
    """
    Guard tests to prevent accidental DSL creep.
    
    These tests ensure that non-features remain non-features.
    """
    
    def test_docdef_section_rejects_unknown_fields(self):
        """
        GUARD: Unknown fields in docdef sections should not silently enable new features.
        
        This test documents which fields are valid. If a new field is needed,
        add it explicitly with governance approval.
        """
        valid_section_fields = {
            "section_id",
            "title",
            "description",
            "order",
            "component_id",
            "shape",
            "source_pointer",
            "repeat_over",
            "context",
        }
        
        # Fields that must NOT be added without governance:
        forbidden_fields = {
            "filter",           # DSL creep
            "where",            # DSL creep
            "condition",        # DSL creep
            "expression",       # DSL creep
            "wildcard",         # DSL creep
            "nested_repeat",    # Complexity explosion
            "absolute_pointer", # Ambiguity
        }
        
        # This is a documentation test - it doesn't test code behavior,
        # it documents the contract for reviewers
        assert valid_section_fields.isdisjoint(forbidden_fields), \
            "Contract violation: forbidden field found in valid fields"