"""Backfill project_audit with CREATED events

Revision ID: 003_backfill_audit
Revises: 002_create_audit
Create Date: 2025-01-01 11:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20251231_003'
down_revision = '20251231_002'
branch_labels = None
depends_on = None


def upgrade():
    # Backfill CREATED events for existing projects
    # Uses CASE to handle created_by that might not be valid UUIDs
    op.execute("""
        INSERT INTO project_audit (project_id, actor_user_id, action, metadata, created_at)
        SELECT 
            id AS project_id,
            CASE 
                WHEN created_by ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' 
                THEN created_by::uuid 
                ELSE NULL 
            END AS actor_user_id,
            'CREATED' AS action,
            jsonb_build_object(
                'meta_version', '1.0',
                'client', 'migration',
                'backfill', true,
                'after', jsonb_build_object(
                    'name', name,
                    'project_id', project_id,
                    'icon', icon
                )
            ) AS metadata,
            created_at
        FROM projects
        WHERE NOT EXISTS (
            SELECT 1 FROM project_audit pa 
            WHERE pa.project_id = projects.id 
            AND pa.action = 'CREATED'
        )
    """)


def downgrade():
    # Remove backfilled entries
    op.execute("""
        DELETE FROM project_audit 
        WHERE metadata->>'backfill' = 'true'
    """)