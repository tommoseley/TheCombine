"""
Database configuration and session management.

Provides async database sessions and metadata for ORM models.

DATABASE_URL is read from app.core.config (single resolution path).
Do not read DATABASE_URL independently from os.getenv here — config.py
is the authority (WS-AWS-DB-003 Phase 0 reconciliation).
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
import logging

from app.core.config import DATABASE_URL

logger = logging.getLogger(__name__)

# Create declarative base for ORM models
Base = declarative_base()

# Convert to async URL if needed
if DATABASE_URL.startswith('postgresql://'):
    ASYNC_DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://')
else:
    ASYNC_DATABASE_URL = DATABASE_URL

# Create async engine with UTF-8 encoding
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
    connect_args={"server_settings": {"client_encoding": "utf8"}}
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
    # Import ALL ORM models so they're registered with Base.
    # Every model that inherits from Base must be imported here,
    # otherwise Base.metadata.create_all() won't know about its table.

    # Auth models
    from app.auth.db_models import (  # noqa: F401
        UserORM, UserOAuthIdentityORM, UserSessionORM,
        PersonalAccessTokenORM, AuthAuditLogORM, LinkIntentNonceORM
    )

    # Core domain models
    from app.api.models.project import Project  # noqa: F401
    from app.api.models.document import Document  # noqa: F401
    from app.api.models.document_type import DocumentType  # noqa: F401
    from app.api.models.document_relation import DocumentRelation  # noqa: F401
    from app.api.models.document_definition import DocumentDefinition  # noqa: F401
    from app.api.models.file import File  # noqa: F401

    # Workflow models
    from app.api.models.workflow_instance import (  # noqa: F401
        WorkflowInstance, WorkflowInstanceHistory
    )
    from app.api.models.workflow_execution import WorkflowExecution  # noqa: F401
    from app.api.models.pgc_answer import PGCAnswer  # noqa: F401
    from app.api.models.governance_outcome import GovernanceOutcome  # noqa: F401

    # LLM logging models (canonical location: domain/models)
    from app.domain.models.llm_logging import (  # noqa: F401
        LLMContent, LLMRun, LLMRunInputRef,
        LLMRunOutputRef, LLMRunError, LLMRunToolCall
    )
    from app.api.models.llm_thread import (  # noqa: F401
        LLMThreadModel, LLMWorkItemModel, LLMLedgerEntryModel
    )

    # WS execution metrics models
    from app.domain.models.ws_metrics import WSExecution, WSBugFix  # noqa: F401

    # Artifact models
    from app.api.models.component_artifact import ComponentArtifact  # noqa: F401
    from app.api.models.fragment_artifact import (  # noqa: F401
        FragmentArtifact, FragmentBinding
    )
    from app.api.models.schema_artifact import SchemaArtifact  # noqa: F401

    # Configuration models
    from app.api.models.role import Role  # noqa: F401
    from app.api.models.role_prompt import RolePrompt  # noqa: F401
    from app.api.models.role_task import RoleTask  # noqa: F401
    from app.api.models.system_config import SystemConfig  # noqa: F401
    from app.api.models.project_audit import ProjectAudit  # noqa: F401
    
    async with engine.begin() as conn:
        # Create all tables (idempotent)
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialized")
