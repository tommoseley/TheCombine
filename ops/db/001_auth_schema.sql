-- ADR-008: Multi-Provider OAuth Authentication
-- Database Schema - Auth Tables
-- 
-- This SQL file is for manual inspection only.
-- Use Alembic migration (001_create_auth_tables.py) for actual deployment.
--
-- Created: 2024-12-23
-- Revision: 001_auth_tables

BEGIN;

-- ============================================================================
-- 1. USERS - Core user identity
-- ============================================================================

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    email_verified BOOLEAN NOT NULL DEFAULT false,
    name VARCHAR(255) NOT NULL,
    avatar_url TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    user_created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT users_email_unique UNIQUE (email)
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = true;

COMMENT ON TABLE users IS 'Core user identity - one record per user regardless of OAuth providers';
COMMENT ON COLUMN users.email IS 'Primary email address - unique across system';
COMMENT ON COLUMN users.email_verified IS 'True if at least one linked provider has verified this email';
COMMENT ON COLUMN users.is_active IS 'False for soft-deleted users';
COMMENT ON COLUMN users.user_created_at IS 'First login timestamp';
COMMENT ON COLUMN users.last_login_at IS 'Most recent successful login';

-- ============================================================================
-- 2. USER_OAUTH_IDENTITIES - OIDC provider linkages
-- ============================================================================

CREATE TABLE user_oauth_identities (
    identity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    provider_id VARCHAR(50) NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    provider_email VARCHAR(255),
    email_verified BOOLEAN NOT NULL DEFAULT false,
    provider_metadata JSONB,
    identity_created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT oauth_provider_user_unique UNIQUE (provider_id, provider_user_id)
);

CREATE INDEX idx_oauth_user_id ON user_oauth_identities(user_id);
CREATE INDEX idx_oauth_provider ON user_oauth_identities(provider_id);

COMMENT ON TABLE user_oauth_identities IS 'Links users to OAuth providers - multiple identities per user allowed';
COMMENT ON COLUMN user_oauth_identities.provider_id IS 'OAuth provider: google, microsoft, etc.';
COMMENT ON COLUMN user_oauth_identities.provider_user_id IS 'Provider-specific user ID (sub claim)';
COMMENT ON COLUMN user_oauth_identities.provider_email IS 'Email from provider (may differ from users.email)';
COMMENT ON COLUMN user_oauth_identities.provider_metadata IS 'Minimal OIDC claims: {sub, email, name}';
COMMENT ON CONSTRAINT oauth_provider_user_unique ON user_oauth_identities IS 'One OAuth identity cannot link to multiple users';

-- ============================================================================
-- 3. LINK_INTENT_NONCES - Prevents link-CSRF attacks
-- ============================================================================

CREATE TABLE link_intent_nonces (
    nonce VARCHAR(64) PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    provider_id VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_link_nonces_expires ON link_intent_nonces(expires_at);
CREATE INDEX idx_link_nonces_user ON link_intent_nonces(user_id);

COMMENT ON TABLE link_intent_nonces IS 'One-time nonces for link-CSRF prevention - 10 minute lifetime';
COMMENT ON COLUMN link_intent_nonces.nonce IS '32-byte URL-safe nonce - stored in session + DB';
COMMENT ON COLUMN link_intent_nonces.expires_at IS 'Nonce valid for 10 minutes from creation';

-- ============================================================================
-- 4. USER_SESSIONS - Web sessions with CSRF tokens
-- ============================================================================

CREATE TABLE user_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    session_token VARCHAR(255) NOT NULL UNIQUE,
    csrf_token VARCHAR(255) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    session_created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE UNIQUE INDEX idx_session_token ON user_sessions(session_token);
CREATE INDEX idx_session_user_id ON user_sessions(user_id);
CREATE INDEX idx_session_expires ON user_sessions(expires_at);

COMMENT ON TABLE user_sessions IS 'Web sessions for cookie-based authentication - synchronizer token CSRF pattern';
COMMENT ON COLUMN user_sessions.session_token IS 'Stored in __Host-session cookie - 43-char URL-safe base64';
COMMENT ON COLUMN user_sessions.csrf_token IS 'Stored in __Host-csrf cookie (HttpOnly=false) - required for state-changing ops';
COMMENT ON COLUMN user_sessions.last_activity_at IS 'Updated with 15-minute write throttling to reduce DB load';
COMMENT ON COLUMN user_sessions.expires_at IS '30-day sliding expiration from last activity';

-- ============================================================================
-- 5. PERSONAL_ACCESS_TOKENS - API authentication
-- ============================================================================

CREATE TABLE personal_access_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_name VARCHAR(100) NOT NULL,
    token_display VARCHAR(50) NOT NULL,
    key_id VARCHAR(20) NOT NULL,
    secret_hash VARCHAR(64) NOT NULL,
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    token_created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT true
);

CREATE INDEX idx_pat_user ON personal_access_tokens(user_id);
CREATE INDEX idx_pat_token_id ON personal_access_tokens(token_id);
CREATE INDEX idx_pat_active ON personal_access_tokens(is_active) WHERE is_active = true;

COMMENT ON TABLE personal_access_tokens IS 'API tokens for programmatic access - versioned format with multi-key support';
COMMENT ON COLUMN personal_access_tokens.token_display IS 'First 20 chars of token for UI display: combine_pat_v1_key1_a1b2c3d4...';
COMMENT ON COLUMN personal_access_tokens.key_id IS 'Which server key was used for HMAC - enables key rotation';
COMMENT ON COLUMN personal_access_tokens.secret_hash IS 'HMAC-SHA256 hash of token secret - constant-time verified';
COMMENT ON COLUMN personal_access_tokens.is_active IS 'False when revoked - soft delete';

-- ============================================================================
-- 6. AUTH_AUDIT_LOG - Security event logging
-- ============================================================================

CREATE TABLE auth_audit_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    event_type VARCHAR(50) NOT NULL,
    provider_id VARCHAR(50),
    ip_address INET,
    user_agent TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_auth_log_user ON auth_audit_log(user_id);
CREATE INDEX idx_auth_log_event ON auth_audit_log(event_type);
CREATE INDEX idx_auth_log_created ON auth_audit_log(created_at DESC);

COMMENT ON TABLE auth_audit_log IS 'Security event logging with circuit breaker (1000 events/min max)';
COMMENT ON COLUMN auth_audit_log.event_type IS 'LOGIN_SUCCESS, CSRF_VIOLATION, PAT_CREATED, etc.';
COMMENT ON COLUMN auth_audit_log.ip_address IS 'Real client IP (respects TRUST_PROXY setting)';
COMMENT ON COLUMN auth_audit_log.metadata IS 'Event-specific details as JSON';

COMMIT;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- List all tables
-- \dt

-- Show table structure
-- \d users
-- \d user_oauth_identities
-- \d link_intent_nonces
-- \d user_sessions
-- \d personal_access_tokens
-- \d auth_audit_log

-- List all indexes
-- \di

-- Verify constraints
-- SELECT conname, contype FROM pg_constraint WHERE conrelid = 'users'::regclass;

-- Test timezone-aware columns
-- SELECT user_created_at FROM users WHERE false;
-- Should show: "timestamp with time zone"