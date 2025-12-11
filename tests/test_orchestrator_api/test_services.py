"""
Tests for service layer business logic.

Tests ArtifactService and RolePromptService.
"""
import pytest
from unittest.mock import Mock, patch
from app.combine.services.artifact_service import ArtifactService, ArtifactValidationError
from app.combine.services.role_prompt_service import RolePromptService
from database import SessionLocal


class TestArtifactService:
    """Test ArtifactService business logic."""
    
    def test_create_artifact_success(self):
        """Test successful artifact creation."""
        session = SessionLocal()
        try:
            service = ArtifactService(session)
            
            artifact = service.create_artifact(
                artifact_path="TEST/SVC/001",
                artifact_type="epic",
                title="Service Test Epic",
                content={"description": "Test"},
                status="draft"
            )
            
            assert artifact is not None
            assert artifact.artifact_path == "TEST/SVC/001"
            assert artifact.title == "Service Test Epic"
            assert artifact.project_id == "TEST"
            assert artifact.epic_id == "SVC"
            
            # Cleanup
            session.delete(artifact)
            session.commit()
        finally:
            session.close()
    
    def test_create_artifact_invalid_path(self):
        """Test artifact creation with invalid path."""
        session = SessionLocal()
        try:
            service = ArtifactService(session)
            
            with pytest.raises(ArtifactValidationError):
                service.create_artifact(
                    artifact_path="",  # Invalid empty path
                    artifact_type="epic",
                    title="Test",
                    content={}
                )
        finally:
            session.close()
    
    def test_get_artifact_by_path(self):
        """Test retrieving artifact by path."""
        session = SessionLocal()
        try:
            service = ArtifactService(session)
            
            # Create artifact
            created = service.create_artifact(
                artifact_path="TEST/GET/001",
                artifact_type="epic",
                title="Get Test",
                content={}
            )
            
            # Retrieve it
            retrieved = service.get_artifact("TEST/GET/001")
            
            assert retrieved is not None
            assert retrieved.id == created.id
            assert retrieved.title == "Get Test"
            
            # Cleanup
            session.delete(created)
            session.commit()
        finally:
            session.close()
    
    def test_update_artifact(self):
        """Test updating an artifact."""
        session = SessionLocal()
        try:
            service = ArtifactService(session)
            
            # Create artifact
            artifact = service.create_artifact(
                artifact_path="TEST/UPDATE/001",
                artifact_type="epic",
                title="Original Title",
                content={"version": 1},
                status="draft"
            )
            
            # Update it
            updated = service.update_artifact(
                artifact_path="TEST/UPDATE/001",
                title="Updated Title",
                content={"version": 2},
                status="active"
            )
            
            assert updated is not None
            assert updated.title == "Updated Title"
            assert updated.content["version"] == 2
            assert updated.status == "active"
            assert updated.version == 2  # Version should increment
            
            # Cleanup
            session.delete(updated)
            session.commit()
        finally:
            session.close()
    
    def test_list_artifacts(self):
        """Test listing artifacts filtered by type."""
        session = SessionLocal()
        try:
            service = ArtifactService(session)
            
            # Create multiple artifacts
            service.create_artifact("TEST/LIST/E001", "epic", "Epic 1", {})
            service.create_artifact("TEST/LIST/E001/F001", "feature", "Feature 1", {})
            service.create_artifact("TEST/LIST/E002", "epic", "Epic 2", {})
            
            # List epics only
            epics = service.list_artifacts(
                project_id="TEST",
                artifact_type="epic"
            )
            
            # Should have at least 2 epics we just created
            test_epics = [a for a in epics if a.epic_id == "LIST"]
            assert len(test_epics) >= 2
            assert all(a.artifact_type == "epic" for a in test_epics)
            
            # Cleanup
            session.execute("DELETE FROM artifacts WHERE project_id = 'TEST' AND epic_id = 'LIST'")
            session.commit()
        finally:
            session.close()
    
    def test_validate_path(self):
        """Test RSP-1 path validation."""
        session = SessionLocal()
        try:
            service = ArtifactService(session)
            
            # Valid paths
            assert service.validate_path("HMP") is True
            assert service.validate_path("HMP/E001") is True
            assert service.validate_path("HMP/E001/F003") is True
            assert service.validate_path("HMP/E001/F003/S007") is True
            
            # Invalid paths
            assert service.validate_path("") is False
            assert service.validate_path("hmp") is False  # Lowercase
            assert service.validate_path("H") is False  # Too short
            assert service.validate_path("HMP/") is False  # Trailing slash
        finally:
            session.close()


class TestRolePromptService:
    """Test RolePromptService business logic."""
    
    @patch('app.orchestrator_api.services.role_prompt_service.RolePromptRepository')
    def test_build_prompt_basic(self, mock_repo_class):
        """Test building a basic prompt."""
        # Mock prompt data
        mock_prompt = Mock()
        mock_prompt.id = "pm-v1"
        mock_prompt.instructions = "You are a PM. Create an epic."
        mock_prompt.expected_schema = {"type": "object"}
        mock_prompt.created_at = Mock()
        mock_prompt.created_at.tzinfo = Mock()  # Timezone-aware
        
        mock_repo = Mock()
        mock_repo.get_active_prompt.return_value = mock_prompt
        mock_repo_class.return_value = mock_repo
        
        service = RolePromptService()
        prompt_text, prompt_id = service.build_prompt(
            role_name="pm",
            pipeline_id="TEST-001",
            phase="pm_phase"
        )
        
        assert "You are a PM" in prompt_text
        assert "Expected Output Schema" in prompt_text
        assert prompt_id == "pm-v1"
    
    @patch('app.orchestrator_api.services.role_prompt_service.RolePromptRepository')
    def test_build_prompt_with_context(self, mock_repo_class):
        """Test building prompt with additional context."""
        mock_prompt = Mock()
        mock_prompt.id = "architect-v1"
        mock_prompt.instructions = "Design the architecture."
        mock_prompt.expected_schema = None
        mock_prompt.created_at = Mock()
        mock_prompt.created_at.tzinfo = Mock()
        
        mock_repo = Mock()
        mock_repo.get_active_prompt.return_value = mock_prompt
        mock_repo_class.return_value = mock_repo
        
        service = RolePromptService()
        prompt_text, prompt_id = service.build_prompt(
            role_name="architect",
            pipeline_id="TEST-002",
            phase="arch_phase",
            epic_context="Build healthcare platform",
            pipeline_state={"status": "active"}
        )
        
        assert "Design the architecture" in prompt_text
        assert "Build healthcare platform" in prompt_text
        assert "Context State" in prompt_text
        assert "active" in prompt_text
    
    @patch('app.orchestrator_api.services.role_prompt_service.RolePromptRepository')
    def test_build_prompt_no_active_prompt(self, mock_repo_class):
        """Test error when no active prompt found."""
        mock_repo = Mock()
        mock_repo.get_active_prompt.return_value = None
        mock_repo_class.return_value = mock_repo
        
        service = RolePromptService()
        
        with pytest.raises(ValueError, match="No active prompt found"):
            service.build_prompt(
                role_name="nonexistent",
                pipeline_id="TEST-003",
                phase="test_phase"
            )