"""Add synthesis_delta document type

Revision ID: 20260407_001
Revises: 20260402_001
Create Date: 2026-04-07

ADR-070: Binder Synthesis. Registers synthesis_delta document type
for post-binder composition analysis output.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260407_001"
down_revision = "20260402_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO document_types (
            id, doc_type_id, name, description, category, icon,
            schema_version, builder_role, builder_task, handler_id,
            required_inputs, optional_inputs, gating_rules,
            acceptance_required, cardinality,
            scope, display_order, is_active, version, display_prefix
        ) VALUES (
            gen_random_uuid(),
            'synthesis_delta',
            'Synthesis Delta',
            'Post-binder composition analysis. Contains mechanical actions and judgment questions from dual-instance review. Per ADR-070.',
            'quality',
            'filter',
            '1.0.0',
            'quality_assurance',
            'binder_synthesis',
            'synthesis_delta',
            '["binder_content"]'::jsonb,
            '[]'::jsonb,
            '{}'::jsonb,
            false,
            'single',
            'project',
            50,
            true,
            '1.0.0',
            'SD'
        )
    """)


def downgrade() -> None:
    op.execute("DELETE FROM document_types WHERE doc_type_id = 'synthesis_delta'")
