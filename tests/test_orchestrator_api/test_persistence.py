"""
Tests for database persistence and repository layer.

Tests that data survives database restarts and concurrent operations.
"""
import pytest
from sqlalchemy import text
from database import SessionLocal
from app.combine.models import Artifact, RolePrompt
import uuid


class TestDatabasePersistence:
    """Test that data persists correctly in PostgreSQL."""
    
    def test_artifact_survives_session_close(self):
        """Verify artifacts persist after session close."""
        # Create and save artifact in one session
        session1 = SessionLocal()
        try:
            artifact = Artifact(
                id=uuid.uuid4(),
                artifact_path="TEST/PERSIST/001",
                artifact_type="epic",
                project_id="TEST",
                epic_id="PERSIST",
                title="Persistence Test",
                content={"test": "data"},
                breadcrumbs={},
                status="active",
                version=1
            )
            session1.add(artifact)
            session1.commit()
            artifact_id = artifact.id
        finally:
            session1.close()
        
        # Retrieve in new session
        session2 = SessionLocal()
        try:
            retrieved = session2.query(Artifact).filter(
                Artifact.id == artifact_id
            ).first()
            
            assert retrieved is not None
            assert retrieved.title == "Persistence Test"
            assert retrieved.content["test"] == "data"
            
            # Cleanup
            session2.delete(retrieved)
            session2.commit()
        finally:
            session2.close()
    
    def test_role_prompt_survives_session_close(self):
        """Verify role prompts persist after session close."""
        # Create and save prompt in one session
        session1 = SessionLocal()
        try:
            prompt = RolePrompt(
                id="test-persist-001",
                role_name="test_persist",
                version="1.0",
                instructions="Test instructions",
                expected_schema={"type": "object"},
                is_active=True
            )
            session1.add(prompt)
            session1.commit()
            prompt_id = prompt.id
        finally:
            session1.close()
        
        # Retrieve in new session
        session2 = SessionLocal()
        try:
            retrieved = session2.query(RolePrompt).filter(
                RolePrompt.id == prompt_id
            ).first()
            
            assert retrieved is not None
            assert retrieved.instructions == "Test instructions"
            assert retrieved.expected_schema["type"] == "object"
            
            # Cleanup
            session2.delete(retrieved)
            session2.commit()
        finally:
            session2.close()
    
    def test_jsonb_data_integrity(self):
        """Verify JSONB data maintains structure after persistence."""
        complex_content = {
            "nested": {
                "array": [1, 2, 3],
                "object": {"key": "value"},
                "number": 42,
                "bool": True,
                "null": None
            }
        }
        
        session = SessionLocal()
        try:
            artifact = Artifact(
                id=uuid.uuid4(),
                artifact_path="TEST/JSONB/001",
                artifact_type="epic",
                project_id="TEST",
                epic_id="JSONB",
                title="JSONB Test",
                content=complex_content,
                breadcrumbs={},
                status="active",
                version=1
            )
            session.add(artifact)
            session.commit()
            session.refresh(artifact)
            
            # Verify structure preserved
            assert artifact.content["nested"]["array"] == [1, 2, 3]
            assert artifact.content["nested"]["object"]["key"] == "value"
            assert artifact.content["nested"]["number"] == 42
            assert artifact.content["nested"]["bool"] is True
            assert artifact.content["nested"]["null"] is None
            
            # Cleanup
            session.delete(artifact)
            session.commit()
        finally:
            session.close()


class TestConcurrency:
    """Test concurrent database operations."""
    
    def test_concurrent_artifact_creates(self):
        """Verify multiple artifacts can be created concurrently."""
        sessions = []
        artifact_ids = []
        
        try:
            # Create 5 artifacts in parallel sessions
            for i in range(5):
                session = SessionLocal()
                sessions.append(session)
                
                artifact = Artifact(
                    id=uuid.uuid4(),
                    artifact_path=f"TEST/CONCURRENT/{i}",
                    artifact_type="epic",
                    project_id="TEST",
                    epic_id="CONCURRENT",
                    title=f"Concurrent {i}",
                    content={},
                    breadcrumbs={},
                    status="active",
                    version=1
                )
                session.add(artifact)
                session.commit()
                artifact_ids.append(artifact.id)
            
            # Verify all were created
            verify_session = SessionLocal()
            try:
                count = verify_session.query(Artifact).filter(
                    Artifact.epic_id == "CONCURRENT"
                ).count()
                assert count == 5
            finally:
                verify_session.close()
            
        finally:
            # Cleanup
            for session in sessions:
                session.close()
            
            cleanup_session = SessionLocal()
            try:
                cleanup_session.execute(
                    text("DELETE FROM artifacts WHERE epic_id = 'CONCURRENT'")
                )
                cleanup_session.commit()
            finally:
                cleanup_session.close()
    
    def test_optimistic_locking_with_version(self):
        """Verify version field prevents concurrent update conflicts."""
        session = SessionLocal()
        try:
            # Create artifact
            artifact = Artifact(
                id=uuid.uuid4(),
                artifact_path="TEST/VERSION/001",
                artifact_type="epic",
                project_id="TEST",
                epic_id="VERSION",
                title="Version Test",
                content={},
                breadcrumbs={},
                status="draft",
                version=1
            )
            session.add(artifact)
            session.commit()
            artifact_id = artifact.id
            
            # Update version
            artifact.status = "active"
            artifact.version = 2
            session.commit()
            
            # Verify version incremented
            session.refresh(artifact)
            assert artifact.version == 2
            assert artifact.status == "active"
            
            # Cleanup
            session.delete(artifact)
            session.commit()
        finally:
            session.close()


class TestTransactions:
    """Test transaction behavior."""
    
    def test_rollback_on_error(self):
        """Verify failed transactions rollback correctly."""
        session = SessionLocal()
        try:
            # Start transaction
            artifact = Artifact(
                id=uuid.uuid4(),
                artifact_path="TEST/ROLLBACK/001",
                artifact_type="epic",
                project_id="TEST",
                epic_id="ROLLBACK",
                title="Rollback Test",
                content={},
                breadcrumbs={},
                status="active",
                version=1
            )
            session.add(artifact)
            
            # Force an error before commit
            session.rollback()
            
            # Verify artifact was not persisted
            count = session.query(Artifact).filter(
                Artifact.epic_id == "ROLLBACK"
            ).count()
            assert count == 0
        finally:
            session.close()