"""Add execution_plan document type

Revision ID: 20260216_004
Revises: 20260216_003
Create Date: 2026-02-16

Per WS-BCP-002 Phase 3.

Registers execution_plan (single, constructed) document type for the
Backlog Compilation Pipeline. Mechanically derived, never LLM-authored.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260216_004"
down_revision = "20260216_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO document_types (
            id, doc_type_id, name, description, category, icon,
            schema_version, builder_role, builder_task, handler_id,
            required_inputs, optional_inputs, gating_rules,
            acceptance_required, cardinality, instance_key,
            scope, display_order, is_active, version
        ) VALUES (
            gen_random_uuid(),
            'execution_plan',
            'Execution Plan',
            'Deterministically derived execution plan. Mechanically produced, never LLM-authored.',
            'planning',
            'route',
            '1.0.0',
            NULL,
            NULL,
            'execution_plan',
            '["backlog_item"]'::jsonb,
            '[]'::jsonb,
            '{}'::jsonb,
            false,
            'single',
            NULL,
            'project',
            3,
            true,
            '1.0.0'
        )
    """)


def downgrade() -> None:
    op.execute("DELETE FROM document_types WHERE doc_type_id = 'execution_plan'")
