"""
Database configuration and session management.

Provides async database sessions and metadata for ORM models.
"""
from dotenv import load_dotenv
load_dotenv()

import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
import logging

logger = logging.getLogger(__name__)

# Create declarative base for ORM models
Base = declarative_base()

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/combine')

# Convert to async URL if needed
if DATABASE_URL.startswith('postgresql://'):
    ASYNC_DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://')
else:
    ASYNC_DATABASE_URL = DATABASE_URL

# Create async engine
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Yields:
        AsyncSession: Database session
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database():
    """
    Initialize database - create tables if they don't exist.
    
    Note: In production, use Alembic migrations instead.
    This is mainly for development/testing.
    """
    # Import all ORM models so they're registered with Base
    from app.auth.db_models import (
        UserORM, UserOAuthIdentityORM, UserSessionORM,
        PersonalAccessTokenORM, AuthAuditLogORM, LinkIntentNonceORM
    )
    from app.api.models.concierge_intake import (
        ConciergeIntakeSession, ConciergeIntakeEvent
    )
    
    async with engine.begin() as conn:
        # Create all tables (idempotent)
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialized")
