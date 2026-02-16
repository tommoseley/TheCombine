"""Add plan_explanation document type

Revision ID: 20260216_005
Revises: 20260216_004
Create Date: 2026-02-16

Per WS-BCP-003.

Registers plan_explanation (single, LLM-generated) document type.
Human-readable explanation of mechanically derived execution plans.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260216_005"
down_revision = "20260216_004"
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
            'plan_explanation',
            'Plan Explanation',
            'LLM-generated explanation of a mechanically derived execution plan.',
            'planning',
            'message-square',
            '1.0.0',
            'project_manager',
            'plan_explanation',
            'plan_explanation',
            '["execution_plan"]'::jsonb,
            '[]'::jsonb,
            '{}'::jsonb,
            false,
            'single',
            NULL,
            'project',
            4,
            true,
            '1.0.0'
        )
    """)


def downgrade() -> None:
    op.execute("DELETE FROM document_types WHERE doc_type_id = 'plan_explanation'")
