"""create auth tables

Revision ID: 001_auth_tables
Revises: 
Create Date: 2024-12-23

ADR-008: Multi-Provider OAuth Authentication
Creates 6 tables for authentication system:
- users: Core user identity
- user_oauth_identities: OIDC provider linkages
- link_intent_nonces: Link-CSRF prevention
- user_sessions: Web sessions with CSRF tokens
- personal_access_tokens: API authentication
- auth_audit_log: Security event logging
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251223_001'
down_revision = '20251218_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all auth tables with indexes and constraints."""
    
    # 1. users - Core user identity
    op.create_table(
        'users',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('user_created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('user_updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_login_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint('email', name='users_email_unique')
    )
    
    # Indexes for users
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_active', 'users', ['is_active'], postgresql_where=sa.text('is_active = true'))
    
    # 2. user_oauth_identities - OIDC provider linkages
    op.create_table(
        'user_oauth_identities',
        sa.Column('identity_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider_id', sa.String(50), nullable=False),
        sa.Column('provider_user_id', sa.String(255), nullable=False),
        sa.Column('provider_email', sa.String(255), nullable=True),
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('provider_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('identity_created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_used_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('provider_id', 'provider_user_id', name='oauth_provider_user_unique')
    )
    
    # Indexes for user_oauth_identities
    op.create_index('idx_oauth_user_id', 'user_oauth_identities', ['user_id'])
    op.create_index('idx_oauth_provider', 'user_oauth_identities', ['provider_id'])
    
    # 3. link_intent_nonces - Prevents link-CSRF attacks
    op.create_table(
        'link_intent_nonces',
        sa.Column('nonce', sa.String(64), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider_id', sa.String(50), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE')
    )
    
    # Indexes for link_intent_nonces
    op.create_index('idx_link_nonces_expires', 'link_intent_nonces', ['expires_at'])
    op.create_index('idx_link_nonces_user', 'link_intent_nonces', ['user_id'])
    
    # 4. user_sessions - Web sessions with CSRF tokens
    op.create_table(
        'user_sessions',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_token', sa.String(255), nullable=False),
        sa.Column('csrf_token', sa.String(255), nullable=False),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('session_created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_activity_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('session_token', name='user_sessions_session_token_unique')
    )
    
    # Indexes for user_sessions
    op.create_index('idx_session_token', 'user_sessions', ['session_token'], unique=True)
    op.create_index('idx_session_user_id', 'user_sessions', ['user_id'])
    op.create_index('idx_session_expires', 'user_sessions', ['expires_at'])
    
    # 5. personal_access_tokens - API authentication
    op.create_table(
        'personal_access_tokens',
        sa.Column('token_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_name', sa.String(100), nullable=False),
        sa.Column('token_display', sa.String(50), nullable=False),
        sa.Column('key_id', sa.String(20), nullable=False),
        sa.Column('secret_hash', sa.String(64), nullable=False),
        sa.Column('last_used_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('token_created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE')
    )
    
    # Indexes for personal_access_tokens
    op.create_index('idx_pat_user', 'personal_access_tokens', ['user_id'])
    op.create_index('idx_pat_token_id', 'personal_access_tokens', ['token_id'])
    op.create_index('idx_pat_active', 'personal_access_tokens', ['is_active'], postgresql_where=sa.text('is_active = true'))
    
    # 6. auth_audit_log - Security event logging
    op.create_table(
        'auth_audit_log',
        sa.Column('log_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('provider_id', sa.String(50), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='SET NULL')
    )
    
    # Indexes for auth_audit_log
    op.create_index('idx_auth_log_user', 'auth_audit_log', ['user_id'])
    op.create_index('idx_auth_log_event', 'auth_audit_log', ['event_type'])
    op.create_index('idx_auth_log_created', 'auth_audit_log', [sa.text('created_at DESC')])


def downgrade() -> None:
    """Drop all auth tables in reverse order to respect foreign key constraints."""
    
    # Drop in reverse order (respects foreign keys)
    op.drop_table('auth_audit_log')
    op.drop_table('personal_access_tokens')
    op.drop_table('user_sessions')
    op.drop_table('link_intent_nonces')
    op.drop_table('user_oauth_identities')
    op.drop_table('users')