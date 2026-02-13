"""Personal Access Token service."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, List

from .models import PersonalAccessToken, User


def generate_token_id() -> str:
    """Generate a unique token ID."""
    return f"pat_{secrets.token_hex(12)}"


def generate_pat_token() -> str:
    """
    Generate a secure PAT token.
    
    Format: pat_<random_bytes>
    Returns a 48-character token (4 + 44 from base64)
    """
    return f"pat_{secrets.token_urlsafe(32)}"


def hash_pat(token: str) -> str:
    """Hash a PAT for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def get_token_display(token: str) -> str:
    """Get display version of token (first 8 + last 4 chars)."""
    if len(token) <= 12:
        return token
    return f"{token[:8]}...{token[-4:]}"


def get_key_id(token: str) -> str:
    """Get short key ID from token (first 12 chars of hash)."""
    return hashlib.sha256(token.encode()).hexdigest()[:12]


class InMemoryPATRepository:
    """In-memory PAT repository for testing."""
    
    def __init__(self):
        self._tokens: dict[str, PersonalAccessToken] = {}
        self._by_hash: dict[str, str] = {}  # token_hash -> token_id
        self._by_user: dict[str, list[str]] = {}  # user_id -> [token_ids]
    
    async def create(self, pat: PersonalAccessToken) -> PersonalAccessToken:
        """Create a new PAT."""
        self._tokens[pat.token_id] = pat
        self._by_hash[pat.token_hash] = pat.token_id
        
        if pat.user_id not in self._by_user:
            self._by_user[pat.user_id] = []
        self._by_user[pat.user_id].append(pat.token_id)
        
        return pat
    
    async def get_by_id(self, token_id: str) -> Optional[PersonalAccessToken]:
        """Get PAT by ID."""
        return self._tokens.get(token_id)
    
    async def get_by_hash(self, token_hash: str) -> Optional[PersonalAccessToken]:
        """Get PAT by token hash."""
        token_id = self._by_hash.get(token_hash)
        if token_id:
            return self._tokens.get(token_id)
        return None
    
    async def list_by_user(self, user_id: str) -> List[PersonalAccessToken]:
        """List all PATs for a user."""
        token_ids = self._by_user.get(user_id, [])
        return [self._tokens[tid] for tid in token_ids if tid in self._tokens]
    
    async def update(self, pat: PersonalAccessToken) -> PersonalAccessToken:
        """Update a PAT."""
        if pat.token_id not in self._tokens:
            raise ValueError(f"PAT {pat.token_id} not found")
        self._tokens[pat.token_id] = pat
        return pat
    
    async def delete(self, token_id: str) -> bool:
        """Delete a PAT."""
        if token_id not in self._tokens:
            return False
        
        pat = self._tokens[token_id]
        del self._tokens[token_id]
        
        if pat.token_hash in self._by_hash:
            del self._by_hash[pat.token_hash]
        
        if pat.user_id in self._by_user:
            self._by_user[pat.user_id] = [
                tid for tid in self._by_user[pat.user_id] if tid != token_id
            ]
        
        return True
    
    def clear(self) -> None:
        """Clear all PATs (for testing)."""
        self._tokens.clear()
        self._by_hash.clear()
        self._by_user.clear()


class PATService:
    """Service for managing Personal Access Tokens."""
    
    def __init__(
        self,
        pat_repo: InMemoryPATRepository,
        default_expiry: Optional[timedelta] = None,
    ):
        self._pat_repo = pat_repo
        self._default_expiry = default_expiry or timedelta(days=90)
    
    async def create_token(
        self,
        user: User,
        name: str,
        expires_in: Optional[timedelta] = None,
    ) -> Tuple[str, PersonalAccessToken]:
        """
        Create a new PAT for a user.
        
        Args:
            user: User creating the token
            name: User-provided name/description
            expires_in: Optional custom expiry (defaults to 90 days)
            
        Returns:
            Tuple of (raw_token, PersonalAccessToken)
            The raw_token is only returned once and should be shown to user.
        """
        token = generate_pat_token()
        token_hash = hash_pat(token)
        now = datetime.now(timezone.utc)
        
        expiry = expires_in or self._default_expiry
        expires_at = now + expiry if expiry else None
        
        pat = PersonalAccessToken(
            token_id=generate_token_id(),
            user_id=user.user_id,
            name=name,
            token_hash=token_hash,
            token_display=get_token_display(token),
            key_id=get_key_id(token),
            created_at=now,
            expires_at=expires_at,
            last_used_at=None,
            is_active=True,
        )
        
        await self._pat_repo.create(pat)
        
        return token, pat
    
    async def validate_token(self, token: str) -> Optional[PersonalAccessToken]:
        """
        Validate a PAT and return it if valid.
        
        Args:
            token: Raw PAT string
            
        Returns:
            PersonalAccessToken if valid, None otherwise
        """
        token_hash = hash_pat(token)
        pat = await self._pat_repo.get_by_hash(token_hash)
        
        if not pat:
            return None
        
        if not pat.is_valid():
            return None
        
        # Update last used time
        pat.last_used_at = datetime.now(timezone.utc)
        await self._pat_repo.update(pat)
        
        return pat
    
    async def revoke_token(self, token_id: str, user_id: str) -> bool:
        """
        Revoke a PAT.
        
        Args:
            token_id: Token ID to revoke
            user_id: User ID (for authorization check)
            
        Returns:
            True if revoked, False if not found or unauthorized
        """
        pat = await self._pat_repo.get_by_id(token_id)
        
        if not pat or pat.user_id != user_id:
            return False
        
        pat.is_active = False
        await self._pat_repo.update(pat)
        
        return True
    
    async def list_user_tokens(self, user_id: str) -> List[PersonalAccessToken]:
        """
        List all PATs for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of PersonalAccessTokens (without revealing actual token)
        """
        return await self._pat_repo.list_by_user(user_id)
    
    async def delete_token(self, token_id: str, user_id: str) -> bool:
        """
        Permanently delete a PAT.
        
        Args:
            token_id: Token ID to delete
            user_id: User ID (for authorization check)
            
        Returns:
            True if deleted, False if not found or unauthorized
        """
        pat = await self._pat_repo.get_by_id(token_id)
        
        if not pat or pat.user_id != user_id:
            return False
        
        return await self._pat_repo.delete(token_id)
