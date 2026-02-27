"""
Tests for PromptAssembler.

Per WS-ADR-034-POC Phase 8.2: Tests for prompt assembly service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.domain.services.prompt_assembler import (
    PromptAssembler,
    AssembledPrompt,
)


class TestPromptAssembler:
    """Tests for PromptAssembler."""
    
    @pytest.fixture
    def mock_docdef_service(self):
        """Create mock DocumentDefinitionService."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_component_service(self):
        """Create mock ComponentRegistryService."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_schema_service(self):
        """Create mock SchemaRegistryService that returns None (no schema lookup)."""
        service = AsyncMock()
        service.get_by_id.return_value = None  # No schema found - skips schema bundle population
        return service
    
    @pytest.fixture
    def assembler(self, mock_docdef_service, mock_component_service, mock_schema_service):
        """Create PromptAssembler with mock services."""
        return PromptAssembler(
            docdef_service=mock_docdef_service,
            component_service=mock_component_service,
            schema_service=mock_schema_service,
        )
    
    @pytest.fixture
    def sample_docdef(self):
        """Create sample document definition."""
        docdef = MagicMock()
        docdef.document_def_id = "docdef:TestDoc:1.0.0"
        docdef.prompt_header = {
            "role": "You are a test assistant.",
            "constraints": ["Be concise.", "Be accurate."],
        }
        docdef.sections = [
            {"section_id": "sec1", "order": 10, "component_id": "component:CompA:1.0.0"},
            {"section_id": "sec2", "order": 20, "component_id": "component:CompB:1.0.0"},
        ]
        return docdef
    
    @pytest.fixture
    def sample_components(self):
        """Create sample components."""
        comp_a = MagicMock()
        comp_a.component_id = "component:CompA:1.0.0"
        comp_a.schema_id = "schema:CompA"
        comp_a.generation_guidance = {"bullets": ["Bullet A1", "Bullet A2"]}
        
        comp_b = MagicMock()
        comp_b.component_id = "component:CompB:1.0.0"
        comp_b.schema_id = "schema:CompB"
        comp_b.generation_guidance = {"bullets": ["Bullet B1"]}
        
        return {"component:CompA:1.0.0": comp_a, "component:CompB:1.0.0": comp_b}
    
    @pytest.mark.asyncio
    async def test_assemble_loads_docdef(self, assembler, mock_docdef_service, mock_component_service, sample_docdef, sample_components):
        """Test that assemble() loads the document definition."""
        mock_docdef_service.get.return_value = sample_docdef
        mock_component_service.get.side_effect = lambda cid: sample_components.get(cid)
        
        result = await assembler.assemble("docdef:TestDoc:1.0.0")
        
        mock_docdef_service.get.assert_called_once_with("docdef:TestDoc:1.0.0")
    
    @pytest.mark.asyncio
    async def test_assemble_resolves_components(self, assembler, mock_docdef_service, mock_component_service, sample_docdef, sample_components):
        """Test that assemble() resolves all referenced components."""
        mock_docdef_service.get.return_value = sample_docdef
        mock_component_service.get.side_effect = lambda cid: sample_components.get(cid)
        
        result = await assembler.assemble("docdef:TestDoc:1.0.0")
        
        assert mock_component_service.get.call_count == 2
    
    @pytest.mark.asyncio
    async def test_assemble_preserves_section_order(self, assembler, mock_docdef_service, mock_component_service, sample_docdef, sample_components):
        """Test that bullets are ordered by section order."""
        mock_docdef_service.get.return_value = sample_docdef
        mock_component_service.get.side_effect = lambda cid: sample_components.get(cid)
        
        result = await assembler.assemble("docdef:TestDoc:1.0.0")
        
        # CompA bullets should come before CompB bullets (order 10 < 20)
        assert result.component_bullets[0] == "Bullet A1"
        assert result.component_bullets[1] == "Bullet A2"
        assert result.component_bullets[2] == "Bullet B1"
    
    @pytest.mark.asyncio
    async def test_assemble_preserves_bullet_order(self, assembler, mock_docdef_service, mock_component_service, sample_docdef, sample_components):
        """Test that bullet order within component is preserved."""
        mock_docdef_service.get.return_value = sample_docdef
        mock_component_service.get.side_effect = lambda cid: sample_components.get(cid)
        
        result = await assembler.assemble("docdef:TestDoc:1.0.0")
        
        # A1 should come before A2
        a1_idx = result.component_bullets.index("Bullet A1")
        a2_idx = result.component_bullets.index("Bullet A2")
        assert a1_idx < a2_idx
    
    @pytest.mark.asyncio
    async def test_assemble_dedupes_exact_duplicates_keeps_first(self, assembler, mock_docdef_service, mock_component_service):
        """Test that exact duplicate bullets are removed, keeping first occurrence."""
        docdef = MagicMock()
        docdef.document_def_id = "docdef:TestDoc:1.0.0"
        docdef.prompt_header = {"role": "Test", "constraints": []}
        docdef.sections = [
            {"section_id": "sec1", "order": 10, "component_id": "component:CompA:1.0.0"},
            {"section_id": "sec2", "order": 20, "component_id": "component:CompB:1.0.0"},
        ]
        
        comp_a = MagicMock()
        comp_a.schema_id = "schema:CompA"
        comp_a.generation_guidance = {"bullets": ["Shared bullet", "Bullet A"]}
        
        comp_b = MagicMock()
        comp_b.schema_id = "schema:CompB"
        comp_b.generation_guidance = {"bullets": ["Shared bullet", "Bullet B"]}  # Duplicate!
        
        mock_docdef_service.get.return_value = docdef
        mock_component_service.get.side_effect = lambda cid: comp_a if "CompA" in cid else comp_b
        
        result = await assembler.assemble("docdef:TestDoc:1.0.0")
        
        # Should have 3 bullets (shared deduped)
        assert len(result.component_bullets) == 3
        assert result.component_bullets.count("Shared bullet") == 1
        # First occurrence wins - shared bullet at position 0
        assert result.component_bullets[0] == "Shared bullet"
    
    @pytest.mark.asyncio
    async def test_assemble_includes_schema_bundle_from_components(self, assembler, mock_docdef_service, mock_component_service, sample_docdef, sample_components):
        """Test that schema bundle is included (from component schemas)."""
        mock_docdef_service.get.return_value = sample_docdef
        mock_component_service.get.side_effect = lambda cid: sample_components.get(cid)
        
        result = await assembler.assemble("docdef:TestDoc:1.0.0")
        
        assert result.schema_bundle is not None
        assert "component_schemas" in result.schema_bundle
        assert "schema:CompA" in result.schema_bundle["component_schemas"]
        assert "schema:CompB" in result.schema_bundle["component_schemas"]
    
    def test_format_prompt_text(self, assembler):
        """Test formatting assembled prompt as text."""
        assembled = AssembledPrompt(
            document_def_id="docdef:Test:1.0.0",
            header={"role": "Test role", "constraints": ["Constraint 1"]},
            component_bullets=["Bullet 1", "Bullet 2"],
            component_ids=["component:Test:1.0.0"],
            schema_bundle={"schemas": {}},
            bundle_sha256="sha256:abc123",
        )
        
        text = assembler.format_prompt_text(assembled)
        
        assert "Test role" in text
        assert "Constraint 1" in text
        assert "Bullet 1" in text
        assert "Bullet 2" in text
        assert "sha256:abc123" in text
