"""Add view_docdef column to document_types

Revision ID: 20260112_001
Revises: 20260110_001
Create Date: 2026-01-12

Phase 1 of WS-DOCUMENT-SYSTEM-CLEANUP:
Adds view_docdef column to document_types table so the document viewer
can resolve docdefs from DB instead of hardcoded DOCUMENT_CONFIG.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260112_001'
down_revision = '20260110_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add view_docdef column - stores the document definition ID used for rendering
    # e.g., 'EpicBacklogView', 'ProjectDiscovery', 'StoryBacklogView'
    op.add_column(
        'document_types',
        sa.Column('view_docdef', sa.String(100), nullable=True,
                  comment='Document definition ID for rendering (e.g., EpicBacklogView)')
    )
    
    # Backfill existing document types with their view_docdef values
    # These values match the hardcoded DOCUMENT_CONFIG being eliminated
    op.execute("""
        UPDATE document_types 
        SET view_docdef = CASE doc_type_id
            WHEN 'project_discovery' THEN 'ProjectDiscovery'
            WHEN 'epic_backlog' THEN 'EpicBacklogView'
            WHEN 'technical_architecture' THEN 'ArchitecturalSummaryView'
            WHEN 'story_backlog' THEN 'StoryBacklogView'
            WHEN 'architecture_spec' THEN 'ArchitecturalSummaryView'
            ELSE NULL
        END
        WHERE view_docdef IS NULL
    """)


def downgrade() -> None:
    op.drop_column('document_types', 'view_docdef')