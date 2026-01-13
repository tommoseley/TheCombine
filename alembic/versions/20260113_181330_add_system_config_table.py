"""Add system_config table for data-driven environment settings.

Revision ID: add_system_config
Revises: 
Create Date: 2026-01-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid


# revision identifiers
revision = '20260113_001'
down_revision = '20260112_004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'system_config',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('key', sa.String(100), nullable=False, unique=True),
        sa.Column('value', sa.String(500), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Seed default values
    op.execute("""
        INSERT INTO system_config (id, key, value, description) VALUES
        (gen_random_uuid(), 'environment_name', 'Beta', 'Display name for environment (e.g., Beta, Development, Production)'),
        (gen_random_uuid(), 'version', 'v0.5', 'Current version string'),
        (gen_random_uuid(), 'environment_badge_color', 'amber', 'Badge color: amber, green, blue, red, gray')
    """)


def downgrade() -> None:
    op.drop_table('system_config')