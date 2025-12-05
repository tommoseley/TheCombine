from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from app.orchestrator_api.models import Artifact
from app.orchestrator_api.persistence.database import SessionLocal

class ArtifactRepository:
    """Repository for Artifact CRUD operations."""
    
    @staticmethod
    def create(
        pipeline_id: str,
        artifact_type: str,
        phase: str,
        payload: dict,
        mentor_role: Optional[str] = None,
        validation_status: str = "valid"
    ) -> Artifact:
        """Create new artifact."""
        session = SessionLocal()
        try:
            artifact = Artifact(
                artifact_id=f"pip_{uuid.uuid4().hex}",
                pipeline_id=pipeline_id,
                artifact_type=artifact_type,
                phase=phase,
                mentor_role=mentor_role,
                payload=payload,
                validation_status=validation_status
            )
            session.add(artifact)
            session.commit()
            session.refresh(artifact)
            return artifact
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @staticmethod
    def get_by_pipeline_id(pipeline_id: str) -> List[Artifact]:
        """Get all artifacts for a pipeline."""
        session = SessionLocal()
        try:
            return session.query(Artifact).filter(Artifact.pipeline_id == pipeline_id).all()
        finally:
            session.close()
    
    @staticmethod
    def get_by_type(pipeline_id: str, artifact_type: str) -> Optional[Artifact]:
        """Get artifact by type for a pipeline."""
        session = SessionLocal()
        try:
            return session.query(Artifact).filter(
                Artifact.pipeline_id == pipeline_id,
                Artifact.artifact_type == artifact_type
            ).first()
        finally:
            session.close()