"""
LLM Logging dependency providers.

Provides FastAPI dependencies for LLM execution logging (ADR-010).
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.repositories.llm_log_repository import LLMLogRepository
from app.domain.repositories.postgres_llm_log_repository import PostgresLLMLogRepository
from app.domain.services.llm_execution_logger import LLMExecutionLogger


async def get_llm_log_repository(
    db: AsyncSession = Depends(get_db)
) -> LLMLogRepository:
    """Provide LLM log repository."""
    return PostgresLLMLogRepository(db)


async def get_llm_execution_logger(
    repo: LLMLogRepository = Depends(get_llm_log_repository)
) -> LLMExecutionLogger:
    """Provide LLM execution logger."""
    return LLMExecutionLogger(repo)
