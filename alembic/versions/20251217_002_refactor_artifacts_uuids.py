"""Refactor artifacts table to use UUID foreign keys

Drop artifact_path and RSP-1 constraints.
Use proper UUID foreign keys to projects and epics.

Revision ID: refactor_artifacts_uuids
Revises: <your_previous_revision>
Create Date: 2025-12-17
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '20251217_002'
down_revision: Union[str, None] = '20251217_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop all the RSP-1 format constraints (if not already dropped)
    # These may fail if already dropped - that's fine
    try:
        op.drop_constraint('artifacts_path_format', 'artifacts', type_='check')
    except:
        pass
    
    try:
        op.drop_constraint('artifacts_project_id_format', 'artifacts', type_='check')
    except:
        pass
    
    try:
        op.drop_constraint('artifacts_epic_id_format', 'artifacts', type_='check')
    except:
        pass
    
    try:
        op.drop_constraint('artifacts_feature_id_format', 'artifacts', type_='check')
    except:
        pass
    
    try:
        op.drop_constraint('artifacts_story_id_format', 'artifacts', type_='check')
    except:
        pass

    # 2. Drop columns we no longer need
    op.drop_column('artifacts', 'artifact_path')
    op.drop_column('artifacts', 'feature_id')
    op.drop_column('artifacts', 'story_id')
    op.drop_column('artifacts', 'parent_path')
    
    # 3. Alter project_id from VARCHAR to UUID
    # First drop any existing data (dev only!)
    op.execute('TRUNCATE TABLE artifacts')
    
    # Change column type
    op.alter_column(
        'artifacts',
        'project_id',
        existing_type=sa.VARCHAR(8),
        type_=postgresql.UUID(as_uuid=True),
        existing_nullable=False,
        postgresql_using='NULL'  # Will be set properly after
    )
    
    # 4. Alter epic_id from VARCHAR to UUID
    op.alter_column(
        'artifacts',
        'epic_id',
        existing_type=sa.VARCHAR(8),
        type_=postgresql.UUID(as_uuid=True),
        existing_nullable=True,
        postgresql_using='NULL'
    )
    
    # 5. Add foreign key constraints
    op.create_foreign_key(
        'fk_artifacts_project',
        'artifacts',
        'projects',
        ['project_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Note: Only add epic FK if you have an epics table
    # op.create_foreign_key(
    #     'fk_artifacts_epic',
    #     'artifacts',
    #     'epics',
    #     ['epic_id'],
    #     ['id'],
    #     ondelete='CASCADE'
    # )
    
    # 6. Add unique constraint for project + artifact_type (for project-scoped docs)
    # This prevents duplicate project_discovery docs for the same project
    op.create_index(
        'ix_artifacts_project_type',
        'artifacts',
        ['project_id', 'artifact_type', 'epic_id'],
        unique=False  # Set to True if you want uniqueness
    )


def downgrade() -> None:
    # Remove new constraints
    op.drop_index('ix_artifacts_project_type', 'artifacts')
    op.drop_constraint('fk_artifacts_project', 'artifacts', type_='foreignkey')
    
    # Revert column types (will lose data)
    op.alter_column(
        'artifacts',
        'project_id',
        existing_type=postgresql.UUID(as_uuid=True),
        type_=sa.VARCHAR(8),
        existing_nullable=False
    )
    
    op.alter_column(
        'artifacts',
        'epic_id',
        existing_type=postgresql.UUID(as_uuid=True),
        type_=sa.VARCHAR(8),
        existing_nullable=True
    )
    
    # Re-add dropped columns
    op.add_column('artifacts', sa.Column('artifact_path', sa.VARCHAR(100), nullable=True))
    op.add_column('artifacts', sa.Column('feature_id', sa.VARCHAR(8), nullable=True))
    op.add_column('artifacts', sa.Column('story_id', sa.VARCHAR(8), nullable=True))
    op.add_column('artifacts', sa.Column('parent_path', sa.VARCHAR(100), nullable=True))