"""
Repository for PipelinePromptUsage audit trail operations.

Part of PIPELINE-175A: Data-Described Pipeline Infrastructure.
"""
from typing import List
from datetime import datetime, timezone
import uuid
from sqlalchemy.exc import IntegrityError
from app.orchestrator_api.models.pipeline_prompt_usage import PipelinePromptUsage
from app.orchestrator_api.persistence.database import SessionLocal
from app.orchestrator_api.persistence.repositories.exceptions import RepositoryError


class PipelinePromptUsageRepository:
    """Repository for pipeline prompt usage audit trail."""
    
    @staticmethod
    def record_usage(
        pipeline_id: str,
        role_name: str,
        prompt_id: str,
        phase_name: str
    ) -> PipelinePromptUsage:
        """
        Record that a prompt was used in a pipeline phase.
        
        Args:
            pipeline_id: Pipeline identifier
            role_name: Role that was executed
            prompt_id: Prompt version used
            phase_name: Phase where prompt was used
            
        Returns:
            Created PipelinePromptUsage
            
        Raises:
            RepositoryError: If foreign key constraints fail or database operation fails
        """
        session = SessionLocal()
        try:
            usage = PipelinePromptUsage(
                id=f"ppu_{uuid.uuid4().hex}",
                pipeline_id=pipeline_id,
                prompt_id=prompt_id,
                role_name=role_name,
                phase_name=phase_name,
                used_at=datetime.now(timezone.utc)
            )
            
            session.add(usage)
            session.commit()
            session.refresh(usage)
            return usage
            
        except IntegrityError as e:
            session.rollback()
            error_msg = str(e).lower()
            
            # Parse foreign key violations for clear error messages
            if "foreign key" in error_msg or "constraint" in error_msg:
                if "pipeline_id" in error_msg or "pipelines" in error_msg:
                    raise RepositoryError(f"Foreign key constraint violation: Pipeline not found: {pipeline_id}")
                elif "prompt_id" in error_msg or "role_prompts" in error_msg:
                    raise RepositoryError(f"Foreign key constraint violation: Prompt not found: {prompt_id}")
            
            # Generic constraint violation
            raise RepositoryError(f"Database constraint violation: {e}")
            
        except Exception as e:
            session.rollback()
            raise RepositoryError(f"Failed to record prompt usage: {e}")
        finally:
            session.close()
    
    @staticmethod
    def get_by_pipeline(pipeline_id: str) -> List[PipelinePromptUsage]:
        """
        Get all prompt usage records for a pipeline.
        
        Args:
            pipeline_id: Pipeline identifier
            
        Returns:
            List of PipelinePromptUsage ordered by used_at
        """
        session = SessionLocal()
        try:
            usages = session.query(PipelinePromptUsage).filter(
                PipelinePromptUsage.pipeline_id == pipeline_id
            ).order_by(PipelinePromptUsage.used_at).all()
            return usages
        finally:
            session.close()
    
    @staticmethod
    def get_by_prompt(prompt_id: str) -> List[PipelinePromptUsage]:
        """
        Get all pipelines that used a specific prompt version.
        
        Args:
            prompt_id: Prompt identifier
            
        Returns:
            List of PipelinePromptUsage ordered by used_at descending (most recent first)
        """
        session = SessionLocal()
        try:
            usages = session.query(PipelinePromptUsage).filter(
                PipelinePromptUsage.prompt_id == prompt_id
            ).order_by(PipelinePromptUsage.used_at.desc()).all()
            return usages
        finally:
            session.close()