"""
ComponentRegistryService for ADR-034 Canonical Components.

Provides read-first operations for component artifacts:
- get (exact match)
- get_accepted (latest accepted by prefix, ordered by accepted_at DESC)
- list_by_schema
- create
- accept (only mutation permitted)
"""

import re
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.component_artifact import ComponentArtifact
from app.api.models.schema_artifact import SchemaArtifact


logger = logging.getLogger(__name__)


# Component ID pattern: component:<Name>:<semver>
COMPONENT_ID_PATTERN = re.compile(r"^component:[A-Za-z0-9._-]+:[0-9]+\.[0-9]+\.[0-9]+$")


class ComponentRegistryError(Exception):
    """Base exception for component registry operations."""
    pass


class InvalidComponentIdError(ComponentRegistryError):
    """Raised when component_id format is invalid."""
    pass


class ComponentNotFoundError(ComponentRegistryError):
    """Raised when component is not found."""
    pass


class ComponentAlreadyAcceptedError(ComponentRegistryError):
    """Raised when trying to accept an already-accepted component."""
    pass


class SchemaNotFoundError(ComponentRegistryError):
    """Raised when referenced schema does not exist."""
    pass


class ComponentRegistryService:
    """
    Service for managing canonical component specifications.
    
    Per ADR-034 and WS-ADR-034-POC:
    - Read-first: get, get_accepted, list_by_schema, create, accept
    - No general update/delete (only accept() permitted)
    - get_accepted uses accepted_at DESC for deterministic ordering (D7)
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _validate_component_id(self, component_id: str) -> None:
        """Validate component_id matches canonical format."""
        if not COMPONENT_ID_PATTERN.match(component_id):
            raise InvalidComponentIdError(
                f"Invalid component_id format: '{component_id}'. "
                f"Expected: component:<Name>:<semver> (e.g., component:OpenQuestionV1:1.0.0)"
            )
    
    async def get(self, component_id: str) -> Optional[ComponentArtifact]:
        """
        Get component by exact component_id.
        
        Args:
            component_id: Exact component ID (e.g., component:OpenQuestionV1:1.0.0)
            
        Returns:
            ComponentArtifact or None if not found
        """
        stmt = select(ComponentArtifact).where(
            ComponentArtifact.component_id == component_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_accepted(self, component_id_prefix: str) -> Optional[ComponentArtifact]:
        """
        Get latest accepted component matching prefix.
        
        Per D7: Orders by accepted_at DESC for deterministic results.
        
        Args:
            component_id_prefix: Prefix to match (e.g., "component:OpenQuestionV1:")
            
        Returns:
            Latest accepted ComponentArtifact or None
        """
        stmt = (
            select(ComponentArtifact)
            .where(
                and_(
                    ComponentArtifact.component_id.startswith(component_id_prefix),
                    ComponentArtifact.status == "accepted",
                )
            )
            .order_by(ComponentArtifact.accepted_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_by_schema(self, schema_id: str) -> List[ComponentArtifact]:
        """
        List all components using a specific schema.
        
        Args:
            schema_id: Schema ID to filter by (e.g., schema:OpenQuestionV1)
            
        Returns:
            List of ComponentArtifact
        """
        stmt = (
            select(ComponentArtifact)
            .where(ComponentArtifact.schema_id == schema_id)
            .order_by(ComponentArtifact.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def list_all(self, status: Optional[str] = None) -> List[ComponentArtifact]:
        """
        List all components, optionally filtered by status.
        
        Args:
            status: Optional status filter ('draft', 'accepted')
            
        Returns:
            List of ComponentArtifact
        """
        stmt = select(ComponentArtifact)
        
        if status:
            stmt = stmt.where(ComponentArtifact.status == status)
        
        stmt = stmt.order_by(ComponentArtifact.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def create(
        self,
        component_id: str,
        schema_artifact_id: UUID,
        schema_id: str,
        generation_guidance: dict,
        view_bindings: dict,
        created_by: Optional[str] = None,
        status: str = "draft",
    ) -> ComponentArtifact:
        """
        Create a new component artifact.
        
        Args:
            component_id: Canonical component ID with semver
            schema_artifact_id: UUID FK to schema_artifacts
            schema_id: Denormalized schema ID string
            generation_guidance: Prompt generation bullets
            view_bindings: Channel-specific fragment bindings
            created_by: Optional creator identifier
            status: Initial status (default: draft)
            
        Returns:
            Created ComponentArtifact
            
        Raises:
            InvalidComponentIdError: If component_id format is invalid
            SchemaNotFoundError: If schema_artifact_id doesn't exist
        """
        # Validate component_id format
        self._validate_component_id(component_id)
        
        # Verify schema exists
        schema_stmt = select(SchemaArtifact).where(SchemaArtifact.id == schema_artifact_id)
        schema_result = await self.db.execute(schema_stmt)
        if not schema_result.scalar_one_or_none():
            raise SchemaNotFoundError(f"Schema artifact not found: {schema_artifact_id}")
        
        # Create component
        component = ComponentArtifact(
            component_id=component_id,
            schema_artifact_id=schema_artifact_id,
            schema_id=schema_id,
            generation_guidance=generation_guidance,
            view_bindings=view_bindings,
            status=status,
            created_by=created_by,
        )
        
        # If created as accepted, set accepted_at
        if status == "accepted":
            component.accepted_at = datetime.now(timezone.utc)
        
        self.db.add(component)
        await self.db.flush()
        await self.db.refresh(component)
        
        logger.info(f"Created component: {component_id} ({status})")
        return component
    
    async def accept(self, component_id: str) -> ComponentArtifact:
        """
        Accept a component (transition from draft to accepted).
        
        This is the only mutation permitted per D1.
        
        Args:
            component_id: Component ID to accept
            
        Returns:
            Updated ComponentArtifact
            
        Raises:
            ComponentNotFoundError: If component doesn't exist
            ComponentAlreadyAcceptedError: If already accepted
        """
        component = await self.get(component_id)
        
        if not component:
            raise ComponentNotFoundError(f"Component not found: {component_id}")
        
        if component.status == "accepted":
            raise ComponentAlreadyAcceptedError(
                f"Component already accepted: {component_id}"
            )
        
        component.status = "accepted"
        component.accepted_at = datetime.now(timezone.utc)
        
        await self.db.flush()
        await self.db.refresh(component)
        
        logger.info(f"Accepted component: {component_id}")
        return component
