"""Update project_discovery to require concierge_intake input.

Revision ID: 20260121_002
Revises: 20260121_001
Create Date: 2026-01-21

WS-INTAKE-SEP-003: PM Discovery workflow requires concierge_intake as input.
"""
from alembic import op

revision = '20260121_002'
down_revision = '20260121_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Set concierge_intake as required input for project_discovery."""
    op.execute("""
        UPDATE document_types 
        SET required_inputs = '["concierge_intake"]'::jsonb
        WHERE doc_type_id = 'project_discovery';
    """)


def downgrade() -> None:
    """Remove required input."""
    op.execute("""
        UPDATE document_types 
        SET required_inputs = '[]'::jsonb
        WHERE doc_type_id = 'project_discovery';
    """)