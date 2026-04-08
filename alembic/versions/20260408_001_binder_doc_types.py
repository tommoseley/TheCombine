"""Add work_binder and work_plan document types

Revision ID: 20260408_001
Revises: 20260407_001
Create Date: 2026-04-08

ADR-071: Binder Management & Presentation. Registers work_binder and
work_plan document types for binder composition and final deliverable.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260408_001"
down_revision = "20260407_001"
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
            'work_binder',
            'Work Binder',
            'Composition document that references and organizes project documents with version-pinned links. Per ADR-071.',
            'composition',
            'book',
            '1.0.0',
            NULL,
            NULL,
            'work_binder',
            '[]'::jsonb,
            '[]'::jsonb,
            '{}'::jsonb,
            false,
            'single',
            'project',
            60,
            true,
            '1.0.0',
            'WB'
        )
    """)

    op.execute("""
        INSERT INTO document_types (
            id, doc_type_id, name, description, category, icon,
            schema_version, builder_role, builder_task, handler_id,
            required_inputs, optional_inputs, gating_rules,
            acceptance_required, cardinality,
            scope, display_order, is_active, version, display_prefix
        ) VALUES (
            gen_random_uuid(),
            'work_plan',
            'Work Plan',
            'Final binder artifact with executive summary, decision log, and dependency context. Read-only deliverable per ADR-071.',
            'deliverable',
            'clipboard-check',
            '1.0.0',
            NULL,
            NULL,
            'work_plan',
            '["work_binder"]'::jsonb,
            '["synthesis_delta"]'::jsonb,
            '{}'::jsonb,
            false,
            'single',
            'project',
            70,
            true,
            '1.0.0',
            'PLAN'
        )
    """)


def downgrade() -> None:
    op.execute("DELETE FROM document_types WHERE doc_type_id IN ('work_binder', 'work_plan')")
