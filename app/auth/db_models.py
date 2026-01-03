"""
SQLAlchemy ORM models for authentication tables.

ADR-008: Multi-Provider OAuth Authentication
These are the database-layer models that map to actual PostgreSQL tables.

Separate from app/auth/models.py (dataclasses) which are domain models.
"""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Text, Index, UniqueConstraint,
    Integer, TIMESTAMP
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, INET
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class UserORM(Base):
    """User table - core user identity."""
    __tablename__ = 'users'
    
    user_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(320), unique=True, nullable=False, index=True)
    email_verified = Column(Boolean, nullable=False, default=False)
    name = Column(String(256), nullable=False)
    avatar_url = Column(String(2048), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    user_created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    user_updated_at = Column(TIMESTAMP(timezone=True), nullable=False)
    last_login_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Relationships
    oauth_identities = relationship("UserOAuthIdentityORM", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSessionORM", back_populates="user", cascade="all, delete-orphan")
    tokens = relationship("PersonalAccessTokenORM", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_active', 'is_active', postgresql_where=Column('is_active') == True),
    )


class UserOAuthIdentityORM(Base):
    """OAuth identity linking table."""
    __tablename__ = 'user_oauth_identities'
    
    identity_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    provider_id = Column(String(32), nullable=False)
    provider_user_id = Column(String(256), nullable=False)
    provider_email = Column(String(320), nullable=True)
    email_verified = Column(Boolean, nullable=False, default=False)
    provider_metadata = Column('provider_metadata', JSONB, nullable=True)  # Map to avoid 'metadata' conflict
    identity_created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    last_used_at = Column(TIMESTAMP(timezone=True), nullable=False)
    
    # Relationships
    user = relationship("UserORM", back_populates="oauth_identities")
    
    __table_args__ = (
        UniqueConstraint('provider_id', 'provider_user_id', name='oauth_provider_user_unique'),
        Index('idx_oauth_user_id', 'user_id'),
        Index('idx_oauth_provider', 'provider_id', 'provider_user_id'),
    )


class LinkIntentNonceORM(Base):
    """Nonces for account linking flow."""
    __tablename__ = 'link_intent_nonces'
    
    nonce = Column(String(64), primary_key=True)  # Changed: nonce is the PK, not nonce_id
    user_id = Column(PGUUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    provider_id = Column(String(50), nullable=False)  # Changed: 50 to match DB
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    
    __table_args__ = (
        Index('idx_link_nonces_expires', 'expires_at'),
        Index('idx_link_nonces_user', 'user_id'),
    )


class UserSessionORM(Base):
    """Web sessions with CSRF tokens."""
    __tablename__ = 'user_sessions'
    
    session_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    session_token = Column(String(64), unique=True, nullable=False, index=True)
    csrf_token = Column(String(64), nullable=False)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    session_created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    last_activity_at = Column(TIMESTAMP(timezone=True), nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    
    # Relationships
    user = relationship("UserORM", back_populates="sessions")
    
    __table_args__ = (
        UniqueConstraint('session_token', name='user_sessions_session_token_unique'),
        Index('idx_session_token', 'session_token'),
        Index('idx_session_user_id', 'user_id'),
        Index('idx_session_expires', 'expires_at'),
    )


class PersonalAccessTokenORM(Base):
    """Personal Access Tokens for API authentication."""
    __tablename__ = 'personal_access_tokens'
    
    token_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    token_name = Column(String(128), nullable=False)
    token_hash = Column(String(128), nullable=False)
    token_display = Column(String(32), nullable=False)
    key_id = Column(String(16), nullable=False)
    last_used_at = Column(TIMESTAMP(timezone=True), nullable=True)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    token_created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    user = relationship("UserORM", back_populates="tokens")
    
    __table_args__ = (
        Index('idx_pat_user', 'user_id'),
        Index('idx_pat_token_id', 'token_id'),
        Index('idx_pat_active', 'is_active', postgresql_where=Column('is_active') == True),
    )


class AuthAuditLogORM(Base):
    """Authentication audit log."""
    __tablename__ = 'auth_audit_log'
    
    log_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True)
    event_type = Column(String(64), nullable=False)
    provider_id = Column(String(32), nullable=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    event_metadata = Column('metadata', JSONB, nullable=True)  # Map to 'metadata' column, use different attr name
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    
    __table_args__ = (
        Index('idx_auth_log_user', 'user_id'),
        Index('idx_auth_log_event', 'event_type'),
        Index('idx_auth_log_created', 'created_at'),
    )