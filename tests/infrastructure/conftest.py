"""Shared fixtures for infrastructure tests.

Infrastructure tests use TestClient against the real app, which hits the
real database. This conftest ensures database tables exist before tests run.
"""

import logging

import pytest
from sqlalchemy import create_engine

from app.core.config import DATABASE_URL
from app.core.database import Base

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
def _create_database_tables():
    """Create all ORM tables in the test database before infrastructure tests.

    Uses a sync engine to avoid event loop conflicts with TestClient.
    The same model imports as init_database() in app/core/database.py.
    """
    # Import all ORM models so they register with Base.metadata
    from app.auth.db_models import (  # noqa: F401
        UserORM, UserOAuthIdentityORM, UserSessionORM,
        PersonalAccessTokenORM, AuthAuditLogORM, LinkIntentNonceORM
    )
    from app.api.models.project import Project  # noqa: F401
    from app.api.models.document import Document  # noqa: F401
    from app.api.models.document_type import DocumentType  # noqa: F401
    from app.api.models.document_relation import DocumentRelation  # noqa: F401
    from app.api.models.document_definition import DocumentDefinition  # noqa: F401
    from app.api.models.file import File  # noqa: F401
    from app.api.models.workflow_instance import (  # noqa: F401
        WorkflowInstance, WorkflowInstanceHistory
    )
    from app.api.models.workflow_execution import WorkflowExecution  # noqa: F401
    from app.api.models.pgc_answer import PGCAnswer  # noqa: F401
    from app.api.models.governance_outcome import GovernanceOutcome  # noqa: F401
    from app.domain.models.llm_logging import (  # noqa: F401
        LLMContent, LLMRun, LLMRunInputRef,
        LLMRunOutputRef, LLMRunError, LLMRunToolCall
    )
    from app.api.models.llm_thread import (  # noqa: F401
        LLMThreadModel, LLMWorkItemModel, LLMLedgerEntryModel
    )
    from app.domain.models.ws_metrics import WSExecution, WSBugFix  # noqa: F401
    from app.api.models.component_artifact import ComponentArtifact  # noqa: F401
    from app.api.models.fragment_artifact import (  # noqa: F401
        FragmentArtifact, FragmentBinding
    )
    from app.api.models.schema_artifact import SchemaArtifact  # noqa: F401
    from app.api.models.role import Role  # noqa: F401
    from app.api.models.role_prompt import RolePrompt  # noqa: F401
    from app.api.models.role_task import RoleTask  # noqa: F401
    from app.api.models.system_config import SystemConfig  # noqa: F401
    from app.api.models.project_audit import ProjectAudit  # noqa: F401

    # Sync URL for table creation (no asyncpg needed)
    sync_url = DATABASE_URL
    if "+asyncpg" in sync_url:
        sync_url = sync_url.replace("+asyncpg", "")

    try:
        engine = create_engine(sync_url)
        Base.metadata.create_all(engine)
        engine.dispose()
        logger.info("Infrastructure test database tables created")
    except Exception as e:
        logger.warning(f"Could not create database tables: {e}")
