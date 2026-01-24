"""
Unit tests for Project model and project routes.

These tests codify current behavior BEFORE refactoring.
If any test fails after refactoring, behavior has changed.

WS-PROJECT-MODEL-001: Behavior preservation tests
"""

import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession


class TestProjectModelStructure:
    """Tests that verify the Project model has all required columns."""
    
    def test_model_has_core_columns(self):
        """Verify Project model has basic columns."""
        from app.api.models.project import Project
        
        # These columns MUST exist
        assert hasattr(Project, 'id')
        assert hasattr(Project, 'project_id')
        assert hasattr(Project, 'name')
        assert hasattr(Project, 'description')
        assert hasattr(Project, 'status')
        assert hasattr(Project, 'created_at')
        assert hasattr(Project, 'updated_at')
        assert hasattr(Project, 'created_by')
        assert hasattr(Project, 'meta')  # maps to 'metadata' column
    
    def test_model_has_ownership_columns(self):
        """Verify Project model has ownership columns.
        
        CRITICAL: These columns exist in database but may be missing from model.
        This test will FAIL if columns are missing - that is the point.
        After WS-PROJECT-MODEL-001, this test should pass.
        """
        from app.api.models.project import Project
        
        # These columns MUST exist for ownership to work
        assert hasattr(Project, 'owner_id'), "owner_id column missing from Project model"
        assert hasattr(Project, 'organization_id'), "organization_id column missing from Project model"
    
    def test_model_has_display_columns(self):
        """Verify Project model has display-related columns.
        
        CRITICAL: icon column exists in database but may be missing from model.
        """
        from app.api.models.project import Project
        
        assert hasattr(Project, 'icon'), "icon column missing from Project model"
    
    def test_model_has_archive_columns(self):
        """Verify Project model has archive-related columns.
        
        CRITICAL: Archive columns exist in database but may be missing from model.
        """
        from app.api.models.project import Project
        
        assert hasattr(Project, 'archived_at'), "archived_at column missing from Project model"
        assert hasattr(Project, 'archived_by'), "archived_by column missing from Project model"
        assert hasattr(Project, 'archived_reason'), "archived_reason column missing from Project model"

class TestProjectOwnershipBehavior:
    """Tests that verify ownership-based filtering works correctly."""
    
    @pytest.mark.asyncio
    async def test_get_project_filters_by_owner(self):
        """Verify _get_project_with_icon filters by owner_id via ORM."""
        from app.web.routes.public.project_routes import _get_project_with_icon
        from app.api.models.project import Project
        
        # Arrange
        db = AsyncMock(spec=AsyncSession)
        project_id = "TEST-001"
        
        # Create a mock user - configure id field (the first one _get_user_id tries)
        user_uuid = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_uuid  # _get_user_id tries 'id' first
        
        # Create mock Project ORM object
        mock_project = MagicMock(spec=Project)
        mock_project.id = uuid4()
        mock_project.name = "Test Project"
        mock_project.project_id = project_id
        mock_project.description = "Test"
        mock_project.icon = "folder"
        mock_project.created_at = datetime.now(timezone.utc)
        mock_project.updated_at = datetime.now(timezone.utc)
        mock_project.owner_id = user_uuid
        mock_project.archived_at = None
        mock_project.archived_by = None
        mock_project.archived_reason = None
        
        # ORM uses scalar_one_or_none
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        db.execute.return_value = mock_result
        
        # Act
        result = await _get_project_with_icon(db, project_id, mock_user)
        
        # Assert
        assert result is not None
        assert result['project_id'] == project_id
        assert result['owner_id'] == str(user_uuid)
    
    @pytest.mark.asyncio
    async def test_get_project_returns_none_for_non_owner(self):
        """Verify _get_project_with_icon returns None if user does not own project."""
        from app.web.routes.public.project_routes import _get_project_with_icon
        
        # Arrange
        db = AsyncMock(spec=AsyncSession)
        project_id = "TEST-001"
        
        user_uuid = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_uuid
        
        # ORM returns None when no match
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result
        
        # Act
        result = await _get_project_with_icon(db, project_id, mock_user)
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_project_returns_archive_state(self):
        """Verify _get_project_with_icon includes archive information via ORM."""
        from app.web.routes.public.project_routes import _get_project_with_icon
        from app.api.models.project import Project
        
        # Arrange
        db = AsyncMock(spec=AsyncSession)
        project_id = "TEST-001"
        
        user_uuid = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_uuid
        
        # Create mock archived Project ORM object
        mock_project = MagicMock(spec=Project)
        mock_project.id = uuid4()
        mock_project.name = "Archived Project"
        mock_project.project_id = project_id
        mock_project.description = "Test"
        mock_project.icon = "archive"
        mock_project.created_at = datetime.now(timezone.utc)
        mock_project.updated_at = datetime.now(timezone.utc)
        mock_project.owner_id = user_uuid
        mock_project.archived_at = datetime.now(timezone.utc)
        mock_project.archived_by = user_uuid
        mock_project.archived_reason = "No longer needed"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        db.execute.return_value = mock_result
        
        # Act
        result = await _get_project_with_icon(db, project_id, mock_user)
        
        # Assert
        assert result is not None
        assert result['archived_at'] is not None
        assert result['is_archived'] == True
        assert result['archived_reason'] == "No longer needed"

