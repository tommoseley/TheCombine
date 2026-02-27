"""
DocumentDefinitionService for ADR-034 Document Composition Manifest.

Provides read-first operations for document definitions:
- get (exact match)
- get_accepted (latest accepted by prefix, ordered by accepted_at DESC)
- list_all
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

from app.api.models.document_definition import DocumentDefinition
from app.api.models.schema_artifact import SchemaArtifact


logger = logging.getLogger(__name__)


# Document definition ID pattern: docdef:<n>:<semver>
DOCDEF_ID_PATTERN = re.compile(r"^docdef:[A-Za-z0-9._-]+:[0-9]+\.[0-9]+\.[0-9]+$")


class DocumentDefinitionError(Exception):
    """Base exception for document definition operations."""
    pass


class InvalidDocDefIdError(DocumentDefinitionError):
    """Raised when document_def_id format is invalid."""
    pass


class DocDefNotFoundError(DocumentDefinitionError):
    """Raised when document definition is not found."""
    pass


class DocDefAlreadyAcceptedError(DocumentDefinitionError):
    """Raised when trying to accept an already-accepted definition."""
    pass


class SchemaNotFoundError(DocumentDefinitionError):
    """Raised when referenced schema does not exist."""
    pass


class DocumentDefinitionService:
    """
    Service for managing document definitions (composition manifests).
    
    Per ADR-034 and WS-ADR-034-POC:
    - Read-first: get, get_accepted, list_all, create, accept
    - No general update/delete (only accept() permitted)
    - get_accepted uses accepted_at DESC for deterministic ordering (D7)
    - document_schema_id is nullable for MVP
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _validate_docdef_id(self, document_def_id: str) -> None:
        """Validate document_def_id matches canonical format."""
        if not DOCDEF_ID_PATTERN.match(document_def_id):
            raise InvalidDocDefIdError(
                f"Invalid document_def_id format: '{document_def_id}'. "
                f"Expected: docdef:<n>:<semver> (e.g., docdef:ImplementationPlan:1.0.0)"
            )
    
    async def get(self, document_def_id: str) -> Optional[DocumentDefinition]:
        """
        Get document definition by exact document_def_id.
        
        Args:
            document_def_id: Exact definition ID (e.g., docdef:ImplementationPlan:1.0.0)
            
        Returns:
            DocumentDefinition or None if not found
        """
        stmt = select(DocumentDefinition).where(
            DocumentDefinition.document_def_id == document_def_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_accepted(self, document_def_id_prefix: str) -> Optional[DocumentDefinition]:
        """
        Get latest accepted document definition matching prefix.
        
        Per D7: Orders by accepted_at DESC for deterministic results.
        
        Args:
            document_def_id_prefix: Prefix to match (e.g., "docdef:ImplementationPlan:")
            
        Returns:
            Latest accepted DocumentDefinition or None
        """
        stmt = (
            select(DocumentDefinition)
            .where(
                and_(
                    DocumentDefinition.document_def_id.startswith(document_def_id_prefix),
                    DocumentDefinition.status == "accepted",
                )
            )
            .order_by(DocumentDefinition.accepted_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_all(self, status: Optional[str] = None) -> List[DocumentDefinition]:
        """
        List all document definitions, optionally filtered by status.
        
        Args:
            status: Optional status filter ('draft', 'accepted')
            
        Returns:
            List of DocumentDefinition
        """
        stmt = select(DocumentDefinition)
        
        if status:
            stmt = stmt.where(DocumentDefinition.status == status)
        
        stmt = stmt.order_by(DocumentDefinition.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def create(
        self,
        document_def_id: str,
        prompt_header: dict,
        sections: list,
        document_schema_id: Optional[UUID] = None,
        created_by: Optional[str] = None,
        status: str = "draft",
    ) -> DocumentDefinition:
        """
        Create a new document definition.
        
        Args:
            document_def_id: Canonical definition ID with semver
            prompt_header: Role and constraints for prompt generation
            sections: Section definitions with component bindings
            document_schema_id: Optional UUID FK to schema_artifacts (nullable for MVP)
            created_by: Optional creator identifier
            status: Initial status (default: draft)
            
        Returns:
            Created DocumentDefinition
            
        Raises:
            InvalidDocDefIdError: If document_def_id format is invalid
            SchemaNotFoundError: If document_schema_id provided but doesn't exist
        """
        # Validate document_def_id format
        self._validate_docdef_id(document_def_id)
        
        # Verify schema exists if provided
        if document_schema_id:
            schema_stmt = select(SchemaArtifact).where(SchemaArtifact.id == document_schema_id)
            schema_result = await self.db.execute(schema_stmt)
            if not schema_result.scalar_one_or_none():
                raise SchemaNotFoundError(f"Schema artifact not found: {document_schema_id}")
        
        # Create document definition
        docdef = DocumentDefinition(
            document_def_id=document_def_id,
            document_schema_id=document_schema_id,
            prompt_header=prompt_header,
            sections=sections,
            status=status,
            created_by=created_by,
        )
        
        # If created as accepted, set accepted_at
        if status == "accepted":
            docdef.accepted_at = datetime.now(timezone.utc)
        
        self.db.add(docdef)
        await self.db.flush()
        await self.db.refresh(docdef)
        
        logger.info(f"Created document definition: {document_def_id} ({status})")
        return docdef
    
    async def accept(self, document_def_id: str) -> DocumentDefinition:
        """
        Accept a document definition (transition from draft to accepted).
        
        This is the only mutation permitted per D1.
        
        Args:
            document_def_id: Definition ID to accept
            
        Returns:
            Updated DocumentDefinition
            
        Raises:
            DocDefNotFoundError: If definition doesn't exist
            DocDefAlreadyAcceptedError: If already accepted
        """
        docdef = await self.get(document_def_id)
        
        if not docdef:
            raise DocDefNotFoundError(f"Document definition not found: {document_def_id}")
        
        if docdef.status == "accepted":
            raise DocDefAlreadyAcceptedError(
                f"Document definition already accepted: {document_def_id}"
            )
        
        docdef.status = "accepted"
        docdef.accepted_at = datetime.now(timezone.utc)
        
        await self.db.flush()
        await self.db.refresh(docdef)
        
        logger.info(f"Accepted document definition: {document_def_id}")
        return docdef
