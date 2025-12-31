"""
Project audit logging service.
Provides transactional audit event creation with metadata validation.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, Dict, Any
from uuid import UUID
import json
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
        Write audit event to project_audit table.
        
        MUST be called within an active transaction.
        Validates action against allowed values.
        
        Args:
            db: Database session (must be in transaction)
            project_id: Project being audited
            action: One of CREATED, UPDATED, ARCHIVED, UNARCHIVED, EDIT_BLOCKED_ARCHIVED
            actor_user_id: User who performed action (NULL for system)
            reason: Optional human-readable reason
            metadata: Structured audit context (meta_version, client, changed_fields, etc.)
            correlation_id: Request correlation ID for tracing
        
        Raises:
            ValueError: If action is not valid
            
        Example:
            async with db.begin():
                await db.execute(text("UPDATE projects ..."))
                await audit_service.log_event(
                    db=db,
                    project_id=project_uuid,
                    action='UPDATED',
                    actor_user_id=user_uuid,
                    metadata={'changed_fields': ['name'], 'before': {...}, 'after': {...}}
                )
        """
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
            await db.execute(
                text("""
                    INSERT INTO project_audit (
                        id, project_id, actor_user_id, action, reason, metadata, created_at
                    ) VALUES (
                        gen_random_uuid(), 
                        :project_id, 
                        :actor_user_id, 
                        :action, 
                        :reason, 
                        :metadata, 
                        NOW()
                    )
                """),
                {
                    "project_id": str(project_id),
                    "actor_user_id": str(actor_user_id) if actor_user_id else None,
                    "action": action,
                    "reason": reason,
                    "metadata": json.dumps(audit_metadata)
                }
            )
            
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