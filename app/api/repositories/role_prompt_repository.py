"""
Repository for RolePrompt CRUD operations (ASYNC VERSION).

Matches the actual PostgreSQL schema with simplified fields.
"""
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.api.models.role_prompt import RolePrompt
from database import AsyncSessionLocal
from app.api.repositories.exceptions import RepositoryError


class RolePromptRepository:
    """Repository for RolePrompt CRUD operations."""
    
    @staticmethod
    async def get_active_prompt(role_name: str) -> Optional[RolePrompt]:
        """
        Get currently active prompt for a role.
        
        Args:
            role_name: Role identifier (pm, architect, ba, developer, qa)
            
        Returns:
            Active RolePrompt or None if not found
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(RolePrompt).where(
                    RolePrompt.role_name == role_name,
                    RolePrompt.is_active == True
                )
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_id(prompt_id: str) -> Optional[RolePrompt]:
        """
        Get specific prompt by ID.
        
        Args:
            prompt_id: Prompt identifier
            
        Returns:
            RolePrompt or None if not found
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(RolePrompt).where(RolePrompt.id == prompt_id)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def list_versions(role_name: str) -> List[RolePrompt]:
        """
        List all versions for a role, ordered by date descending.
        
        Args:
            role_name: Role identifier
            
        Returns:
            List of RolePrompt versions (newest first)
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(RolePrompt)
                .where(RolePrompt.role_name == role_name)
                .order_by(RolePrompt.created_at.desc())
            )
            return result.scalars().all()
    
    @staticmethod
    async def list_all() -> List[RolePrompt]:
        """
        List all prompts across all roles.
        
        Returns:
            List of all RolePrompts
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(RolePrompt).order_by(
                    RolePrompt.role_name,
                    RolePrompt.version.desc()
                )
            )
            return result.scalars().all()
    
    @staticmethod
    async def create(
        role_name: str,
        version: str,
        instructions: str,
        expected_schema: Optional[dict] = None,
        created_by: Optional[str] = None,
        notes: Optional[str] = None,
        set_active: bool = True
    ) -> RolePrompt:
        """
        Create new role prompt.
        
        Args:
            role_name: Role identifier (pm, architect, ba, developer, qa)
            version: Version string (e.g., "1", "2", "1.1")
            instructions: The prompt instructions (required)
            expected_schema: Expected output schema as dict
            created_by: Creator identifier
            notes: Version notes
            set_active: If True, deactivate other versions for this role
            
        Returns:
            Created RolePrompt
            
        Raises:
            ValueError: If required fields missing or validation fails
            RepositoryError: If database operation fails
        """
        # Validate required fields
        if not role_name or not role_name.strip():
            raise ValueError("role_name is required and cannot be empty")
        if not version or not version.strip():
            raise ValueError("version is required and cannot be empty")
        if not instructions or not instructions.strip():
            raise ValueError("instructions is required and cannot be empty")
        
        # Validate expected_schema is dict or None
        if expected_schema is not None and not isinstance(expected_schema, dict):
            raise ValueError("expected_schema must be dict or None")
        
        async with AsyncSessionLocal() as session:
            try:
                # Deactivate existing active prompts if set_active=True
                if set_active:
                    result = await session.execute(
                        select(RolePrompt).where(
                            RolePrompt.role_name == role_name,
                            RolePrompt.is_active == True
                        )
                    )
                    existing_active = result.scalars().all()
                    for prompt in existing_active:
                        prompt.is_active = False
                
                # Generate ID
                prompt_id = f"{role_name}-v{version}"
                
                # Create new prompt
                prompt = RolePrompt(
                    id=prompt_id,
                    role_name=role_name,
                    version=version,
                    instructions=instructions,
                    expected_schema=expected_schema,
                    is_active=set_active,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    created_by=created_by,
                    notes=notes
                )
                
                session.add(prompt)
                await session.commit()
                await session.refresh(prompt)
                return prompt
                
            except IntegrityError as e:
                await session.rollback()
                raise RepositoryError(f"Database constraint violation: {e}")
            except Exception as e:
                await session.rollback()
                raise RepositoryError(f"Failed to create prompt: {e}")
    
    @staticmethod
    async def update(
        prompt_id: str,
        instructions: Optional[str] = None,
        expected_schema: Optional[dict] = None,
        notes: Optional[str] = None
    ) -> Optional[RolePrompt]:
        """
        Update an existing prompt.
        
        Args:
            prompt_id: Prompt identifier
            instructions: New instructions (optional)
            expected_schema: New schema (optional)
            notes: New notes (optional)
            
        Returns:
            Updated RolePrompt or None if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(RolePrompt).where(RolePrompt.id == prompt_id)
                )
                prompt = result.scalar_one_or_none()
                
                if not prompt:
                    return None
                
                if instructions is not None:
                    prompt.instructions = instructions
                if expected_schema is not None:
                    prompt.expected_schema = expected_schema
                if notes is not None:
                    prompt.notes = notes
                
                prompt.updated_at = datetime.now(timezone.utc)
                
                await session.commit()
                await session.refresh(prompt)
                return prompt
                
            except Exception as e:
                await session.rollback()
                raise RepositoryError(f"Failed to update prompt: {e}")
    
    @staticmethod
    async def set_active(prompt_id: str) -> RolePrompt:
        """
        Set specific prompt as active (deactivates others for same role).
        
        Args:
            prompt_id: Prompt identifier to activate
            
        Returns:
            Updated RolePrompt
            
        Raises:
            ValueError: If prompt not found
            RepositoryError: If database operation fails
        """
        async with AsyncSessionLocal() as session:
            try:
                # Get prompt to activate
                result = await session.execute(
                    select(RolePrompt).where(RolePrompt.id == prompt_id)
                )
                prompt = result.scalar_one_or_none()
                
                if not prompt:
                    raise ValueError(f"Prompt not found: {prompt_id}")
                
                # Deactivate other prompts for same role
                other_result = await session.execute(
                    select(RolePrompt).where(
                        RolePrompt.role_name == prompt.role_name,
                        RolePrompt.id != prompt_id,
                        RolePrompt.is_active == True
                    )
                )
                other_prompts = other_result.scalars().all()
                
                for other in other_prompts:
                    other.is_active = False
                
                # Activate target prompt
                prompt.is_active = True
                prompt.updated_at = datetime.now(timezone.utc)
                
                await session.commit()
                await session.refresh(prompt)
                return prompt
                
            except ValueError:
                await session.rollback()
                raise
            except Exception as e:
                await session.rollback()
                raise RepositoryError(f"Failed to set active prompt: {e}")
    
    @staticmethod
    async def delete(prompt_id: str) -> bool:
        """
        Delete a prompt.
        
        Args:
            prompt_id: Prompt identifier
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(RolePrompt).where(RolePrompt.id == prompt_id)
                )
                prompt = result.scalar_one_or_none()
                
                if not prompt:
                    return False
                
                await session.delete(prompt)
                await session.commit()
                return True
                
            except Exception as e:
                await session.rollback()
                raise RepositoryError(f"Failed to delete prompt: {e}")