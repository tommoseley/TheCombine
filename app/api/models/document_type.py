"""
DocumentType model for The Combine.

The document type registry - defines what documents the system can produce
and how they are built.
"""

from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class DocumentType(Base):
    """
    Document Type Registry - the heart of the document-centric architecture.
    
    Each row defines:
    - What a document IS (schema, category)
    - How it's BUILT (prompts, builder role/task)
    - What it NEEDS (required/optional inputs)
    - How it's HANDLED (handler_id maps to code)
    - Who must ACCEPT it (ADR-007 acceptance workflow)
    
    Adding a new document type is an INSERT, not a code change.
    """
    
    __tablename__ = "document_types"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Stable identifier - this is the public contract
    # e.g., 'project_discovery', 'architecture_spec', 'implementation_plan'
    doc_type_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Human-readable metadata
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=False, index=True)  # 'architecture', 'planning', 'development'
    icon = Column(String(50), nullable=True)  # lucide icon name
    
    # Schema reference (JSON schema for validation)
    # Can be inline JSONB or reference to external schema
    schema_definition = Column(JSONB, nullable=True)
    schema_version = Column(String(20), nullable=False, default="1.0")
    
    # Builder configuration - which prompts produce this document
    # References to role_tasks table for the actual prompts
    builder_role = Column(String(50), nullable=False)  # 'architect', 'pm', 'ba'
    builder_task = Column(String(100), nullable=False)  # 'discovery', 'implementation_plan'
    
    # Alternative: direct prompt references (if not using role_tasks)
    system_prompt_id = Column(UUID(as_uuid=True), ForeignKey("role_tasks.id"), nullable=True)
    
    # Handler configuration - which code class processes this document
    # Maps to a handler class in app/domain/handlers/
    handler_id = Column(String(100), nullable=False)  # 'project_discovery', 'architecture_spec'
    
    # Dependencies - what documents must exist before this can be built
    required_inputs = Column(JSONB, nullable=False, default=list)  # ["project_discovery"]
    optional_inputs = Column(JSONB, nullable=False, default=list)  # ["stakeholder_interviews"]
    
    # Gating rules - additional conditions beyond document existence
    # e.g., {"blocking_questions_answered": true}
    gating_rules = Column(JSONB, nullable=False, default=dict)
    
    # =========================================================================
    # ACCEPTANCE CONFIGURATION (ADR-007)
    # =========================================================================
    
    # Does this document type require human sign-off before downstream use?
    acceptance_required = Column(
        Boolean, 
        nullable=False, 
        default=False,
        doc="Whether this document type requires human acceptance before downstream use"
    )
    
    # Which role is responsible for acceptance? (pm, architect, tech_lead, etc.)
    accepted_by_role = Column(
        String(64), 
        nullable=True,
        doc="Role that must accept this document type (pm, architect, etc.)"
    )
    
    # =========================================================================
    # CARDINALITY (WS-INSTANCE-ID-001)
    # =========================================================================

    # 'single' = one latest per space, 'multi' = multiple instances per space
    cardinality = Column(
        String(20), nullable=False, default="single",
        doc="'single' = one latest per space, 'multi' = multiple instances per space"
    )

    # Content field name used as instance_id for multi-instance types (e.g., 'work_package_id')
    instance_key = Column(
        String(100), nullable=True,
        doc="Content field name used as instance_id for multi-instance types (e.g., 'work_package_id')"
    )

    # =========================================================================
    # SCOPE & DISPLAY
    # =========================================================================

    # Scope - where does this document appear?
    # 'project' = one per project, 'work_package' = one per work package
    scope = Column(String(50), nullable=False, default="project")
    
    # Display configuration
    display_order = Column(Integer, nullable=False, default=0)
    
    # ADR-034: Document definition ID for new viewer rendering
    # Maps to document_definitions.document_def_id (e.g., 'ImplementationPlanView')
    view_docdef = Column(String(100), nullable=True)

    # =========================================================================
    # PHASE 9: DATA-DRIVEN UX (WS-DOCUMENT-SYSTEM-CLEANUP)
    # =========================================================================

    # Status badges - configurable icons/colors per lifecycle state
    # e.g., {"missing": {"icon": "file-plus", "color": "gray"}, ...}
    status_badges = Column(JSONB, nullable=True)

    # Primary action (CTA) configuration
    # e.g., {"label": "Begin Research", "icon": "compass", "variant": "primary"}
    primary_action = Column(JSONB, nullable=True)

    # General display configuration (variants, visibility rules)
    display_config = Column(JSONB, nullable=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Versioning
    version = Column(String(20), nullable=False, default="1.0")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Audit
    created_by = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_document_types_category', 'category'),
        Index('idx_document_types_scope', 'scope'),
        Index('idx_document_types_active', 'is_active'),
        Index('idx_document_types_builder', 'builder_role', 'builder_task'),
        Index('idx_document_types_acceptance_required', 'acceptance_required',
              postgresql_where='acceptance_required = true'),
    )
    
    def __repr__(self):
        return f"<DocumentType(doc_type_id='{self.doc_type_id}', name='{self.name}')>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "doc_type_id": self.doc_type_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "icon": self.icon,
            "schema_definition": self.schema_definition,
            "schema_version": self.schema_version,
            "builder_role": self.builder_role,
            "builder_task": self.builder_task,
            "handler_id": self.handler_id,
            "required_inputs": self.required_inputs,
            "optional_inputs": self.optional_inputs,
            "gating_rules": self.gating_rules,
            "acceptance_required": self.acceptance_required,
            "accepted_by_role": self.accepted_by_role,
            "cardinality": self.cardinality,
            "instance_key": self.instance_key,
            "scope": self.scope,
            "display_order": self.display_order,
            "view_docdef": self.view_docdef,
            "status_badges": self.status_badges,
            "primary_action": self.primary_action,
            "display_config": self.display_config,
            "is_active": self.is_active,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }