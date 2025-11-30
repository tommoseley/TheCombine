"""
Session management models for magic link authentication.
"""

from sqlalchemy import Column, String, Boolean
from datetime import datetime, timedelta, timezone


def create_sessions_table(Base):
    """
    Create Session model using the application's Base.
    """
    
    class Session(Base):
        """Active user session after successful magic link validation."""
        
        __tablename__ = "sessions"
        
        id = Column(String, primary_key=True, index=True)
        email = Column(String, nullable=False, index=True)
        expires_at = Column(String, nullable=False, index=True)
        created_at = Column(String, nullable=False)
        
        def is_expired(self) -> bool:
            """Check if session has expired."""
            expires_at = datetime.fromisoformat(self.expires_at.rstrip('Z').replace('+00:00', ''))
            expires_at = expires_at.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) > expires_at
    
    
    class PendingToken(Base):
        """Temporary storage for unused magic link tokens."""
        
        __tablename__ = "pending_tokens"
        
        token_hash = Column(String, primary_key=True)
        email = Column(String, nullable=False, index=True)
        expires_at = Column(String, nullable=False, index=True)
        created_at = Column(String, nullable=False)
        
        def is_expired(self) -> bool:
            """Check if token has expired."""
            expires_at = datetime.fromisoformat(self.expires_at.rstrip('Z').replace('+00:00', ''))
            expires_at = expires_at.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) > expires_at
    
    return Session, PendingToken