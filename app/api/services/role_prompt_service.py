"""Role prompt service for building prompts from database."""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models import Role, RoleTask

logger = logging.getLogger(__name__)


@dataclass
class ComposedPrompt:
    """Represents a composed prompt from role + task"""
    task_id: str
    role_name: str
    task_name: str
    identity_prompt: str
    task_prompt: str
    expected_schema: Optional[Dict[str, Any]]
    progress_steps: Optional[list]
    version: str
    created_at: datetime


class RolePromptService:
    """Service for building role prompts with context injection."""

    def __init__(self, db: AsyncSession):
        """
        Initialize the service with database session.
        
        Args:
            db: SQLAlchemy async database session
        """
        self.db = db

    async def get_role_task(
        self, 
        role_name: str, 
        task_name: str
    ) -> Optional[ComposedPrompt]:
        """
        Get a role + task combination from the database.
        
        Args:
            role_name: Role identifier (pm, architect, ba, developer, qa)
            task_name: Task identifier (preliminary, final, epic_creation, etc.)
            
        Returns:
            ComposedPrompt or None
        """
        query = (
            select(Role, RoleTask)
            .join(RoleTask, Role.id == RoleTask.role_id)
            .where(Role.name == role_name)
            .where(RoleTask.task_name == task_name)
            .where(RoleTask.is_active == True)
        )
        
        result = await self.db.execute(query)
        row = result.first()
        
        if not row:
            return None
        
        role, task = row
        
        return ComposedPrompt(
            task_id=str(task.id),
            role_name=role.name,
            task_name=task.task_name,
            identity_prompt=role.identity_prompt,
            task_prompt=task.task_prompt,
            expected_schema=task.expected_schema,
            progress_steps=task.progress_steps,
            version=task.version,
            created_at=task.created_at
        )

    async def build_prompt(
        self,
        role_name: str,
        task_name: str,
        pipeline_id: str = None,  # Legacy, ignored
        phase: str = None,  # Legacy, ignored
        epic_context: Optional[str] = None,
        pipeline_state: Optional[Dict[str, Any]] = None,
        artifacts: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """
        Build complete role prompt with all sections.

        Args:
            role_name: Role identifier (pm, architect, ba, developer, qa)
            task_name: Task identifier (preliminary, final, epic_creation, etc.)
            pipeline_id: DEPRECATED - ignored
            phase: DEPRECATED - ignored
            epic_context: Epic description (optional)
            pipeline_state: State data (optional)
            artifacts: Previous artifacts as dict (optional)

        Returns:
            Tuple of (prompt_text, task_id) for execution and audit

        Raises:
            ValueError: If no active prompt found for role/task
        """
        # Load role + task
        composed = await self.get_role_task(role_name, task_name)
        if not composed:
            raise ValueError(f"No active prompt found for role '{role_name}' task '{task_name}'")

        # Warn if prompt is stale (>1 year old)
        created_at = composed.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        age_days = (datetime.now(timezone.utc) - created_at).days
        if age_days > 365:
            logger.warning(
                f"Role task '{role_name}/{task_name}' is {age_days} days old. "
                f"Consider creating new version."
            )

        # Build sections
        sections = []

        # Identity Prompt (who you are)
        sections.append("# Role Identity")
        sections.append("")
        sections.append(composed.identity_prompt)
        sections.append("")

        # Task Prompt (what you're doing)
        sections.append("# Current Task")
        sections.append("")
        sections.append(composed.task_prompt)
        sections.append("")

        # Expected Schema (optional)
        if composed.expected_schema:
            sections.append("# Expected Output Schema")
            sections.append("")
            sections.append("```json")
            sections.append(json.dumps(composed.expected_schema, indent=2))
            sections.append("```")
            sections.append("")

        # Epic Context (optional)
        if epic_context:
            sections.append("# Epic Context")
            sections.append("")
            sections.append(epic_context)
            sections.append("")

        # Pipeline/Artifact State (optional)
        if pipeline_state:
            sections.append("# Context State")
            sections.append("")
            sections.append("```json")
            sections.append(json.dumps(pipeline_state, indent=2))
            sections.append("```")
            sections.append("")

        # Previous Artifacts (optional)
        if artifacts:
            sections.append("# Previous Artifacts")
            sections.append("")
            sections.append("```json")
            sections.append(json.dumps(artifacts, indent=2))
            sections.append("```")
            sections.append("")

        # Join all sections
        prompt_text = "\n".join(sections)

        return prompt_text, composed.task_id

    async def get_prompt_by_id(self, task_id: str) -> Optional[ComposedPrompt]:
        """
        Get a task record by ID.
        
        Args:
            task_id: The task identifier (UUID)
            
        Returns:
            ComposedPrompt or None
        """
        query = (
            select(Role, RoleTask)
            .join(RoleTask, Role.id == RoleTask.role_id)
            .where(RoleTask.id == task_id)
        )
        
        result = await self.db.execute(query)
        row = result.first()
        
        if not row:
            return None
        
        role, task = row
        
        return ComposedPrompt(
            task_id=str(task.id),
            role_name=role.name,
            task_name=task.task_name,
            identity_prompt=role.identity_prompt,
            task_prompt=task.task_prompt,
            expected_schema=task.expected_schema,
            progress_steps=task.progress_steps,
            version=task.version,
            created_at=task.created_at
        )

    async def get_active_task(self, role_name: str, task_name: str) -> Optional[ComposedPrompt]:
        """
        Get the active task for a role.
        
        Args:
            role_name: Role identifier (pm, architect, ba, developer, qa)
            task_name: Task identifier
            
        Returns:
            ComposedPrompt or None
        """
        return await self.get_role_task(role_name, task_name)