"""
Database configuration and session management (ASYNC VERSION).

PostgreSQL database with SQLAlchemy ORM + asyncpg.
"""

import os
import logging
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from config import settings

logger = logging.getLogger(__name__)

# Database URL from config
DATABASE_URL = settings.DATABASE_URL

if not DATABASE_URL.startswith("postgresql"):
    raise ValueError(
        f"Expected PostgreSQL database URL, got: {DATABASE_URL[:20]}...\n"
        f"Set DATABASE_URL=postgresql://user:pass@localhost/combine in your .env"
    )

# Convert to async driver (asyncpg)
ASYNC_DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://')

# Create async PostgreSQL engine with connection pooling
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_size=10,           # Number of connections to maintain
    max_overflow=20,        # Additional connections when pool is full
    pool_pre_ping=True,     # Verify connections before using
    pool_recycle=3600,      # Recycle connections after 1 hour
    echo=False              # Set to True for SQL query logging
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for ORM models
Base = declarative_base()


async def init_database():
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
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise


async def close_database():
    """Close database connections and dispose of connection pool."""
    await engine.dispose()
    logger.info("✅ Database connections closed")


async def check_database_connection() -> bool:
    """
    Check if database is accessible.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


@asynccontextmanager
async def get_db_session():
    """
    Get database session (async context manager).
    
    Usage:
        async with get_db_session() as session:
            result = await session.execute(select(User))
            user = result.scalar_one()
    
    Automatically commits on success, rolls back on error.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db():
    """
    FastAPI dependency for database sessions (ASYNC).
    
    Usage in FastAPI:
        from database import get_db
        from sqlalchemy.ext.asyncio import AsyncSession
        
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ============================================================================
# PostgreSQL-Specific Utilities
# ============================================================================

async def test_postgres_extensions():
    """
    Verify required PostgreSQL extensions are installed.
    
    Returns:
        True if all extensions present, False otherwise
    """
    required_extensions = ["uuid-ossp", "btree_gin"]
    
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("""
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


async def verify_database_ready():
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
    if not await check_database_connection():
        raise RuntimeError("Cannot connect to database")
    
    logger.info("✅ Database connection successful")
    
    # Check extensions
    if not await test_postgres_extensions():
        raise RuntimeError("Missing required PostgreSQL extensions")
    
    logger.info("✅ PostgreSQL extensions verified")
    logger.info("✅ Database ready for use")