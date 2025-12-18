"""create document_types table

Revision ID: 20241217_001
Revises: <previous_revision>
Create Date: 2024-12-17

The document_types table is the heart of the document-centric architecture.
It defines what documents the system can produce and how they are built.

Adding a new document type is an INSERT, not a code change.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20241217_001'
down_revision = None  # UPDATE THIS to your actual previous revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create document_types table
    op.create_table(
        'document_types',
        
        # Primary key
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, 
                  server_default=sa.text('gen_random_uuid()')),
        
        # Stable identifier - the public contract
        sa.Column('doc_type_id', sa.String(100), unique=True, nullable=False, index=True),
        
        # Human-readable metadata
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('category', sa.String(100), nullable=False, index=True),
        sa.Column('icon', sa.String(50), nullable=True),
        
        # Schema
        sa.Column('schema_definition', postgresql.JSONB, nullable=True),
        sa.Column('schema_version', sa.String(20), nullable=False, server_default='1.0'),
        
        # Builder configuration
        sa.Column('builder_role', sa.String(50), nullable=False),
        sa.Column('builder_task', sa.String(100), nullable=False),
        sa.Column('system_prompt_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Handler
        sa.Column('handler_id', sa.String(100), nullable=False),
        
        # Dependencies
        sa.Column('required_inputs', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('optional_inputs', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('gating_rules', postgresql.JSONB, nullable=False, server_default='{}'),
        
        # Scope
        sa.Column('scope', sa.String(50), nullable=False, server_default='project'),
        
        # Display
        sa.Column('display_order', sa.Integer, nullable=False, server_default='0'),
        
        # Status
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        
        # Version
        sa.Column('version', sa.String(20), nullable=False, server_default='1.0'),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('NOW()'), nullable=False),
        
        # Audit
        sa.Column('created_by', sa.String(200), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
    )
    
    # Create indexes
    op.create_index('idx_document_types_category', 'document_types', ['category'])
    op.create_index('idx_document_types_scope', 'document_types', ['scope'])
    op.create_index('idx_document_types_active', 'document_types', ['is_active'])
    op.create_index('idx_document_types_builder', 'document_types', ['builder_role', 'builder_task'])
    
    # Create GIN index for JSONB queries on dependencies
    op.create_index(
        'idx_document_types_required_inputs', 
        'document_types', 
        ['required_inputs'],
        postgresql_using='gin'
    )
    
    # Add foreign key to role_tasks if it exists
    # Uncomment if you want the FK constraint:
    # op.create_foreign_key(
    #     'fk_document_types_system_prompt',
    #     'document_types',
    #     'role_tasks',
    #     ['system_prompt_id'],
    #     ['id'],
    #     ondelete='SET NULL'
    # )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_document_types_required_inputs', table_name='document_types')
    op.drop_index('idx_document_types_builder', table_name='document_types')
    op.drop_index('idx_document_types_active', table_name='document_types')
    op.drop_index('idx_document_types_scope', table_name='document_types')
    op.drop_index('idx_document_types_category', table_name='document_types')
    
    # Drop table
    op.drop_table('document_types')