class TestProjectCreationBehavior:
    """Tests that verify project creation sets all required fields."""
    
    def test_generate_project_id_prefix(self):
        """Verify project_id prefix is generated correctly from name."""
        from app.web.routes.public.intake_workflow_routes import _generate_project_id_prefix
        
        # Test prefix generation
        assert _generate_project_id_prefix("Legacy Inventory Replacement") == "LIR"
        assert _generate_project_id_prefix("Mobile App") == "MA"
        assert _generate_project_id_prefix("Customer Portal Redesign") == "CPR"
        assert _generate_project_id_prefix("AI") == "AX"  # Single word pads to 2 chars
        assert _generate_project_id_prefix("Single") == "SX"  # Single word pads to 2 chars
    
    @pytest.mark.asyncio
    async def test_generate_unique_project_id_first(self):
        """Verify first project gets -001 suffix."""
        from app.web.routes.public.intake_workflow_routes import _generate_unique_project_id
        
        db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []  # No existing projects
        mock_result.scalars.return_value = mock_scalars
        db.execute.return_value = mock_result
        
        project_id = await _generate_unique_project_id(db, "Test Project")
        assert project_id == "TP-001"
    
    @pytest.mark.asyncio
    async def test_generate_unique_project_id_increments(self):
        """Verify project_id sequence increments correctly."""
        from app.web.routes.public.intake_workflow_routes import _generate_unique_project_id
        
        db = AsyncMock(spec=AsyncSession)
        
        # Mock: 2 existing projects with TP prefix
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = ["TP-002", "TP-001"]  # Existing projects
        mock_result.scalars.return_value = mock_scalars
        db.execute.return_value = mock_result
        
        project_id = await _generate_unique_project_id(db, "Test Project")
        assert project_id == "TP-003"  # Next in sequence
    
    @pytest.mark.asyncio
    async def test_create_project_from_intake_sets_ownership(self):
        """Verify _create_project_from_intake sets owner_id via ORM."""
        from app.web.routes.public.intake_workflow_routes import _create_project_from_intake
        from app.api.models.project import Project
        
        # Arrange
        db = AsyncMock(spec=AsyncSession)
        user_id = str(uuid4())
        user_uuid = UUID(user_id)
        
        # Mock workflow state with intake document
        mock_state = MagicMock()
        mock_state.execution_id = "exec-123"
        mock_state.context_state = {
            "document_concierge_intake_document": {
                "project_name": "Test Project",
                "summary": {"description": "A test project"}
            }
        }
        
        # Mock the unique ID generation query (uses scalars().all())
        mock_id_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []  # No existing projects with prefix
        mock_id_result.scalars.return_value = mock_scalars
        db.execute.return_value = mock_id_result
        
        # Capture all objects passed to db.add()
        added_objects = []
        def capture_add(obj):
            added_objects.append(obj)
        db.add.side_effect = capture_add
        
        # Mock refresh to update project_id
        async def mock_refresh(obj):
            obj.project_id = "TP-001"
        db.refresh = mock_refresh
        
        # Act
        result = await _create_project_from_intake(db, mock_state, user_id)
        
        # Assert
        assert result is not None
        assert result.project_id == "TP-001"
        
        # Verify db.add was called with Project and Document
        assert db.add.call_count == 2  # Project + Document
        assert len(added_objects) == 2
        # First object should be Project
        added_project = added_objects[0]
        assert isinstance(added_project, Project)
        
        # Verify ownership fields are set correctly
        assert added_project.owner_id == user_uuid, "owner_id must be set to user UUID"
        assert added_project.organization_id == user_uuid, "organization_id must be set to user UUID"
        assert added_project.created_by == user_id, "created_by must be set to user_id string"

class TestArchiveBehavior:
    """Tests for archive/unarchive functionality."""
    
    @pytest.mark.asyncio
    async def test_archive_dependency_allows_active_project(self):
        """Verify active projects pass the archive check via ORM."""
        from app.core.dependencies.archive import verify_project_not_archived
        
        db = AsyncMock(spec=AsyncSession)
        project_id = "TEST-001"
        
        # ORM returns tuple from .first() when selecting single column
        mock_result = MagicMock()
        mock_result.first.return_value = (None,)  # (archived_at,) - not archived
        db.execute.return_value = mock_result
        
        # Should not raise
        await verify_project_not_archived(project_id, db)
        
        # Verify query was executed
        db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_archive_dependency_blocks_archived_project(self):
        """Verify archived projects are blocked."""
        from app.core.dependencies.archive import verify_project_not_archived
        from fastapi import HTTPException
        
        db = AsyncMock(spec=AsyncSession)
        project_id = "TEST-001"
        
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.archived_at = datetime.now(timezone.utc)  # Archived!
        mock_result.fetchone.return_value = mock_row
        db.execute.return_value = mock_result
        
        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await verify_project_not_archived(project_id, db)
        
        assert exc_info.value.status_code == 403
        assert "archived" in exc_info.value.detail.lower()


class TestProjectIdFormat:
    """Tests for project_id format validation."""
    
    def test_hyphenated_format_regex(self):
        """Verify hyphenated project_id format is correct."""
        import re
        
        # Pattern for new format: 2-5 uppercase letters, hyphen, 3 digits
        pattern = r'^[A-Z]{2,5}-[0-9]{3}$'
        
        # Valid formats
        assert re.match(pattern, "LIR-001")
        assert re.match(pattern, "MA-002")
        assert re.match(pattern, "CPR-999")
        assert re.match(pattern, "AI-001")
        assert re.match(pattern, "ABCDE-123")
        
        # Invalid formats
        assert not re.match(pattern, "A-001")  # Too short prefix
        assert not re.match(pattern, "ABCDEF-001")  # Too long prefix
        assert not re.match(pattern, "LIR001")  # Missing hyphen
        assert not re.match(pattern, "LIR-01")  # Too few digits
        assert not re.match(pattern, "LIR-0001")  # Too many digits
        assert not re.match(pattern, "lir-001")  # Lowercase