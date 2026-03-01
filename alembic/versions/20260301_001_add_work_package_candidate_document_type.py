"""Add work_package_candidate document type

Revision ID: 20260301_001
Revises: 20260221_001
Create Date: 2026-03-01

Per WS-WB-009: Register the work_package_candidate document type.
Frozen lineage artifacts extracted from Implementation Plans.
Multi-instance, keyed by wpc_id.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260301_001"
down_revision = "20260221_001"
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
            'work_package_candidate',
            'Work Package Candidate',
            'Frozen lineage artifact extracted from an Implementation Plan. Immutable after creation. Persists as governance provenance, encoding what the IP actually proposed vs what was promoted to governed Work Packages.',
            'planning',
            'file-input',
            '1.0.0',
            'system',
            'extraction',
            'work_package_candidate',
            '["implementation_plan"]'::jsonb,
            '[]'::jsonb,
            '{}'::jsonb,
            false,
            'multi',
            'wpc_id',
            'project',
            37,
            true,
            '1.0.0'
        )
    """)


def downgrade() -> None:
    op.execute("DELETE FROM document_types WHERE doc_type_id = 'work_package_candidate'")
