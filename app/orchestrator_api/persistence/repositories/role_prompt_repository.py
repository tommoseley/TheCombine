"""
Repository for RolePrompt CRUD operations with versioning support.

Part of PIPELINE-175A: Data-Described Pipeline Infrastructure.
"""
from typing import Optional, List
from datetime import datetime, timezone
import sys
import uuid
from sqlalchemy.exc import IntegrityError
from app.orchestrator_api.models.role_prompt import RolePrompt
from app.orchestrator_api.persistence.database import SessionLocal
from app.orchestrator_api.persistence.repositories.exceptions import RepositoryError


class RolePromptRepository:
    """Repository for RolePrompt CRUD operations."""
    
    @staticmethod
    def get_active_prompt(role_name: str) -> Optional[RolePrompt]:
        """
        Get currently active prompt for a role.
        
        Args:
            role_name: Role identifier (pm, architect, ba, dev, qa, commit)
            
        Returns:
            Active RolePrompt or None if not found
        """
        session = SessionLocal()
        try:
            prompt = session.query(RolePrompt).filter(
                RolePrompt.role_name == role_name,
                RolePrompt.is_active == True
            ).first()
            return prompt
        finally:
            session.close()
    
    @staticmethod
    def get_by_id(prompt_id: str) -> Optional[RolePrompt]:
        """
        Get specific prompt by ID.
        
        Args:
            prompt_id: Prompt identifier
            
        Returns:
            RolePrompt or None if not found
        """
        session = SessionLocal()
        try:
            prompt = session.query(RolePrompt).filter(
                RolePrompt.id == prompt_id
            ).first()
            return prompt
        finally:
            session.close()
    
    @staticmethod
    def list_versions(role_name: str) -> List[RolePrompt]:
        """
        List all versions for a role, ordered by date descending.
        
        Args:
            role_name: Role identifier
            
        Returns:
            List of RolePrompt versions (newest first)
        """
        session = SessionLocal()
        try:
            prompts = session.query(RolePrompt).filter(
                RolePrompt.role_name == role_name
            ).order_by(RolePrompt.created_at.desc()).all()
            return prompts
        finally:
            session.close()
    
    @staticmethod
    def create(
        role_name: str,
        version: str,
        bootstrapper: str,
        instructions: str,
        starting_prompt: Optional[str] = None,
        working_schema: Optional[dict] = None,
        created_by: Optional[str] = None,
        notes: Optional[str] = None,
        set_active: bool = True
    ) -> RolePrompt:
        """
        Create new role prompt.
        
        Args:
            role_name: Role identifier
            version: Semantic version (1.0, 1.1, 2.0)
            bootstrapper: Role identity/framing (required)
            instructions: Detailed role instructions (required)
            starting_prompt: Optional opening context
            working_schema: Expected input/output schemas
            created_by: Creator identifier
            notes: Version changelog/notes
            set_active: If True, deactivate other versions
            
        Returns:
            Created RolePrompt
            
        Raises:
            ValueError: If required fields missing or validation fails
            RepositoryError: If database operation fails
        """
        # Validate required fields
        if not bootstrapper or not bootstrapper.strip():
            raise ValueError("bootstrapper is required and cannot be empty")
        if not instructions or not instructions.strip():
            raise ValueError("instructions is required and cannot be empty")
        if not role_name or not role_name.strip():
            raise ValueError("role_name is required and cannot be empty")
        if not version or not version.strip():
            raise ValueError("version is required and cannot be empty")
        
        # Validate working_schema is dict or None
        if working_schema is not None and not isinstance(working_schema, dict):
            raise ValueError("working_schema must be dict or None")
        
        session = SessionLocal()
        try:
            # Deactivate existing active prompts if set_active=True
            if set_active:
                existing_active = session.query(RolePrompt).filter(
                    RolePrompt.role_name == role_name,
                    RolePrompt.is_active == True
                ).all()
                for prompt in existing_active:
                    prompt.is_active = False
            
            # Create new prompt
            prompt = RolePrompt(
                id=f"rp_{uuid.uuid4().hex[:16]}",  # Fixed: use uuid instead of ULID
                role_name=role_name,
                version=version,
                starting_prompt=starting_prompt,
                bootstrapper=bootstrapper,
                instructions=instructions,
                working_schema=working_schema,
                is_active=set_active,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                created_by=created_by,
                notes=notes
            )
            
            session.add(prompt)
            session.commit()
            session.refresh(prompt)
            return prompt
            
        except IntegrityError as e:
            session.rollback()
            raise RepositoryError(f"Database constraint violation: {e}")
        except Exception as e:
            session.rollback()
            raise RepositoryError(f"Failed to create prompt: {e}")
        finally:
            session.close()
    
    @staticmethod
    def set_active(prompt_id: str) -> RolePrompt:
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
        session = SessionLocal()
        try:
            # Get prompt to activate
            prompt = session.query(RolePrompt).filter(
                RolePrompt.id == prompt_id
            ).first()
            
            if not prompt:
                raise ValueError(f"Prompt not found: {prompt_id}")
            
            # Deactivate other prompts for same role
            other_prompts = session.query(RolePrompt).filter(
                RolePrompt.role_name == prompt.role_name,
                RolePrompt.id != prompt_id,
                RolePrompt.is_active == True
            ).all()
            
            for other in other_prompts:
                other.is_active = False
            
            # Activate target prompt
            prompt.is_active = True
            prompt.updated_at = datetime.now(timezone.utc)
            
            session.commit()
            session.refresh(prompt)
            return prompt
            
        except ValueError:
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise RepositoryError(f"Failed to set active prompt: {e}")
        finally:
            session.close()