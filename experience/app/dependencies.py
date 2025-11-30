"""
Shared dependencies for FastAPI routers.
"""

from sqlalchemy.orm import Session
from typing import Generator

# Will be set by main.py
SessionLocal = None


def set_session_local(session_local):
    """Set SessionLocal after it's created in main.py."""
    global SessionLocal
    SessionLocal = session_local


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get database session.
    
    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()