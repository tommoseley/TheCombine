"""Data access layer using Repository pattern."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
from app.orchestrator_api.models import Pipeline, Artifact, PhaseTransition, RolePrompt, PipelinePromptUsage    
from app.orchestrator_api.persistence.database import SessionLocal

class PhaseTransitionRepository:
    """Repository for PhaseTransition CRUD operations."""
    
    @staticmethod
    def create(pipeline_id: str, from_state: str, to_state: str, reason: Optional[str] = None) -> PhaseTransition:
        """Record phase transition."""
        session = SessionLocal()
        try:
            transition = PhaseTransition(
                transition_id=f"rtn_{uuid.uuid4().hex[:16]}",
                pipeline_id=pipeline_id,
                from_state=from_state,
                to_state=to_state,
                reason=reason
            )
            session.add(transition)
            session.commit()
            session.refresh(transition)
            return transition
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @staticmethod
    def get_by_pipeline_id(pipeline_id: str) -> List[PhaseTransition]:
        """Get transition history for a pipeline."""
        session = SessionLocal()
        try:
            return session.query(PhaseTransition).filter(
                PhaseTransition.pipeline_id == pipeline_id
            ).order_by(PhaseTransition.timestamp.asc()).all()
        finally:
            session.close()

