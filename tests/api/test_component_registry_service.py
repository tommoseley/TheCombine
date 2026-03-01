"""
Tests for ComponentRegistryService.

Per WS-ADR-034-POC Phase 8.1: Service unit tests for component registry.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.api.services.component_registry_service import (
    ComponentRegistryService,
    InvalidComponentIdError,
    COMPONENT_ID_PATTERN,
)
from app.api.models.component_artifact import ComponentArtifact


class TestComponentIdValidation:
    """Tests for component_id format validation."""
    
    def test_valid_component_id_patterns(self):
        """Valid component IDs should match the pattern."""
        valid_ids = [
            "component:OpenQuestionV1:1.0.0",
            "component:RiskV2:2.1.3",
            "component:My_Component:0.0.1",
            "component:Test-Component:10.20.30",
            "component:some.thing:1.0.0",
        ]
        for comp_id in valid_ids:
            assert COMPONENT_ID_PATTERN.match(comp_id), f"Should match: {comp_id}"
    
    def test_invalid_component_id_patterns(self):
        """Invalid component IDs should not match the pattern."""
        invalid_ids = [
            "OpenQuestionV1:1.0.0",  # missing prefix
            "component:OpenQuestionV1",  # missing version
            "component::1.0.0",  # empty name
            "component:OpenQuestionV1:1.0",  # incomplete version
            "component:OpenQuestionV1:v1.0.0",  # 'v' in version
            "component:Open Question:1.0.0",  # space in name
        ]
        for comp_id in invalid_ids:
            assert not COMPONENT_ID_PATTERN.match(comp_id), f"Should not match: {comp_id}"


class TestComponentRegistryService:
    """Tests for ComponentRegistryService methods."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock()
        # db.add() is not async - make it a regular mock
        db.add = MagicMock()
        return db
    
    @pytest.fixture
    def service(self, mock_db):
        """Create service instance with mock db."""
        return ComponentRegistryService(mock_db)
    
    @pytest.mark.asyncio
    async def test_create_component_artifact(self, service, mock_db):
        """Test creating a new component artifact."""
        schema_artifact_id = uuid4()
        
        # Mock schema lookup
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(id=schema_artifact_id)
        mock_db.execute.return_value = mock_result
        
        # Create component
        await service.create(
            component_id="component:TestV1:1.0.0",
            schema_artifact_id=schema_artifact_id,
            schema_id="schema:TestV1",
            generation_guidance={"bullets": ["Test bullet"]},
            view_bindings={"web": {"fragment_id": "fragment:TestV1:web:1.0.0"}},
            created_by="test",
        )
        
        # Verify db.add was called
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_component_by_exact_id(self, service, mock_db):
        """Test getting a component by exact ID."""
        expected_component = ComponentArtifact(
            id=uuid4(),
            component_id="component:OpenQuestionV1:1.0.0",
            schema_id="schema:OpenQuestionV1",
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_component
        mock_db.execute.return_value = mock_result
        
        result = await service.get("component:OpenQuestionV1:1.0.0")
        
        assert result == expected_component
    
    @pytest.mark.asyncio
    async def test_get_accepted_returns_latest_by_accepted_at(self, service, mock_db):
        """Test that get_accepted orders by accepted_at DESC."""
        expected_component = ComponentArtifact(
            id=uuid4(),
            component_id="component:OpenQuestionV1:1.0.0",
            status="accepted",
            accepted_at=datetime.now(timezone.utc),
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_component
        mock_db.execute.return_value = mock_result
        
        result = await service.get_accepted("component:OpenQuestionV1:")
        
        assert result == expected_component
        assert result.status == "accepted"
    
    @pytest.mark.asyncio
    async def test_list_by_schema(self, service, mock_db):
        """Test listing components by schema_id."""
        components = [
            ComponentArtifact(component_id="component:TestV1:1.0.0", schema_id="schema:TestV1"),
            ComponentArtifact(component_id="component:TestV1:1.1.0", schema_id="schema:TestV1"),
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = components
        mock_db.execute.return_value = mock_result
        
        result = await service.list_by_schema("schema:TestV1")
        
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_accept_transitions_status(self, service, mock_db):
        """Test that accept() transitions status from draft to accepted."""
        component = ComponentArtifact(
            id=uuid4(),
            component_id="component:TestV1:1.0.0",
            status="draft",
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = component
        mock_db.execute.return_value = mock_result
        
        result = await service.accept("component:TestV1:1.0.0")
        
        assert result.status == "accepted"
        assert result.accepted_at is not None
    
    @pytest.mark.asyncio
    async def test_accept_sets_accepted_at(self, service, mock_db):
        """Test that accept() sets the accepted_at timestamp."""
        component = ComponentArtifact(
            id=uuid4(),
            component_id="component:TestV1:1.0.0",
            status="draft",
            accepted_at=None,
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = component
        mock_db.execute.return_value = mock_result
        
        before = datetime.now(timezone.utc)
        result = await service.accept("component:TestV1:1.0.0")
        after = datetime.now(timezone.utc)
        
        assert result.accepted_at is not None
        assert before <= result.accepted_at <= after
    
    @pytest.mark.asyncio
    async def test_component_id_format_validation(self, service, mock_db):
        """Test that create() validates component_id format."""
        with pytest.raises(InvalidComponentIdError):
            await service.create(
                component_id="invalid-format",
                schema_artifact_id=uuid4(),
                schema_id="schema:TestV1",
                generation_guidance={"bullets": ["Test"]},
                view_bindings={},
            )

