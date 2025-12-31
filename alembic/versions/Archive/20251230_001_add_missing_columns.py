"""add_missing_columns

Revision ID: 85757bbd7d90
Revises: 20251228_002
Create Date: 2025-12-30 15:54:00.632605

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251230_001'
down_revision: Union[str, Sequence[str], None] = '20251228_002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Get connection and inspector
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = {col['name'] for col in inspector.get_columns('projects')}
    
    # Add icon column if missing
    if 'icon' not in existing_columns:
        op.add_column('projects', 
            sa.Column('icon', sa.String(32), 
                     server_default='folder', 
                     nullable=True))
        print("✅ Added 'icon' column")
    else:
        print("⏭️  'icon' column already exists")
    
    # Add owner_id column if missing
    if 'owner_id' not in existing_columns:
        op.add_column('projects', 
            sa.Column('owner_id', postgresql.UUID(), nullable=True))
        op.create_index('ix_projects_owner_id', 'projects', ['owner_id'], unique=False)
        print("✅ Added 'owner_id' column")
    else:
        print("⏭️  'owner_id' column already exists")
    
    # Add organization_id column if missing
    if 'organization_id' not in existing_columns:
        op.add_column('projects', 
            sa.Column('organization_id', postgresql.UUID(), nullable=True))
        op.create_index('ix_projects_organization_id', 'projects', ['organization_id'], unique=False)
        print("✅ Added 'organization_id' column")
    else:
        print("⏭️  'organization_id' column already exists")
    
    # Ensure defaults are set (safe to run multiple times)
    op.alter_column('projects', 'id',
                    server_default=sa.text('uuid_generate_v4()'),
                    existing_type=postgresql.UUID(),
                    existing_nullable=False)
    
    op.alter_column('projects', 'status',
                    server_default='active',
                    existing_type=sa.String(50),
                    existing_nullable=True)
    
    op.alter_column('projects', 'metadata',
                    server_default='{}',
                    existing_type=postgresql.JSONB(),
                    existing_nullable=True)

def downgrade():
    # Only drop if exists
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = {col['name'] for col in inspector.get_columns('projects')}
    
    if 'organization_id' in existing_columns:
        op.drop_index('ix_projects_organization_id', table_name='projects')
        op.drop_column('projects', 'organization_id')
    
    if 'owner_id' in existing_columns:
        op.drop_index('ix_projects_owner_id', table_name='projects')
        op.drop_column('projects', 'owner_id')
    
    if 'icon' in existing_columns:
        op.drop_column('projects', 'icon')