"""PGC Answer Repository.

Per WS-PGC-VALIDATION-001 Phase 2.

IMPORTANT: Does NOT commit. Caller owns transaction.
"""

from typing import List, Optional
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.models.pgc_answer import PGCAnswer

logger = logging.getLogger(__name__)


class PGCAnswerRepository:
    """PostgreSQL repository for PGC answers.

    Does NOT commit internally - caller owns transaction.
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    async def add(self, answer: PGCAnswer) -> None:
        """Add answer to session.

        Caller must commit.
        """
        self._db.add(answer)
        logger.info(f"Added PGC answer for execution {answer.execution_id}")

    async def get_by_execution(self, execution_id: str) -> Optional[PGCAnswer]:
        """Get PGC answer by execution ID.

        Args:
            execution_id: The workflow execution ID

        Returns:
            PGCAnswer or None if not found
        """
        result = await self._db.execute(
            select(PGCAnswer).where(PGCAnswer.execution_id == execution_id)
        )
        return result.scalar_one_or_none()

    async def get_by_project(self, project_id: UUID) -> List[PGCAnswer]:
        """Get all PGC answers for a project, newest first.

        Args:
            project_id: The project ID

        Returns:
            List of PGCAnswer, ordered by created_at descending
        """
        result = await self._db.execute(
            select(PGCAnswer)
            .where(PGCAnswer.project_id == project_id)
            .order_by(PGCAnswer.created_at.desc())
        )
        return list(result.scalars().all())
