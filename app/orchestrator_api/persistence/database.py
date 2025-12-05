"""Database configuration and session management."""

import os
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool  # ← ADD THIS IMPORT
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

from config import settings
from workforce.utils.logging import log_info, log_error


# Database URL from config
DATABASE_URL = settings.DATABASE_URL

# Create engine with appropriate configuration
if DATABASE_URL.startswith("sqlite"):
    # SQLite: single connection pool, WAL mode
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    # Enable WAL mode for better concurrency
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        
else:
    # PostgreSQL: connection pooling
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=10,
        echo=False
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def init_database():
    """
    Initialize database: create tables if they don't exist.
    
    Uses SQLAlchemy's Base.metadata.create_all() which is idempotent
    (only creates tables that don't exist).
    """
    log_info(f"Initializing database: {DATABASE_URL}")
    try:
        # Import models to ensure they're registered with Base
        from app.orchestrator_api import models
        
        # Create all tables (idempotent - only creates if missing)
        Base.metadata.create_all(bind=engine)
        log_info("Database initialized successfully")
    except Exception as e:
        log_error(f"Database initialization failed: {e}")
        raise


def close_database():
    """Close database connections."""
    engine.dispose()
    log_info("Database connections closed")


def check_database_connection() -> bool:
    """Check if database is accessible."""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


@contextmanager
def get_db_session():
    """Get database session (context manager)."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()