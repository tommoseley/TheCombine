"""
Authentication service.

ADR-008: Multi-Provider OAuth Authentication
Business logic for session management, user creation, and audit logging.

Stage 6: With Account Linking
"""
import logging
import os
import secrets
from datetime import timedelta
from typing import Optional, Tuple, Dict, Any
from uuid import UUID
from collections import deque
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func

from app.auth.models import User, UserSession, AuthEventType
from app.auth.db_models import (
    UserORM, UserOAuthIdentityORM, UserSessionORM,
    AuthAuditLogORM, LinkIntentNonceORM
)
from app.auth.utils import utcnow

logger = logging.getLogger(__name__)


def _is_admin_email(email: str) -> bool:
    """Check if email is in admin allowlist."""
    admin_emails = os.getenv('ADMIN_EMAILS', '')
    if not admin_emails:
        return False
    allowlist = [e.strip().lower() for e in admin_emails.split(',') if e.strip()]
    return email.lower() in allowlist


class AuthService:
    """
    Authentication service for user and session management.
    
    Handles:
    - Session creation and verification (with write throttling)
    - User creation from OIDC claims
    - Audit event logging (with circuit breaker)
    - Account linking (Stage 6)
    
    Future: PATs (Stage 7)
    """
    
    # Circuit breaker for audit logging: max 1000 events per minute
    AUDIT_LOG_RATE_LIMIT = 1000
    
    def __init__(self, db: AsyncSession):
        """
        Initialize auth service.
        
        Args:
            db: Async database session
        """
        self.db = db
        self._audit_log_times = deque(maxlen=self.AUDIT_LOG_RATE_LIMIT)
    
    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================
    
    async def create_session(
        self,
        user_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserSession:
        """
        Create new session for user.
        
        Generates cryptographically secure tokens (43 chars URL-safe).
        Session expires in 30 days.
        
        Args:
            user_id: User ID
            ip_address: Client IP address
            user_agent: User agent string
            
        Returns:
            UserSession with session_token and csrf_token
        """
        now = utcnow()
        session_token = secrets.token_urlsafe(32)  # 43 chars
        csrf_token = secrets.token_urlsafe(32)     # 43 chars
        
        # Create ORM object
        session_orm = UserSessionORM(
            user_id=user_id,
            session_token=session_token,
            csrf_token=csrf_token,
            ip_address=ip_address,
            user_agent=user_agent,
            session_created_at=now,
            last_activity_at=now,
            expires_at=now + timedelta(days=30)
        )
        
        self.db.add(session_orm)
        await self.db.commit()
        await self.db.refresh(session_orm)
        
        # Convert to dataclass
        session = UserSession(
            session_id=session_orm.session_id,
            user_id=session_orm.user_id,
            session_token=session_orm.session_token,
            csrf_token=session_orm.csrf_token,
            ip_address=session_orm.ip_address,
            user_agent=session_orm.user_agent,
            session_created_at=session_orm.session_created_at,
            last_activity_at=session_orm.last_activity_at,
            expires_at=session_orm.expires_at
        )
        
        logger.info(f"Created session {session.session_id} for user {user_id}")
        return session
    
    async def verify_session(
        self,
        session_token: str
    ) -> Optional[Tuple[User, UUID, str]]:
        """
        Verify session token and return user.
        
        Write throttling: Only updates last_activity_at if >15 minutes since last update
        (reduces DB writes by ~90% while maintaining reasonable freshness).
        
        Args:
            session_token: Session token from cookie
            
        Returns:
            Tuple of (User, session_id, csrf_token) or None if invalid/expired
        """
        now = utcnow()
        
        # Query session with user (using ORM with join)
        result = await self.db.execute(
            select(UserSessionORM, UserORM)
            .join(UserORM)
            .where(
                UserSessionORM.session_token == session_token,
                UserSessionORM.expires_at > now
            )
        )
        row = result.first()
        
        if not row:
            return None
        
        session_orm, user_orm = row
        
        # Check if user is active
        if not user_orm.is_active:
            return None
        
        # Write throttling: only update if >15 minutes
        time_since_activity = now - session_orm.last_activity_at
        if time_since_activity.total_seconds() > 900:  # 15 minutes
            session_orm.last_activity_at = now
            await self.db.commit()
        
        # Convert to dataclasses
        user = User(
            user_id=user_orm.user_id,
            email=user_orm.email,
            email_verified=user_orm.email_verified,
            name=user_orm.name,
            avatar_url=user_orm.avatar_url,
            is_active=user_orm.is_active,
            user_created_at=user_orm.user_created_at,
            user_updated_at=user_orm.user_updated_at,
            last_login_at=user_orm.last_login_at,
            is_admin=_is_admin_email(user_orm.email)
        )
        
        return (user, session_orm.session_id, session_orm.csrf_token)

    async def delete_session(self, session_token: str) -> bool:
        """
        Delete session by token.
        
        Args:
            session_token: Session token to delete
            
        Returns:
            True if session was deleted, False if not found
        """
        result = await self.db.execute(
            delete(UserSessionORM).where(
                UserSessionORM.session_token == session_token
            )
        )
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
        - If email exists with verified match: Auto-link the new provider
        - If email exists with unverified match: Block, show error
        - If email doesn't exist: Create new user
        
        Returns:
            Tuple of (User, created: bool)
        """
        email = claims['email']
        email_verified = claims.get('email_verified', False)
        
        # Check if OAuth identity already exists
        existing_user = await self._find_user_by_oauth_identity(provider_id, provider_user_id)
        if existing_user:
            await self._update_user_on_login(existing_user, claims)
            logger.info(f"Existing user {existing_user.user_id} logged in via {provider_id}")
            return (self._orm_to_user(existing_user), False)
        
        # Check for email collision
        existing_by_email = await self._find_user_by_email(email)
        if existing_by_email:
            return await self._handle_email_collision(
                existing_by_email, provider_id, provider_user_id, claims, email_verified
            )
        
        # Create new user
        user = await self._create_new_user(provider_id, provider_user_id, claims)
        logger.info(f"Created new user {user.user_id} from {provider_id} OAuth")
        return (user, True)
    
    async def _find_user_by_oauth_identity(
        self, provider_id: str, provider_user_id: str
    ) -> Optional[UserORM]:
        """Find user by OAuth identity."""
        result = await self.db.execute(
            select(UserORM)
            .join(UserOAuthIdentityORM)
            .where(
                UserOAuthIdentityORM.provider_id == provider_id,
                UserOAuthIdentityORM.provider_user_id == provider_user_id
            )
        )
        return result.scalar_one_or_none()
    
    async def _find_user_by_email(self, email: str) -> Optional[UserORM]:
        """Find user by email."""
        result = await self.db.execute(
            select(UserORM).where(UserORM.email == email)
        )
        return result.scalar_one_or_none()
    
    async def _update_last_login(self, user_orm: UserORM) -> None:
        """Update user's last login timestamp."""
        user_orm.last_login_at = utcnow()
        await self.db.commit()
        await self.db.refresh(user_orm)

    async def _update_user_on_login(self, user_orm: UserORM, claims: Dict[str, Any]) -> None:
        """Update user on login - refresh timestamp and avatar from claims."""
        user_orm.last_login_at = utcnow()
        # Refresh avatar from OAuth provider (in case it changed)
        if claims.get('picture'):
            user_orm.avatar_url = claims['picture']
        # Refresh name if not set
        if not user_orm.name and claims.get('name'):
            user_orm.name = claims['name']
        await self.db.commit()
        await self.db.refresh(user_orm)
    
    def _orm_to_user(self, user_orm: UserORM) -> User:
        """Convert UserORM to User dataclass."""
        return User(
            user_id=user_orm.user_id,
            email=user_orm.email,
            email_verified=user_orm.email_verified,
            name=user_orm.name or '',
            avatar_url=user_orm.avatar_url,
            is_active=user_orm.is_active,
            user_created_at=user_orm.user_created_at,
            user_updated_at=user_orm.user_updated_at,
            last_login_at=user_orm.last_login_at,
            is_admin=_is_admin_email(user_orm.email)
        )
    
    async def _handle_email_collision(
        self,
        existing_user: UserORM,
        provider_id: str,
        provider_user_id: str,
        claims: Dict[str, Any],
        incoming_verified: bool
    ) -> Tuple[User, bool]:
        """Handle email collision when OAuth identity doesn't exist but email does."""
        email = claims['email']
        
        if existing_user.email_verified and incoming_verified:
            logger.info(
                f"Auto-linking {provider_id} to existing user {existing_user.user_id} "
                f"(both providers verified {email})"
            )
            await self._create_oauth_identity(
                existing_user.user_id, provider_id, provider_user_id, claims, incoming_verified
            )
            existing_user.last_login_at = utcnow()
            await self.db.commit()
            return (self._orm_to_user(existing_user), False)
        
        elif existing_user.email_verified:
            logger.warning(f"Email collision: {email} exists (verified), incoming NOT verified")
            raise ValueError(
                f"An account with email {email} already exists. "
                f"Please sign in with your existing provider first, "
                f"then link {provider_id} from your account settings."
            )
        else:
            logger.warning(f"Email collision: {email} exists (unverified)")
            raise ValueError(
                f"An account with email {email} already exists but is not verified. "
                f"Please verify your existing account first."
            )
    
    async def _create_oauth_identity(
        self,
        user_id: UUID,
        provider_id: str,
        provider_user_id: str,
        claims: Dict[str, Any],
        email_verified: bool
    ) -> UserOAuthIdentityORM:
        """Create OAuth identity record for a user."""
        now = utcnow()
        oauth_identity = UserOAuthIdentityORM(
            user_id=user_id,
            provider_id=provider_id,
            provider_user_id=provider_user_id,
            provider_email=claims['email'],
            email_verified=email_verified,
            provider_metadata={
                'sub': claims['sub'],
                'email': claims['email'],
                'name': claims.get('name', '')
            },
            identity_created_at=now,
            last_used_at=now
        )
        self.db.add(oauth_identity)
        return oauth_identity
    
    async def _create_new_user(
        self,
        provider_id: str,
        provider_user_id: str,
        claims: Dict[str, Any]
    ) -> User:
        """Create new user from OIDC claims."""
        email = claims['email']
        email_verified = claims.get('email_verified', False)
        name = claims.get('name', '')
        avatar_url = claims.get('picture')
        
        now = utcnow()
        new_user = UserORM(
            email=email,
            email_verified=email_verified,
            name=name,
            avatar_url=avatar_url,
            is_active=True,
            user_created_at=now,
            user_updated_at=now,
            last_login_at=now
        )
        self.db.add(new_user)
        await self.db.flush()
        
        await self._create_oauth_identity(
            new_user.user_id, provider_id, provider_user_id, claims, email_verified
        )
        await self.db.commit()
        await self.db.refresh(new_user)
        
        return self._orm_to_user(new_user)

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
        
        Circuit breaker: Drops events after 1000/minute to prevent DB saturation
        during attacks.
        
        Args:
            event_type: Type of auth event
            user_id: Optional user ID
            provider_id: Optional OAuth provider
            ip_address: Client IP
            user_agent: User agent string
            metadata: Additional metadata dict
            
        Returns:
            True if logged, False if rate limited
        """
        # Circuit breaker: limit to 1000 events per minute
        now = utcnow()
        
        # Clean old entries (older than 1 minute)
        cutoff_time = now - timedelta(minutes=1)
        while self._audit_log_times and self._audit_log_times[0] < cutoff_time:
            self._audit_log_times.popleft()
        
        # Check rate limit
        if len(self._audit_log_times) >= self.AUDIT_LOG_RATE_LIMIT:
            logger.warning(
                f"Audit log rate limit hit ({self.AUDIT_LOG_RATE_LIMIT}/min). "
                f"Dropping event: {event_type.value}"
            )
            return False
        
        # Record timestamp
        self._audit_log_times.append(now)
        
        # Create audit log entry (using ORM)
        log_entry = AuthAuditLogORM(
            user_id=user_id,
            event_type=event_type.value,
            provider_id=provider_id,
            ip_address=ip_address,
            user_agent=user_agent,
            event_metadata=metadata,  # Note: using event_metadata attribute
            created_at=now
        )
        
        self.db.add(log_entry)
        await self.db.commit()
        
        return True
    
    # ========================================================================
    # ACCOUNT LINKING
    # ========================================================================
    
    async def create_link_intent(
        self,
        user_id: UUID,
        provider_id: str
    ) -> str:
        """
        Create link intent nonce for account linking flow.
        
        Security: Nonce is single-use and expires in 15 minutes.
        Prevents unauthorized linking attempts.
        
        Args:
            user_id: User who is initiating the link
            provider_id: Provider to link ('google', 'microsoft')
            
        Returns:
            Nonce string (64 chars hex)
        """
        # Generate nonce
        nonce = secrets.token_hex(32)  # 64 chars
        
        # Create intent
        now = utcnow()
        intent = LinkIntentNonceORM(
            user_id=user_id,
            nonce=nonce,
            provider_id=provider_id,
            created_at=now,
            expires_at=now + timedelta(minutes=15)
        )
        
        self.db.add(intent)
        await self.db.commit()
        
        logger.info(f"Created link intent for user {user_id} to link {provider_id}")
        return nonce
    
    async def verify_link_intent(
        self,
        nonce: str
    ) -> Optional[Tuple[UUID, str]]:
        """
        Verify and consume link intent nonce.
        
        Single-use: Nonce is deleted after verification.
        
        Args:
            nonce: Link intent nonce
            
        Returns:
            Tuple of (user_id, provider_id) or None if invalid/expired
        """
        now = utcnow()
        
        # Find and delete nonce (single-use)
        result = await self.db.execute(
            select(LinkIntentNonceORM).where(
                LinkIntentNonceORM.nonce == nonce,
                LinkIntentNonceORM.expires_at > now
            )
        )
        intent = result.scalar_one_or_none()
        
        if not intent:
            return None
        
        user_id = intent.user_id
        provider_id = intent.provider_id
        
        # Delete nonce (single-use)
        await self.db.delete(intent)
        await self.db.commit()
        
        logger.info(f"Verified link intent for user {user_id} to link {provider_id}")
        return (user_id, provider_id)
    
    async def link_oauth_identity(
        self,
        user_id: UUID,
        provider_id: str,
        provider_user_id: str,
        claims: Dict[str, Any]
    ) -> bool:
        """
        Link OAuth identity to existing user.
        
        Security checks:
        - Prevents linking identity already linked to another user
        - Prevents duplicate links to same user
        
        Args:
            user_id: User to link identity to
            provider_id: OAuth provider
            provider_user_id: Provider's user ID
            claims: OAuth claims
            
        Returns:
            True if linked, False if already linked
            
        Raises:
            ValueError: If identity is linked to a different user
        """
        # Check if this identity is already linked to ANOTHER user
        result = await self.db.execute(
            select(UserOAuthIdentityORM).where(
                UserOAuthIdentityORM.provider_id == provider_id,
                UserOAuthIdentityORM.provider_user_id == provider_user_id
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            if existing.user_id == user_id:
                # Already linked to this user - idempotent
                logger.info(f"Identity {provider_id}/{provider_user_id} already linked to user {user_id}")
                return False
            else:
                # Linked to different user - security violation
                logger.warning(
                    f"Attempt to link {provider_id}/{provider_user_id} to user {user_id}, "
                    f"but already linked to user {existing.user_id}"
                )
                raise ValueError(
                    f"This {provider_id} account is already linked to another user. "
                    f"Please use a different account."
                )
        
        # Create new link
        now = utcnow()
        identity = UserOAuthIdentityORM(
            user_id=user_id,
            provider_id=provider_id,
            provider_user_id=provider_user_id,
            provider_email=claims.get('email'),
            email_verified=claims.get('email_verified', False),
            provider_metadata={
                'sub': claims['sub'],
                'email': claims.get('email'),
                'name': claims.get('name')
            },
            identity_created_at=now,
            last_used_at=now
        )
        
        self.db.add(identity)
        await self.db.commit()
        
        logger.info(f"Linked {provider_id} identity to user {user_id}")
        return True
    
    async def get_linked_identities(
        self,
        user_id: UUID
    ) -> list[Dict[str, Any]]:
        """
        Get all OAuth identities linked to user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of identity dicts with provider info
        """
        result = await self.db.execute(
            select(UserOAuthIdentityORM).where(
                UserOAuthIdentityORM.user_id == user_id
            ).order_by(UserOAuthIdentityORM.identity_created_at)
        )
        identities = result.scalars().all()
        
        return [
            {
                'identity_id': str(identity.identity_id),
                'provider_id': identity.provider_id,
                'provider_email': identity.provider_email,
                'email_verified': identity.email_verified,
                'linked_at': identity.identity_created_at.isoformat(),
                'last_used': identity.last_used_at.isoformat()
            }
            for identity in identities
        ]
    
    async def unlink_oauth_identity(
        self,
        user_id: UUID,
        provider_id: str
    ) -> bool:
        """
        Unlink OAuth identity from user.
        
        Security: Prevents unlinking if it's the only identity (user would be locked out).
        
        Args:
            user_id: User ID
            provider_id: Provider to unlink
            
        Returns:
            True if unlinked
            
        Raises:
            ValueError: If trying to unlink the only identity
        """
        # Count identities
        result = await self.db.execute(
            select(func.count(UserOAuthIdentityORM.identity_id)).where(
                UserOAuthIdentityORM.user_id == user_id
            )
        )
        count = result.scalar()
        
        if count <= 1:
            raise ValueError(
                "Cannot unlink your only login method. "
                "Please link another account first."
            )
        
        # Delete identity
        result = await self.db.execute(
            delete(UserOAuthIdentityORM).where(
                UserOAuthIdentityORM.user_id == user_id,
                UserOAuthIdentityORM.provider_id == provider_id
            )
        )
        await self.db.commit()
        
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"Unlinked {provider_id} from user {user_id}")
        
        return deleted
