"""Add owner_id and organization_id to projects (v2 - flexible)

Revision ID: 20251228_add_project_ownership_v2
Revises: 
Create Date: 2025-12-28 22:45:00

ADR: Project Ownership & Multi-Tenancy
- Add owner_id (UUID) for user ownership
- Add organization_id (UUID) for organization support
- Foreign key constraint skipped initially (add manually later)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251228_001'
down_revision = '20251223_001' # IMPORTANT: Update this to your latest migration ID
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add ownership columns to projects table."""
    
    # Add owner_id column
    op.add_column('projects',
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    
    # Add organization_id column
    op.add_column('projects',
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    
    # Add indexes for performance
    op.create_index(
        'ix_projects_owner_id',
        'projects',
        ['owner_id']
    )
    
    op.create_index(
        'ix_projects_organization_id',
        'projects',
        ['organization_id']
    )
    
    # Try to add foreign key, but don't fail if it doesn't work
    # This makes the migration more robust
    try:
        # Try with 'id' column first (most common)
        op.create_foreign_key(
            'fk_projects_owner_id',
            'projects',
            'users',
            ['owner_id'],
            ['id'],
            ondelete='SET NULL'
        )
    except Exception as e:
        # If that fails, print a message but continue
        print(f"Could not create foreign key with users.id: {e}")
        print("You may need to add the foreign key manually later")
        print("Run: SELECT column_name FROM information_schema.columns WHERE table_name = 'users';")
    
    # Data migration: Try to set owner_id from created_by if it's a valid UUID
    op.execute("""
        UPDATE projects 
        SET owner_id = created_by::uuid
        WHERE created_by IS NOT NULL 
        AND created_by ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    """)
    
    # For individual users: set organization_id = owner_id
    op.execute("""
        UPDATE projects 
        SET organization_id = owner_id
        WHERE owner_id IS NOT NULL
    """)


def downgrade() -> None:
    """Remove ownership columns from projects table."""
    
    # Remove indexes
    op.drop_index('ix_projects_organization_id', table_name='projects')
    op.drop_index('ix_projects_owner_id', table_name='projects')
    
    # Try to remove foreign key if it exists
    try:
        op.drop_constraint('fk_projects_owner_id', 'projects', type_='foreignkey')
    except Exception:
        pass  # Constraint might not exist, that's ok
    
    # Remove columns
    op.drop_column('projects', 'organization_id')
    op.drop_column('projects', 'owner_id')