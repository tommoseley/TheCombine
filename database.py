"""
Database configuration and session management.

PostgreSQL database with SQLAlchemy ORM.
"""

import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

logger = logging.getLogger(__name__)

# Database URL from config
DATABASE_URL = settings.DATABASE_URL

if not DATABASE_URL.startswith("postgresql"):
    raise ValueError(
        f"Expected PostgreSQL database URL, got: {DATABASE_URL[:20]}...\n"
        f"Set DATABASE_URL=postgresql://user:pass@localhost/combine in your .env"
    )

# Create PostgreSQL engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=10,           # Number of connections to maintain
    max_overflow=20,        # Additional connections when pool is full
    pool_pre_ping=True,     # Verify connections before using
    pool_recycle=3600,      # Recycle connections after 1 hour
    echo=False              # Set to True for SQL query logging
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
    logger.info(f"Initializing database: {DATABASE_URL[:30]}...")
    try:
        # Import models to ensure they're registered with Base
        from app.combine import models
        
        # Create all tables (idempotent - only creates if missing)
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise


def close_database():
    """Close database connections and dispose of connection pool."""
    engine.dispose()
    logger.info("✅ Database connections closed")


def check_database_connection() -> bool:
    """
    Check if database is accessible.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


@contextmanager
def get_db_session():
    """
    Get database session (context manager).
    
    Usage:
        with get_db_session() as session:
            user = session.query(User).first()
    
    Automatically commits on success, rolls back on error.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    """
    FastAPI dependency for database sessions.
    
    Usage in FastAPI:
        from database import get_db
        
        @router.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# PostgreSQL-Specific Utilities
# ============================================================================

def test_postgres_extensions():
    """
    Verify required PostgreSQL extensions are installed.
    
    Returns:
        True if all extensions present, False otherwise
    """
    required_extensions = ["uuid-ossp", "btree_gin"]
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT extname FROM pg_extension 
                WHERE extname IN ('uuid-ossp', 'btree_gin')
            """))
            
            installed = [row[0] for row in result]
            
            for ext in required_extensions:
                if ext not in installed:
                    logger.error(f"Missing PostgreSQL extension: {ext}")
                    logger.error(f"Run: CREATE EXTENSION IF NOT EXISTS \"{ext}\";")
                    return False
            
            logger.info(f"✅ All required PostgreSQL extensions installed")
            return True
            
    except Exception as e:
        logger.error(f"Extension check failed: {e}")
        return False


def verify_database_ready():
    """
    Comprehensive database readiness check.
    
    Checks:
    - Connection works
    - Required extensions installed
    
    Raises:
        RuntimeError if database not ready
    """
    logger.info("Verifying database readiness...")
    
    # Check connection
    if not check_database_connection():
        raise RuntimeError("Cannot connect to database")
    
    logger.info("✅ Database connection successful")
    
    # Check extensions
    if not test_postgres_extensions():
        raise RuntimeError("Missing required PostgreSQL extensions")
    
    logger.info("✅ PostgreSQL extensions verified")
    logger.info("✅ Database ready for use")