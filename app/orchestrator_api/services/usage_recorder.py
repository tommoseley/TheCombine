"""
Usage Recorder - Record prompt usage to audit trail (best-effort).

This module records prompt usage for audit and analytics purposes.
Recording failures do not block pipeline execution.

Author: D-2 (Mid-Level Developer)
Epic: PIPELINE-175B
"""

from dataclasses import dataclass
import logging
from app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository import (
    PipelinePromptUsageRepository
)

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    """Prompt usage data to record."""
    pipeline_id: str
    prompt_id: str
    role_name: str
    phase_name: str


class UsageRecorder:
    """Record prompt usage to audit trail."""
    
    def __init__(self, repo: PipelinePromptUsageRepository):
        """
        Initialize recorder with repository.
        
        Args:
            repo: Pipeline prompt usage repository instance
        """
        self._repo = repo
    
    def record_usage(self, usage: UsageRecord) -> bool:
        """
        Record prompt usage (best-effort).
        
        Args:
            usage: Usage record to persist
            
        Returns:
            True if recorded successfully, False on any error
            
        Raises:
            Never raises - logs errors and returns False
        """
        try:
            usage_id = self._repo.record_usage(
                pipeline_id=usage.pipeline_id,
                prompt_id=usage.prompt_id
            )
            logger.debug(f"Recorded usage: usage_id={usage_id}")
            return True
            
        except Exception as e:
            # QA Issue #4: Structured logging for audit failures
            logger.warning(
                "Usage record failure",
                extra={
                    "event": "usage_record_failure",
                    "pipeline_id": usage.pipeline_id,
                    "phase_name": usage.phase_name,
                    "role_name": usage.role_name,
                    "prompt_id": usage.prompt_id,
                    "error": str(e)
                }
            )
            return False