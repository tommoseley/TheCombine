"""Pipeline repository for database operations."""
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.orchestrator_api.models import Pipeline
from app.orchestrator_api.persistence.database import SessionLocal


class PipelineRepository:
    """Repository for Pipeline CRUD operations."""
    
    @staticmethod
    def create(epic_id: str, pipeline_id: str) -> Pipeline:
        """Create new pipeline."""
        session = SessionLocal()
        try:
            pipeline = Pipeline(
                pipeline_id=pipeline_id,
                epic_id=epic_id,
                current_phase="pm_phase",
                state="active",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(pipeline)
            session.commit()
            session.refresh(pipeline)
            return pipeline
        finally:
            session.close()
    
    @staticmethod
    def get_by_id(pipeline_id: str) -> Optional[Pipeline]:
        """Get pipeline by ID."""
        session = SessionLocal()
        try:
            return session.query(Pipeline).filter(
                Pipeline.pipeline_id == pipeline_id
            ).first()
        finally:
            session.close()
    
    @staticmethod
    def update_state(pipeline_id: str, new_state: str, new_phase: str) -> Pipeline:
        """Update pipeline state and phase."""
        session = SessionLocal()
        try:
            pipeline = session.query(Pipeline).filter(
                Pipeline.pipeline_id == pipeline_id
            ).first()
            
            if not pipeline:
                raise ValueError(f"Pipeline not found: {pipeline_id}")
            
            pipeline.state = new_state
            pipeline.current_phase = new_phase
            pipeline.updated_at = datetime.now(timezone.utc)
            
            session.commit()
            session.refresh(pipeline)
            return pipeline
        finally:
            session.close()
    
    @staticmethod
    def list_all() -> List[Pipeline]:
        """List all pipelines."""
        session = SessionLocal()
        try:
            return session.query(Pipeline).all()
        finally:
            session.close()