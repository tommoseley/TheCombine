"""
Schema Registry Service for ADR-031.

Provides CRUD operations and lifecycle management for schema artifacts.
"""

import hashlib
import json
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.schema_artifact import SchemaArtifact


class SchemaNotFoundError(Exception):
    """Raised when a schema artifact is not found."""
    pass


class InvalidStatusTransitionError(Exception):
    """Raised when an invalid status transition is attempted."""
    pass


class SchemaRegistryService:
    """
    Service for managing schema artifacts in the registry.
    
    Per ADR-031:
    - Schemas are stored as governed artifacts in the database
    - Only accepted schemas may be used for LLM generation
    - Schema JSON is hashed for auditability
    """
    
    # Valid status transitions
    VALID_TRANSITIONS = {
        "draft": {"accepted", "deprecated"},
        "accepted": {"deprecated"},
        "deprecated": set(),  # Terminal state
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        schema_id: str,
        kind: str,
        schema_json: dict,
        version: str = "1.0",
        status: str = "draft",
        governance_refs: Optional[dict] = None,
        created_by: Optional[str] = None,
    ) -> SchemaArtifact:
        """
        Create a new schema artifact.
        
        Args:
            schema_id: Canonical identifier (e.g., "OpenQuestionV1")
            kind: Schema kind ("type", "document", "envelope")
            schema_json: The JSON Schema definition
            version: Version string (default "1.0")
            status: Initial status (default "draft")
            governance_refs: Optional dict of governing ADRs/policies
            created_by: Optional creator identifier
            
        Returns:
            The created SchemaArtifact
        """
        sha256 = self.compute_hash(schema_json)
        
        artifact = SchemaArtifact(
            schema_id=schema_id,
            version=version,
            kind=kind,
            status=status,
            schema_json=schema_json,
            sha256=sha256,
            governance_refs=governance_refs,
            created_by=created_by,
        )
        
        self.db.add(artifact)
        await self.db.commit()
        await self.db.refresh(artifact)
        
        return artifact
    
    async def get_by_id(
        self,
        schema_id: str,
        version: Optional[str] = None,
    ) -> Optional[SchemaArtifact]:
        """
        Get a schema artifact by ID and optional version.
        
        If version is None, returns the latest accepted version.
        
        Args:
            schema_id: The schema identifier
            version: Optional specific version
            
        Returns:
            SchemaArtifact or None if not found
        """
        if version:
            # Exact version lookup
            query = select(SchemaArtifact).where(
                and_(
                    SchemaArtifact.schema_id == schema_id,
                    SchemaArtifact.version == version,
                )
            )
        else:
            # Latest accepted version
            query = (
                select(SchemaArtifact)
                .where(
                    and_(
                        SchemaArtifact.schema_id == schema_id,
                        SchemaArtifact.status == "accepted",
                    )
                )
                .order_by(SchemaArtifact.created_at.desc())
                .limit(1)
            )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_accepted(self, schema_id: str) -> Optional[SchemaArtifact]:
        """
        Get the latest accepted version of a schema.
        
        Args:
            schema_id: The schema identifier
            
        Returns:
            SchemaArtifact or None if no accepted version exists
        """
        query = (
            select(SchemaArtifact)
            .where(
                and_(
                    SchemaArtifact.schema_id == schema_id,
                    SchemaArtifact.status == "accepted",
                )
            )
            .order_by(SchemaArtifact.created_at.desc())
            .limit(1)
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def set_status(
        self,
        schema_id: str,
        version: str,
        new_status: str,
    ) -> SchemaArtifact:
        """
        Update the status of a schema artifact.
        
        Valid transitions:
        - draft -> accepted
        - draft -> deprecated
        - accepted -> deprecated
        
        Args:
            schema_id: The schema identifier
            version: The specific version
            new_status: The new status
            
        Returns:
            The updated SchemaArtifact
            
        Raises:
            SchemaNotFoundError: If schema not found
            InvalidStatusTransitionError: If transition not allowed
        """
        artifact = await self.get_by_id(schema_id, version)
        
        if not artifact:
            raise SchemaNotFoundError(
                f"Schema '{schema_id}' version '{version}' not found"
            )
        
        current_status = artifact.status
        valid_next = self.VALID_TRANSITIONS.get(current_status, set())
        
        if new_status not in valid_next:
            raise InvalidStatusTransitionError(
                f"Cannot transition from '{current_status}' to '{new_status}'. "
                f"Valid transitions: {valid_next or 'none'}"
            )
        
        artifact.status = new_status
        await self.db.commit()
        await self.db.refresh(artifact)
        
        return artifact
    
    async def list_by_kind(
        self,
        kind: str,
        status: Optional[str] = None,
    ) -> List[SchemaArtifact]:
        """
        List schema artifacts by kind and optional status.
        
        Args:
            kind: Schema kind to filter by
            status: Optional status to filter by
            
        Returns:
            List of matching SchemaArtifacts
        """
        conditions = [SchemaArtifact.kind == kind]
        
        if status:
            conditions.append(SchemaArtifact.status == status)
        
        query = (
            select(SchemaArtifact)
            .where(and_(*conditions))
            .order_by(SchemaArtifact.schema_id, SchemaArtifact.version)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def list_all(
        self,
        status: Optional[str] = None,
    ) -> List[SchemaArtifact]:
        """
        List all schema artifacts with optional status filter.
        
        Args:
            status: Optional status to filter by
            
        Returns:
            List of matching SchemaArtifacts
        """
        if status:
            query = (
                select(SchemaArtifact)
                .where(SchemaArtifact.status == status)
                .order_by(SchemaArtifact.schema_id, SchemaArtifact.version)
            )
        else:
            query = (
                select(SchemaArtifact)
                .order_by(SchemaArtifact.schema_id, SchemaArtifact.version)
            )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    def compute_hash(schema_json: dict) -> str:
        """
        Compute deterministic SHA256 hash of schema JSON.
        
        Uses sorted keys and no whitespace for determinism.
        
        Args:
            schema_json: The schema dictionary
            
        Returns:
            64-character hex SHA256 hash
        """
        # Deterministic JSON serialization
        canonical = json.dumps(schema_json, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()