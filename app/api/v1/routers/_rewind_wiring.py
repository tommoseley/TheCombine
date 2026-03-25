"""Wiring helpers for rewind API endpoints.

Adapts the domain services to use DB-backed repositories via
the AsyncSession from FastAPI dependency injection.
"""

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.services.lineage_service import (
    InMemoryLineageRepository,
    LineageService,
)
from app.domain.services.regeneration_service import RegenerationService
from app.domain.services.rewind_service import RewindService
from app.persistence.pg_repositories import PostgresDocumentRepository


# For MVP, lineage events use in-memory storage per process.
# TODO: Create PostgresLineageRepository backed by lineage_events table
# once the alembic migration for that table is applied.
_lineage_repo = InMemoryLineageRepository()


def _wrap_session(db: AsyncSession):
    """Wrap a FastAPI-injected session as a session factory for repositories."""

    @asynccontextmanager
    async def _factory():
        yield db

    return _factory


async def build_rewind_service(db: AsyncSession) -> RewindService:
    """Build RewindService with DB-backed document repo."""
    doc_repo = PostgresDocumentRepository(_wrap_session(db))
    lineage_service = LineageService(repository=_lineage_repo)
    return RewindService(
        document_repo=doc_repo,
        lineage_service=lineage_service,
    )


async def build_regeneration_service(db: AsyncSession) -> RegenerationService:
    """Build RegenerationService with DB-backed document repo."""
    doc_repo = PostgresDocumentRepository(_wrap_session(db))
    lineage_service = LineageService(repository=_lineage_repo)
    return RegenerationService(
        document_repo=doc_repo,
        lineage_service=lineage_service,
    )


async def build_lineage_service(db: AsyncSession) -> LineageService:
    """Build LineageService. MVP: in-memory per process."""
    return LineageService(repository=_lineage_repo)
