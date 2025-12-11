"""
Test ArtifactRepository with PostgreSQL database.
"""
import pytest
import uuid
from datetime import datetime, timezone

from app.combine.models import Artifact
from database import SessionLocal


@pytest.fixture
def clean_artifacts():
    """Clean up artifacts table before and after tests."""
    session = SessionLocal()
    try:
        # Clean before test
        session.execute("DELETE FROM artifacts WHERE project_id = 'TEST'")
        session.commit()
        yield session
        # Clean after test
        session.execute("DELETE FROM artifacts WHERE project_id = 'TEST'")
        session.commit()
    finally:
        session.close()


class TestArtifactRepository:
    """Test Artifact model and repository operations."""
    
    def test_create_artifact(self, clean_artifacts):
        """Test creating a new artifact."""
        session = clean_artifacts
        
        artifact = Artifact(
            id=uuid.uuid4(),
            artifact_path="TEST/E001",
            artifact_type="epic",
            project_id="TEST",
            epic_id="E001",
            title="Test Epic",
            content={"description": "Test epic content"},
            breadcrumbs={},
            status="draft",
            version=1
        )
        
        session.add(artifact)
        session.commit()
        session.refresh(artifact)
        
        assert artifact.id is not None
        assert artifact.artifact_path == "TEST/E001"
        assert artifact.created_at is not None
        assert artifact.created_at.tzinfo is not None  # Timezone-aware
    
    def test_query_by_path(self, clean_artifacts):
        """Test querying artifact by path."""
        session = clean_artifacts
        
        # Create artifact
        artifact = Artifact(
            id=uuid.uuid4(),
            artifact_path="TEST/E002",
            artifact_type="epic",
            project_id="TEST",
            epic_id="E002",
            title="Query Test",
            content={},
            breadcrumbs={},
            status="active",
            version=1
        )
        session.add(artifact)
        session.commit()
        
        # Query by path
        found = session.query(Artifact).filter(
            Artifact.artifact_path == "TEST/E002"
        ).first()
        
        assert found is not None
        assert found.title == "Query Test"
        assert found.artifact_type == "epic"
    
    def test_query_by_project(self, clean_artifacts):
        """Test querying artifacts by project."""
        session = clean_artifacts
        
        # Create multiple artifacts
        for i in range(3):
            artifact = Artifact(
                id=uuid.uuid4(),
                artifact_path=f"TEST/E00{i}",
                artifact_type="epic",
                project_id="TEST",
                epic_id=f"E00{i}",
                title=f"Epic {i}",
                content={},
                breadcrumbs={},
                status="active",
                version=1
            )
            session.add(artifact)
        session.commit()
        
        # Query by project
        artifacts = session.query(Artifact).filter(
            Artifact.project_id == "TEST"
        ).all()
        
        assert len(artifacts) == 3
    
    def test_query_by_type(self, clean_artifacts):
        """Test querying artifacts by type."""
        session = clean_artifacts
        
        # Create different types
        epic = Artifact(
            id=uuid.uuid4(),
            artifact_path="TEST/E003",
            artifact_type="epic",
            project_id="TEST",
            epic_id="E003",
            title="Epic",
            content={},
            breadcrumbs={},
            status="active",
            version=1
        )
        feature = Artifact(
            id=uuid.uuid4(),
            artifact_path="TEST/E003/F001",
            artifact_type="feature",
            project_id="TEST",
            epic_id="E003",
            feature_id="F001",
            title="Feature",
            content={},
            breadcrumbs={},
            status="active",
            version=1,
            parent_path="TEST/E003"
        )
        
        session.add(epic)
        session.add(feature)
        session.commit()
        
        # Query epics
        epics = session.query(Artifact).filter(
            Artifact.artifact_type == "epic"
        ).all()
        
        assert len(epics) >= 1
        assert all(a.artifact_type == "epic" for a in epics)
    
    def test_parent_child_relationship(self, clean_artifacts):
        """Test parent-child artifact relationships."""
        session = clean_artifacts
        
        # Create parent epic
        epic = Artifact(
            id=uuid.uuid4(),
            artifact_path="TEST/E004",
            artifact_type="epic",
            project_id="TEST",
            epic_id="E004",
            title="Parent Epic",
            content={},
            breadcrumbs={},
            status="active",
            version=1
        )
        session.add(epic)
        session.commit()
        
        # Create child feature
        feature = Artifact(
            id=uuid.uuid4(),
            artifact_path="TEST/E004/F001",
            artifact_type="feature",
            project_id="TEST",
            epic_id="E004",
            feature_id="F001",
            title="Child Feature",
            content={},
            breadcrumbs={},
            status="active",
            version=1,
            parent_path="TEST/E004"
        )
        session.add(feature)
        session.commit()
        
        # Query children
        children = session.query(Artifact).filter(
            Artifact.parent_path == "TEST/E004"
        ).all()
        
        assert len(children) == 1
        assert children[0].artifact_path == "TEST/E004/F001"
    
    def test_jsonb_content_storage(self, clean_artifacts):
        """Test JSONB content field."""
        session = clean_artifacts
        
        content = {
            "description": "Test description",
            "stories": [
                {"id": "S001", "title": "Story 1"},
                {"id": "S002", "title": "Story 2"}
            ],
            "metadata": {
                "priority": "high",
                "estimate": "2 weeks"
            }
        }
        
        artifact = Artifact(
            id=uuid.uuid4(),
            artifact_path="TEST/E005",
            artifact_type="epic",
            project_id="TEST",
            epic_id="E005",
            title="JSONB Test",
            content=content,
            breadcrumbs={},
            status="active",
            version=1
        )
        
        session.add(artifact)
        session.commit()
        session.refresh(artifact)
        
        # Verify JSONB was stored correctly
        assert artifact.content["description"] == "Test description"
        assert len(artifact.content["stories"]) == 2
        assert artifact.content["metadata"]["priority"] == "high"
    
    def test_update_artifact(self, clean_artifacts):
        """Test updating an artifact."""
        session = clean_artifacts
        
        # Create artifact
        artifact = Artifact(
            id=uuid.uuid4(),
            artifact_path="TEST/E006",
            artifact_type="epic",
            project_id="TEST",
            epic_id="E006",
            title="Original Title",
            content={"version": 1},
            breadcrumbs={},
            status="draft",
            version=1
        )
        session.add(artifact)
        session.commit()
        
        # Update it
        artifact.title = "Updated Title"
        artifact.status = "active"
        artifact.content = {"version": 2}
        artifact.version = 2
        
        session.commit()
        session.refresh(artifact)
        
        # Verify updates
        assert artifact.title == "Updated Title"
        assert artifact.status == "active"
        assert artifact.content["version"] == 2
        assert artifact.version == 2
        assert artifact.updated_at > artifact.created_at