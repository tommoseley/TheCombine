"""
Project audit logging service.
Provides transactional audit event creation with metadata validation.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


class ProjectAuditService:
    """
    Handles append-only audit logging for project lifecycle events.
    
    Must be called within an active transaction. Validates action against
    allowed values and ensures metadata follows canonical structure.
    """
    
    VALID_ACTIONS = {
        'CREATED', 
        'UPDATED', 
        'ARCHIVED', 
        'UNARCHIVED', 
        'EDIT_BLOCKED_ARCHIVED'
    }
    
    @staticmethod
    async def log_event(
        db: AsyncSession,
        project_id: UUID,
        action: str,
        actor_user_id: Optional[UUID] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Write audit event to project_audit table via ORM.
        
        MUST be called within an active transaction.
        Validates action against allowed values.
        """
        # Lazy import to avoid circular dependency
        from app.api.models.project_audit import ProjectAudit
        
        # Validate action
        if action not in ProjectAuditService.VALID_ACTIONS:
            raise ValueError(
                f"Invalid audit action: {action}. "
                f"Must be one of: {', '.join(sorted(ProjectAuditService.VALID_ACTIONS))}"
            )
        
        # Ensure metadata has required structure
        audit_metadata = metadata or {}
        if 'meta_version' not in audit_metadata:
            audit_metadata['meta_version'] = '1.0'
        if correlation_id and 'correlation_id' not in audit_metadata:
            audit_metadata['correlation_id'] = correlation_id
        
        try:
            audit_entry = ProjectAudit(
                project_id=project_id,
                actor_user_id=actor_user_id,
                action=action,
                reason=reason,
                meta=audit_metadata,
            )
            db.add(audit_entry)
            
            logger.info(
                f"Audit event logged: action={action}, project_id={project_id}, "
                f"actor={actor_user_id or 'system'}"
            )
            
        except Exception as e:
            logger.error(
                f"Failed to write audit event: action={action}, project_id={project_id}, "
                f"error={e}", 
                exc_info=True
            )
            raise


# Singleton instance
audit_service = ProjectAuditService()