"""
Authentication service.

ADR-008: Multi-Provider OAuth Authentication
Business logic for session management, user creation, and audit logging.

Stage 3A: Sessions + Audit only (Link nonces and PATs deferred to later stages)
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from uuid import UUID
from collections import deque
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert, delete, func
from sqlalchemy.exc import IntegrityError

from auth.models import User, UserSession, AuthEventType
from auth.utils import utcnow
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """
    Authentication service for user and session management.
    
    Handles:
    - Session creation and verification (with write throttling)
    - User creation from OIDC claims
    - Audit event logging (with circuit breaker)
    
    Future: Link nonces, PATs (Stage 3B)
    """
    
    # Circuit breaker for audit logging: max 1000 events per minute
    _audit_log_window = deque(maxlen=1000)
    _audit_log_window_start: Optional[datetime] = None
    
    def __init__(self, db: AsyncSession):
        """
        Initialize auth service.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================
    
    async def create_session(
        self,
        user_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        expires_in_days: int = 30
    ) -> UserSession:
        """
        Create new web session with CSRF token.
        
        Generates cryptographically secure session_token and csrf_token.
        Both are 43-character URL-safe base64 strings (32 random bytes).
        
        Args:
            user_id: User UUID
            ip_address: Client IP address
            user_agent: User agent string
            expires_in_days: Session expiration in days (default 30)
            
        Returns:
            UserSession object with session_token and csrf_token
        """
        now = utcnow()
        expires_at = now + timedelta(days=expires_in_days)
        
        # Generate secure tokens (32 bytes = 43 chars in URL-safe base64)
        session_token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        
        # Insert session into database
        query = insert(UserSession.__table__).values(
            user_id=user_id,
            session_token=session_token,
            csrf_token=csrf_token,
            ip_address=ip_address,
            user_agent=user_agent,
            session_created_at=now,
            last_activity_at=now,
            expires_at=expires_at
        ).returning(UserSession.__table__)
        
        result = await self.db.execute(query)
        await self.db.commit()
        
        row = result.fetchone()
        
        session = UserSession(
            session_id=row.session_id,
            user_id=row.user_id,
            session_token=row.session_token,
            csrf_token=row.csrf_token,
            ip_address=row.ip_address,
            user_agent=row.user_agent,
            session_created_at=row.session_created_at,
            last_activity_at=row.last_activity_at,
            expires_at=row.expires_at
        )
        
        logger.info(f"Created session {session.session_id} for user {user_id}")
        return session
    
    async def verify_session(
        self,
        session_token: str
    ) -> Optional[Tuple[User, UUID, str]]:
        """
        Verify session token and return user + session info.
        
        CRITICAL: Implements write throttling to reduce DB load.
        Only updates last_activity_at if >15 minutes since last update.
        This reduces writes by ~90% under HTMX load.
        
        Args:
            session_token: Session token from cookie
            
        Returns:
            Tuple of (User, session_id, csrf_token) if valid, None if invalid/expired
        """
        now = utcnow()
        
        # Query with explicit column selection (prevents collisions)
        # Join users table to get user details in one query
        from sqlalchemy.orm import aliased
        
        UserTable = aliased(User.__table__, name='u')
        SessionTable = aliased(UserSession.__table__, name='s')
        
        query = select(
            UserTable.c.user_id,
            UserTable.c.email,
            UserTable.c.email_verified,
            UserTable.c.name,
            UserTable.c.avatar_url,
            UserTable.c.is_active,
            UserTable.c.user_created_at,
            UserTable.c.user_updated_at,
            UserTable.c.last_login_at,
            SessionTable.c.session_id,
            SessionTable.c.csrf_token,
            SessionTable.c.last_activity_at,
            SessionTable.c.expires_at
        ).select_from(
            SessionTable.join(UserTable, SessionTable.c.user_id == UserTable.c.user_id)
        ).where(
            SessionTable.c.session_token == session_token
        )
        
        result = await self.db.execute(query)
        row = result.fetchone()
        
        if not row:
            return None
        
        # Check expiration
        if row.expires_at < now:
            logger.info(f"Session {row.session_id} expired")
            return None
        
        # Check if user is active
        if not row.is_active:
            logger.warning(f"Inactive user {row.user_id} attempted session use")
            return None
        
        # Write throttling: only update last_activity_at if >15 minutes
        should_update = (now - row.last_activity_at) > timedelta(minutes=15)
        
        if should_update:
            update_query = update(UserSession.__table__).where(
                UserSession.__table__.c.session_id == row.session_id
            ).values(
                last_activity_at=now
            )
            await self.db.execute(update_query)
            await self.db.commit()
            logger.debug(f"Updated last_activity_at for session {row.session_id}")
        
        # Construct User object
        user = User(
            user_id=row.user_id,
            email=row.email,
            email_verified=row.email_verified,
            name=row.name,
            avatar_url=row.avatar_url,
            is_active=row.is_active,
            user_created_at=row.user_created_at,
            user_updated_at=row.user_updated_at,
            last_login_at=row.last_login_at
        )
        
        return (user, row.session_id, row.csrf_token)
    
    async def delete_session(self, session_token: str) -> bool:
        """
        Delete session (logout).
        
        Args:
            session_token: Session token to delete
            
        Returns:
            True if session was deleted, False if not found
        """
        query = delete(UserSession.__table__).where(
            UserSession.__table__.c.session_token == session_token
        )
        result = await self.db.execute(query)
        await self.db.commit()
        
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"Deleted session with token {session_token[:10]}...")
        return deleted
    
    # ========================================================================
    # USER MANAGEMENT
    # ========================================================================
    
    async def get_or_create_user_from_oidc(
        self,
        provider_id: str,
        provider_user_id: str,
        claims: Dict[str, Any]
    ) -> Tuple[User, bool]:
        """
        Get existing user or create new user from OIDC claims.
        
        Email collision handling (prevents account takeover):
        - If email exists with verified match: Block auto-link, require user to login first
        - If email exists with unverified match: Block auto-link, show error
        - If email doesn't exist: Create new user
        
        Args:
            provider_id: OAuth provider ('google', 'microsoft')
            provider_user_id: Provider's user ID (sub claim)
            claims: Normalized claims dict with: sub, email, email_verified, name, picture
            
        Returns:
            Tuple of (User, created: bool)
            
        Raises:
            ValueError: If email collision detected (security protection)
        """
        email = claims['email']
        email_verified = claims.get('email_verified', False)
        name = claims.get('name', '')
        avatar_url = claims.get('picture')
        
        # Check if this OAuth identity already exists
        from sqlalchemy.orm import aliased
        OAuthTable = aliased(User.__table__.metadata.tables['user_oauth_identities'], name='oauth')
        UserTable = aliased(User.__table__, name='u')
        
        oauth_query = select(
            UserTable.c.user_id,
            UserTable.c.email,
            UserTable.c.email_verified,
            UserTable.c.name,
            UserTable.c.avatar_url,
            UserTable.c.is_active,
            UserTable.c.user_created_at,
            UserTable.c.user_updated_at,
            UserTable.c.last_login_at
        ).select_from(
            OAuthTable.join(UserTable, OAuthTable.c.user_id == UserTable.c.user_id)
        ).where(
            OAuthTable.c.provider_id == provider_id,
            OAuthTable.c.provider_user_id == provider_user_id
        )
        
        result = await self.db.execute(oauth_query)
        existing_row = result.fetchone()
        
        if existing_row:
            # User exists - update last_login_at
            now = utcnow()
            update_query = update(User.__table__).where(
                User.__table__.c.user_id == existing_row.user_id
            ).values(
                last_login_at=now
            )
            await self.db.execute(update_query)
            await self.db.commit()
            
            user = User(
                user_id=existing_row.user_id,
                email=existing_row.email,
                email_verified=existing_row.email_verified,
                name=existing_row.name,
                avatar_url=existing_row.avatar_url,
                is_active=existing_row.is_active,
                user_created_at=existing_row.user_created_at,
                user_updated_at=existing_row.user_updated_at,
                last_login_at=now
            )
            
            logger.info(f"Existing user {user.user_id} logged in via {provider_id}")
            return (user, False)
        
        # Check for email collision (security-critical)
        email_query = select(User.__table__.c.user_id, User.__table__.c.email_verified).where(
            User.__table__.c.email == email
        )
        email_result = await self.db.execute(email_query)
        email_row = email_result.fetchone()
        
        if email_row:
            # Email exists - this is an account takeover attempt or needs explicit linking
            if email_row.email_verified:
                logger.warning(
                    f"Email collision: {email} exists (verified). "
                    f"User must login with existing provider first to link {provider_id}"
                )
                raise ValueError(
                    f"An account with email {email} already exists. "
                    f"Please sign in with your existing provider first, "
                    f"then link {provider_id} from your account settings."
                )
            else:
                logger.warning(
                    f"Email collision: {email} exists (unverified). "
                    f"User must verify existing account first."
                )
                raise ValueError(
                    f"An account with email {email} already exists but is not verified. "
                    f"Please verify your existing account first."
                )
        
        # Create new user
        now = utcnow()
        insert_user_query = insert(User.__table__).values(
            email=email,
            email_verified=email_verified,
            name=name,
            avatar_url=avatar_url,
            is_active=True,
            user_created_at=now,
            user_updated_at=now,
            last_login_at=now
        ).returning(User.__table__.c.user_id)
        
        result = await self.db.execute(insert_user_query)
        user_id = result.fetchone()[0]
        
        # Create OAuth identity
        OAuthIdentityTable = User.__table__.metadata.tables['user_oauth_identities']
        insert_oauth_query = insert(OAuthIdentityTable).values(
            user_id=user_id,
            provider_id=provider_id,
            provider_user_id=provider_user_id,
            provider_email=email,
            email_verified=email_verified,
            provider_metadata={
                'sub': claims['sub'],
                'email': email,
                'name': name
            },
            identity_created_at=now,
            last_used_at=now
        )
        await self.db.execute(insert_oauth_query)
        await self.db.commit()
        
        user = User(
            user_id=user_id,
            email=email,
            email_verified=email_verified,
            name=name,
            avatar_url=avatar_url,
            is_active=True,
            user_created_at=now,
            user_updated_at=now,
            last_login_at=now
        )
        
        logger.info(f"Created new user {user_id} from {provider_id} OAuth")
        return (user, True)
    
    # ========================================================================
    # AUDIT LOGGING
    # ========================================================================
    
    async def log_auth_event(
        self,
        event_type: AuthEventType,
        user_id: Optional[UUID] = None,
        provider_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log authentication event to audit log.
        
        CRITICAL: Includes circuit breaker to prevent DB saturation during attacks.
        Maximum 1000 events per minute. After that, events are dropped (not logged).
        
        Args:
            event_type: Type of auth event
            user_id: User UUID (if applicable)
            provider_id: OAuth provider (if applicable)
            ip_address: Client IP address
            user_agent: User agent string
            metadata: Additional event metadata
            
        Returns:
            True if logged, False if dropped due to circuit breaker
        """
        now = utcnow()
        
        # Circuit breaker: check if we're over limit
        if self._audit_log_window_start is None:
            self._audit_log_window_start = now
        
        # Reset window if more than 1 minute has passed
        if (now - self._audit_log_window_start) > timedelta(minutes=1):
            self._audit_log_window.clear()
            self._audit_log_window_start = now
        
        # Check if we've hit the limit (1000 events per minute)
        if len(self._audit_log_window) >= 1000:
            logger.warning(
                f"Audit log circuit breaker triggered: "
                f"Dropping {event_type} event (>1000 events/min)"
            )
            return False
        
        # Log the event
        try:
            AuditLogTable = User.__table__.metadata.tables['auth_audit_log']
            query = insert(AuditLogTable).values(
                user_id=user_id,
                event_type=event_type.value,
                provider_id=provider_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata,
                created_at=now
            )
            await self.db.execute(query)
            await self.db.commit()
            
            # Track in circuit breaker window
            self._audit_log_window.append(now)
            
            logger.debug(f"Logged auth event: {event_type} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log auth event: {e}")
            return False