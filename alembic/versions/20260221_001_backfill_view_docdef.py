"""Backfill view_docdef for implementation_plan and technical_architecture

Revision ID: 20260221_001
Revises: 20260216_006
Create Date: 2026-02-21

The original migration (20260112_001) only backfilled a subset of document
types. This migration adds view_docdef mappings that were missed:
- implementation_plan -> ImplementationPlanView
- technical_architecture -> ArchitecturalSummaryView
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260221_001"
down_revision = "20260216_006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE document_types
        SET view_docdef = 'ImplementationPlanView'
        WHERE doc_type_id = 'implementation_plan'
          AND (view_docdef IS NULL OR view_docdef = '')
    """)
    op.execute("""
        UPDATE document_types
        SET view_docdef = 'ArchitecturalSummaryView'
        WHERE doc_type_id = 'technical_architecture'
          AND (view_docdef IS NULL OR view_docdef = '')
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE document_types
        SET view_docdef = NULL
        WHERE doc_type_id IN ('implementation_plan', 'technical_architecture')
    """)
