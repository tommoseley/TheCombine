"""Add acceptance fields for ADR-007 Sidebar Document Status

Adds acceptance workflow fields to support document sign-off:
- document_types: acceptance_required, accepted_by_role
- documents: accepted_at, accepted_by, rejected_at, rejected_by, rejection_reason

Revision ID: 20241218_001_add_acceptance_fields
Revises: create_documents_tables
Create Date: 2025-12-18
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '20241218_001'
down_revision: Union[str, None] = 'create_documents_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # DOCUMENT_TYPES TABLE - Add acceptance configuration
    # =========================================================================
    
    # acceptance_required: Does this document type need human sign-off?
    op.add_column(
        'document_types',
        sa.Column(
            'acceptance_required',
            sa.Boolean,
            nullable=False,
            server_default='false',
            comment='Whether this document type requires human acceptance before downstream use'
        )
    )
    
    # accepted_by_role: Which role is responsible for acceptance?
    op.add_column(
        'document_types',
        sa.Column(
            'accepted_by_role',
            sa.String(64),
            nullable=True,
            comment='Role that must accept this document type (pm, architect, etc.)'
        )
    )
    
    # =========================================================================
    # DOCUMENTS TABLE - Add acceptance state fields
    # =========================================================================
    
    # accepted_at: When was this document accepted?
    op.add_column(
        'documents',
        sa.Column(
            'accepted_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Timestamp when document was accepted'
        )
    )
    
    # accepted_by: Who accepted this document?
    op.add_column(
        'documents',
        sa.Column(
            'accepted_by',
            sa.String(200),
            nullable=True,
            comment='User ID or identifier who accepted the document'
        )
    )
    
    # rejected_at: When was this document rejected?
    op.add_column(
        'documents',
        sa.Column(
            'rejected_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Timestamp when document was rejected (most recent rejection)'
        )
    )
    
    # rejected_by: Who rejected this document?
    op.add_column(
        'documents',
        sa.Column(
            'rejected_by',
            sa.String(200),
            nullable=True,
            comment='User ID or identifier who rejected the document'
        )
    )
    
    # rejection_reason: Why was it rejected?
    op.add_column(
        'documents',
        sa.Column(
            'rejection_reason',
            sa.Text,
            nullable=True,
            comment='Human-provided reason for rejection'
        )
    )
    
    # =========================================================================
    # INDEXES for acceptance queries
    # =========================================================================
    
    # Index for finding documents needing acceptance
    op.create_index(
        'idx_documents_acceptance',
        'documents',
        ['accepted_at', 'rejected_at'],
        postgresql_where=sa.text('is_latest = true')
    )
    
    # Index for document_types that require acceptance
    op.create_index(
        'idx_document_types_acceptance_required',
        'document_types',
        ['acceptance_required'],
        postgresql_where=sa.text('acceptance_required = true')
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_document_types_acceptance_required', table_name='document_types')
    op.drop_index('idx_documents_acceptance', table_name='documents')
    
    # Drop document columns
    op.drop_column('documents', 'rejection_reason')
    op.drop_column('documents', 'rejected_by')
    op.drop_column('documents', 'rejected_at')
    op.drop_column('documents', 'accepted_by')
    op.drop_column('documents', 'accepted_at')
    
    # Drop document_types columns
    op.drop_column('document_types', 'accepted_by_role')
    op.drop_column('document_types', 'acceptance_required')