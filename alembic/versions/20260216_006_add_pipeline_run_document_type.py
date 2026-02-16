"""Add pipeline_run document type

Revision ID: 20260216_006
Revises: 20260216_005
Create Date: 2026-02-16

Per WS-BCP-004 Phase 3.

Registers pipeline_run (multi-instance, keyed by run_id) document type
for storing BCP pipeline run metadata and replay hashes.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260216_006"
down_revision = "20260216_005"
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
            'pipeline_run',
            'Pipeline Run',
            'Metadata record for a Backlog Compilation Pipeline run with replay hashes.',
            'observability',
            'activity',
            '1.0.0',
            NULL,
            NULL,
            'pipeline_run',
            '[]'::jsonb,
            '[]'::jsonb,
            '{}'::jsonb,
            false,
            'multi',
            'run_id',
            'project',
            10,
            true,
            '1.0.0'
        )
    """)


def downgrade() -> None:
    op.execute("DELETE FROM document_types WHERE doc_type_id = 'pipeline_run'")
