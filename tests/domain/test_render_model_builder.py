"""
Tests for RenderModelBuilder.

Per WS-ADR-034-POC Phase 8.3: Tests for render model builder service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.domain.services.render_model_builder import (
    RenderModelBuilder,
    RenderBlock,
    RenderModel,
    DocDefNotFoundError,
    ComponentNotFoundError,
)


class TestRenderModelBuilder:
    """Tests for RenderModelBuilder."""
    
    @pytest.fixture
    def mock_docdef_service(self):
        """Create mock DocumentDefinitionService."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_component_service(self):
        """Create mock ComponentRegistryService."""
        return AsyncMock()
    
    @pytest.fixture
    def builder(self, mock_docdef_service, mock_component_service):
        """Create RenderModelBuilder with mock services."""
        return RenderModelBuilder(
            docdef_service=mock_docdef_service,
            component_service=mock_component_service,
        )
    
    @pytest.fixture
    def sample_component(self):
        """Create sample component."""
        comp = MagicMock()
        comp.component_id = "component:TestV1:1.0.0"
        comp.schema_id = "schema:TestV1"
        return comp
    
    @pytest.mark.asyncio
    async def test_build_single_shape(self, builder, mock_docdef_service, mock_component_service, sample_component):
        """Test building RenderModel with single shape."""
        docdef = MagicMock()
        docdef.document_def_id = "docdef:Test:1.0.0"
        docdef.sections = [{
            "section_id": "single_sec",
            "order": 10,
            "component_id": "component:TestV1:1.0.0",
            "shape": "single",
            "source_pointer": "/data",
        }]
        
        mock_docdef_service.get.return_value = docdef
        mock_component_service.get.return_value = sample_component
        
        document_data = {"data": {"id": "1", "value": "test"}}
        
        result = await builder.build("docdef:Test:1.0.0", document_data)
        
        assert len(result.blocks) == 1
        assert result.blocks[0].type == "schema:TestV1"
        assert result.blocks[0].data == {"id": "1", "value": "test"}
    
    @pytest.mark.asyncio
    async def test_build_list_shape(self, builder, mock_docdef_service, mock_component_service, sample_component):
        """Test building RenderModel with list shape."""
        docdef = MagicMock()
        docdef.document_def_id = "docdef:Test:1.0.0"
        docdef.sections = [{
            "section_id": "list_sec",
            "order": 10,
            "component_id": "component:TestV1:1.0.0",
            "shape": "list",
            "source_pointer": "/items",
        }]
        
        mock_docdef_service.get.return_value = docdef
        mock_component_service.get.return_value = sample_component
        
        document_data = {
            "items": [
                {"id": "1", "text": "Item 1"},
                {"id": "2", "text": "Item 2"},
                {"id": "3", "text": "Item 3"},
            ]
        }
        
        result = await builder.build("docdef:Test:1.0.0", document_data)
        
        assert len(result.blocks) == 3
        assert result.blocks[0].key == "list_sec:0"
        assert result.blocks[1].key == "list_sec:1"
        assert result.blocks[2].key == "list_sec:2"
    
    @pytest.mark.asyncio
    async def test_build_nested_list_shape(self, builder, mock_docdef_service, mock_component_service, sample_component):
        """Test building RenderModel with nested_list shape."""
        docdef = MagicMock()
        docdef.document_def_id = "docdef:Test:1.0.0"
        docdef.sections = [{
            "section_id": "nested_sec",
            "order": 10,
            "component_id": "component:TestV1:1.0.0",
            "shape": "nested_list",
            "source_pointer": "/questions",
            "repeat_over": "/epics",
            "context": {"epic_id": "/id", "epic_title": "/title"},
        }]
        
        mock_docdef_service.get.return_value = docdef
        mock_component_service.get.return_value = sample_component
        
        document_data = {
            "epics": [
                {"id": "E1", "title": "Epic 1", "questions": [{"q": "Q1"}, {"q": "Q2"}]},
                {"id": "E2", "title": "Epic 2", "questions": [{"q": "Q3"}]},
            ]
        }
        
        result = await builder.build("docdef:Test:1.0.0", document_data)
        
        # Should have 3 blocks total (2 from E1, 1 from E2)
        assert len(result.blocks) == 3
    
    @pytest.mark.asyncio
    async def test_build_nested_list_resolves_pointer_relative_to_parent(self, builder, mock_docdef_service, mock_component_service, sample_component):
        """Test that nested_list resolves source_pointer relative to parent."""
        docdef = MagicMock()
        docdef.document_def_id = "docdef:Test:1.0.0"
        docdef.sections = [{
            "section_id": "nested_sec",
            "order": 10,
            "component_id": "component:TestV1:1.0.0",
            "shape": "nested_list",
            "source_pointer": "/items",  # Relative to each parent
            "repeat_over": "/parents",
        }]
        
        mock_docdef_service.get.return_value = docdef
        mock_component_service.get.return_value = sample_component
        
        document_data = {
            "parents": [
                {"id": "P1", "items": [{"data": "item1"}, {"data": "item2"}]},
                {"id": "P2", "items": [{"data": "item3"}]},
            ]
        }
        
        result = await builder.build("docdef:Test:1.0.0", document_data)
        
        # Verify data comes from relative resolution
        assert result.blocks[0].data == {"data": "item1"}
        assert result.blocks[1].data == {"data": "item2"}
        assert result.blocks[2].data == {"data": "item3"}
    
    @pytest.mark.asyncio
    async def test_build_propagates_context_from_parent(self, builder, mock_docdef_service, mock_component_service, sample_component):
        """Test that context is propagated from parent to blocks."""
        docdef = MagicMock()
        docdef.document_def_id = "docdef:Test:1.0.0"
        docdef.sections = [{
            "section_id": "nested_sec",
            "order": 10,
            "component_id": "component:TestV1:1.0.0",
            "shape": "nested_list",
            "source_pointer": "/children",
            "repeat_over": "/parents",
            "context": {"parent_id": "/id", "parent_name": "/name"},
        }]
        
        mock_docdef_service.get.return_value = docdef
        mock_component_service.get.return_value = sample_component
        
        document_data = {
            "parents": [
                {"id": "P1", "name": "Parent 1", "children": [{"c": "child1"}]},
            ]
        }
        
        result = await builder.build("docdef:Test:1.0.0", document_data)
        
        assert result.blocks[0].context == {"parent_id": "P1", "parent_name": "Parent 1"}
    
    @pytest.mark.asyncio
    async def test_build_block_type_equals_schema_id(self, builder, mock_docdef_service, mock_component_service, sample_component):
        """Test that RenderBlock.type equals component's schema_id (no prefixing)."""
        docdef = MagicMock()
        docdef.document_def_id = "docdef:Test:1.0.0"
        docdef.sections = [{
            "section_id": "sec",
            "order": 10,
            "component_id": "component:TestV1:1.0.0",
            "shape": "single",
            "source_pointer": "/data",
        }]
        
        mock_docdef_service.get.return_value = docdef
        mock_component_service.get.return_value = sample_component
        
        result = await builder.build("docdef:Test:1.0.0", {"data": {"value": "test"}})
        
        # Type should be exactly schema_id, no double-prefixing
        assert result.blocks[0].type == "schema:TestV1"
        assert result.blocks[0].type.count("schema:") == 1
    
    @pytest.mark.asyncio
    async def test_build_empty_data_produces_no_blocks(self, builder, mock_docdef_service, mock_component_service, sample_component):
        """Test that empty/missing data produces no blocks."""
        docdef = MagicMock()
        docdef.document_def_id = "docdef:Test:1.0.0"
        docdef.sections = [{
            "section_id": "sec",
            "order": 10,
            "component_id": "component:TestV1:1.0.0",
            "shape": "list",
            "source_pointer": "/items",
        }]
        
        mock_docdef_service.get.return_value = docdef
        mock_component_service.get.return_value = sample_component
        
        # Empty items array
        result = await builder.build("docdef:Test:1.0.0", {"items": []})
        assert len(result.blocks) == 0
        
        # Missing items key
        result = await builder.build("docdef:Test:1.0.0", {})
        assert len(result.blocks) == 0
    
    @pytest.mark.asyncio
    async def test_build_returns_data_only(self, builder, mock_docdef_service, mock_component_service, sample_component):
        """Test that build returns data-only RenderModel (no HTML)."""
        docdef = MagicMock()
        docdef.document_def_id = "docdef:Test:1.0.0"
        docdef.sections = [{
            "section_id": "sec",
            "order": 10,
            "component_id": "component:TestV1:1.0.0",
            "shape": "single",
            "source_pointer": "/data",
        }]
        
        mock_docdef_service.get.return_value = docdef
        mock_component_service.get.return_value = sample_component
        
        result = await builder.build("docdef:Test:1.0.0", {"data": {"value": "test"}})
        
        # Result should be RenderModel dataclass, not contain any HTML
        assert isinstance(result, RenderModel)
        assert isinstance(result.blocks[0], RenderBlock)
        assert isinstance(result.blocks[0].data, dict)
        # No HTML strings in data
        assert "<" not in str(result.blocks[0].data)
