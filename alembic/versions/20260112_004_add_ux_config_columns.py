"""Add UX config columns to document_types

Phase 9 (WS-DOCUMENT-SYSTEM-CLEANUP): Data-driven UX implementation.

Revision ID: 20260112_004
Revises: 20260112_003
Create Date: 2026-01-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '20260112_004'
down_revision = '20260112_003'
branch_labels = None
depends_on = None


# Default status badges configuration
DEFAULT_STATUS_BADGES = {
    "missing": {"icon": "file-plus", "color": "gray"},
    "generating": {"icon": "loader-2", "color": "blue", "animate": "spin"},
    "partial": {"icon": "file-clock", "color": "yellow"},
    "complete": {"icon": "file-check", "color": "green"},
    "stale": {"icon": "alert-triangle", "color": "amber"}
}


def upgrade() -> None:
    # Add status_badges JSONB column with default
    op.add_column(
        'document_types',
        sa.Column(
            'status_badges',
            JSONB,
            nullable=True,
            comment='State-specific badge configuration (icon, color, animate)'
        )
    )
    
    # Add primary_action JSONB column
    op.add_column(
        'document_types',
        sa.Column(
            'primary_action',
            JSONB,
            nullable=True,
            comment='CTA configuration (label, icon, variant, tooltip)'
        )
    )
    
    # Add display_config JSONB column for general display settings
    op.add_column(
        'document_types',
        sa.Column(
            'display_config',
            JSONB,
            nullable=True,
            comment='General display configuration (variants, visibility rules)'
        )
    )


def downgrade() -> None:
    op.drop_column('document_types', 'display_config')
    op.drop_column('document_types', 'primary_action')
    op.drop_column('document_types', 'status_badges')