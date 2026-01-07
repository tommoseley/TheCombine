"""
Fragment Registry Service for ADR-032.

Provides CRUD operations and binding management for fragment artifacts.
"""

import hashlib
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.fragment_artifact import FragmentArtifact, FragmentBinding


class FragmentNotFoundError(Exception):
    """Raised when a fragment artifact is not found."""
    pass


class BindingNotFoundError(Exception):
    """Raised when a fragment binding is not found."""
    pass


class InvalidStatusTransitionError(Exception):
    """Raised when an invalid status transition is attempted."""
    pass


class FragmentRegistryService:
    """
    Service for managing fragment artifacts and bindings.
    
    Per ADR-032:
    - Fragments render one instance of a canonical schema type
    - Only one active binding per schema_type_id
    - Fragments are versioned and auditable
    """
    
    # Valid status transitions
    VALID_TRANSITIONS = {
        "draft": {"accepted", "deprecated"},
        "accepted": {"deprecated"},
        "deprecated": set(),  # Terminal state
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # =========================================================================
    # Fragment Artifact Operations
    # =========================================================================
    
    async def create_fragment(
        self,
        fragment_id: str,
        schema_type_id: str,
        fragment_markup: str,
        version: str = "1.0",
        status: str = "draft",
        created_by: Optional[str] = None,
    ) -> FragmentArtifact:
        """
        Create a new fragment artifact.
        
        Args:
            fragment_id: Fragment identifier (e.g., "OpenQuestionV1Fragment")
            schema_type_id: Canonical schema type this renders
            fragment_markup: HTML/Jinja2 template content
            version: Version string (default "1.0")
            status: Initial status (default "draft")
            created_by: Optional creator identifier
            
        Returns:
            The created FragmentArtifact
        """
        sha256 = self.compute_hash(fragment_markup)
        
        artifact = FragmentArtifact(
            fragment_id=fragment_id,
            version=version,
            schema_type_id=schema_type_id,
            status=status,
            fragment_markup=fragment_markup,
            sha256=sha256,
            created_by=created_by,
        )
        
        self.db.add(artifact)
        await self.db.commit()
        await self.db.refresh(artifact)
        
        return artifact
    
    async def get_fragment(
        self,
        fragment_id: str,
        version: Optional[str] = None,
    ) -> Optional[FragmentArtifact]:
        """
        Get a fragment artifact by ID and optional version.
        
        If version is None, returns the latest accepted version.
        """
        if version:
            query = select(FragmentArtifact).where(
                and_(
                    FragmentArtifact.fragment_id == fragment_id,
                    FragmentArtifact.version == version,
                )
            )
        else:
            query = (
                select(FragmentArtifact)
                .where(
                    and_(
                        FragmentArtifact.fragment_id == fragment_id,
                        FragmentArtifact.status == "accepted",
                    )
                )
                .order_by(FragmentArtifact.created_at.desc())
                .limit(1)
            )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_active_fragment_for_type(
        self,
        schema_type_id: str,
    ) -> Optional[FragmentArtifact]:
        """
        Get the active fragment for a schema type via binding lookup.
        
        Args:
            schema_type_id: The canonical schema type
            
        Returns:
            FragmentArtifact or None if no active binding
        """
        # Find active binding
        binding_query = select(FragmentBinding).where(
            and_(
                FragmentBinding.schema_type_id == schema_type_id,
                FragmentBinding.is_active == True,
            )
        )
        
        result = await self.db.execute(binding_query)
        binding = result.scalar_one_or_none()
        
        if not binding:
            return None
        
        # Get the bound fragment
        return await self.get_fragment(binding.fragment_id, binding.fragment_version)
    
    async def set_status(
        self,
        fragment_id: str,
        version: str,
        new_status: str,
    ) -> FragmentArtifact:
        """
        Update the status of a fragment artifact.
        
        Valid transitions:
        - draft -> accepted
        - draft -> deprecated
        - accepted -> deprecated
        """
        artifact = await self.get_fragment(fragment_id, version)
        
        if not artifact:
            raise FragmentNotFoundError(
                f"Fragment '{fragment_id}' version '{version}' not found"
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
    
    async def list_fragments_for_type(
        self,
        schema_type_id: str,
        status: Optional[str] = None,
    ) -> List[FragmentArtifact]:
        """List all fragments for a schema type."""
        conditions = [FragmentArtifact.schema_type_id == schema_type_id]
        
        if status:
            conditions.append(FragmentArtifact.status == status)
        
        query = (
            select(FragmentArtifact)
            .where(and_(*conditions))
            .order_by(FragmentArtifact.fragment_id, FragmentArtifact.version)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    # =========================================================================
    # Binding Operations
    # =========================================================================
    
    async def create_binding(
        self,
        schema_type_id: str,
        fragment_id: str,
        fragment_version: str,
        created_by: Optional[str] = None,
    ) -> FragmentBinding:
        """
        Create a new fragment binding (inactive by default).
        """
        binding = FragmentBinding(
            schema_type_id=schema_type_id,
            fragment_id=fragment_id,
            fragment_version=fragment_version,
            is_active=False,
            created_by=created_by,
        )
        
        self.db.add(binding)
        await self.db.commit()
        await self.db.refresh(binding)
        
        return binding
    
    async def activate_binding(
        self,
        schema_type_id: str,
        fragment_id: str,
        fragment_version: str,
    ) -> FragmentBinding:
        """
        Activate a binding, deactivating any existing active binding for the type.
        
        Args:
            schema_type_id: The schema type
            fragment_id: The fragment to bind
            fragment_version: The fragment version
            
        Returns:
            The activated binding
        """
        # Deactivate any existing active binding for this type
        deactivate_stmt = (
            update(FragmentBinding)
            .where(
                and_(
                    FragmentBinding.schema_type_id == schema_type_id,
                    FragmentBinding.is_active == True,
                )
            )
            .values(is_active=False)
        )
        await self.db.execute(deactivate_stmt)
        
        # Find or create the target binding
        query = select(FragmentBinding).where(
            and_(
                FragmentBinding.schema_type_id == schema_type_id,
                FragmentBinding.fragment_id == fragment_id,
                FragmentBinding.fragment_version == fragment_version,
            )
        )
        result = await self.db.execute(query)
        binding = result.scalar_one_or_none()
        
        if not binding:
            # Create new binding
            binding = FragmentBinding(
                schema_type_id=schema_type_id,
                fragment_id=fragment_id,
                fragment_version=fragment_version,
                is_active=True,
            )
            self.db.add(binding)
        else:
            # Activate existing binding
            binding.is_active = True
        
        await self.db.commit()
        await self.db.refresh(binding)
        
        return binding
    
    async def get_active_binding(
        self,
        schema_type_id: str,
    ) -> Optional[FragmentBinding]:
        """Get the active binding for a schema type."""
        query = select(FragmentBinding).where(
            and_(
                FragmentBinding.schema_type_id == schema_type_id,
                FragmentBinding.is_active == True,
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    # =========================================================================
    # Utilities
    # =========================================================================
    
    @staticmethod
    def compute_hash(markup: str) -> str:
        """
        Compute deterministic SHA256 hash of fragment markup.
        """
        return hashlib.sha256(markup.encode('utf-8')).hexdigest()