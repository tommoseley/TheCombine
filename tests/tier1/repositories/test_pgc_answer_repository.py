"""Tests for PGCAnswerRepository.

Per WS-PGC-VALIDATION-001 Phase 2.

These are tier1 tests using mocked database session.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.domain.repositories.pgc_answer_repository import PGCAnswerRepository
from app.api.models.pgc_answer import PGCAnswer


@pytest.mark.asyncio
class TestPGCAnswerRepository:
    """Tests for PGCAnswerRepository."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock async database session."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository with mock database."""
        return PGCAnswerRepository(mock_db)

    @pytest.fixture
    def sample_answer(self):
        """Create a sample PGC answer."""
        return PGCAnswer(
            execution_id="exec-123",
            workflow_id="pm_discovery.v1",
            project_id=uuid4(),
            pgc_node_id="pgc",
            schema_ref="seed/schemas/clarification_question_set.v2.json",
            questions=[
                {"id": "Q1", "text": "Authentication required?", "priority": "must"},
                {"id": "Q2", "text": "Include analytics?", "priority": "should"},
            ],
            answers={"Q1": True, "Q2": False},
        )

    async def test_add_does_not_commit(self, repo, mock_db, sample_answer):
        """Repository add should not commit - caller owns transaction."""
        await repo.add(sample_answer)

        # Verify add was called
        mock_db.add.assert_called_once_with(sample_answer)

        # Verify commit was NOT called
        mock_db.commit.assert_not_called()

    async def test_get_by_execution_returns_answer(self, repo, mock_db, sample_answer):
        """Getting existing answer returns it."""
        # Setup mock to return the answer
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_answer
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_execution("exec-123")

        assert result == sample_answer
        mock_db.execute.assert_called_once()

    async def test_get_by_execution_returns_none_when_missing(self, repo, mock_db):
        """Getting nonexistent answer returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_execution("nonexistent")

        assert result is None

    async def test_get_by_project_returns_list(self, repo, mock_db, sample_answer):
        """Getting answers by project returns list."""
        # Setup mock to return list of answers
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_answer]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        project_id = sample_answer.project_id
        result = await repo.get_by_project(project_id)

        assert len(result) == 1
        assert result[0] == sample_answer

    async def test_get_by_project_returns_empty_list(self, repo, mock_db):
        """Getting answers for project with none returns empty list."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_project(uuid4())

        assert result == []


class TestPGCAnswerModel:
    """Tests for PGCAnswer model."""

    def test_to_dict_serialization(self):
        """to_dict should serialize all fields correctly."""
        project_id = uuid4()
        answer = PGCAnswer(
            execution_id="exec-456",
            workflow_id="test_workflow",
            project_id=project_id,
            pgc_node_id="pgc_clarification",
            schema_ref="schema://test",
            questions=[{"id": "Q1", "text": "Test?"}],
            answers={"Q1": "yes"},
        )

        result = answer.to_dict()

        assert result["execution_id"] == "exec-456"
        assert result["workflow_id"] == "test_workflow"
        assert result["project_id"] == str(project_id)
        assert result["pgc_node_id"] == "pgc_clarification"
        assert result["schema_ref"] == "schema://test"
        assert result["questions"] == [{"id": "Q1", "text": "Test?"}]
        assert result["answers"] == {"Q1": "yes"}

    def test_to_dict_handles_none_created_at(self):
        """to_dict should handle None created_at."""
        answer = PGCAnswer(
            execution_id="exec-789",
            workflow_id="test",
            project_id=uuid4(),
            pgc_node_id="pgc",
            schema_ref="schema://test",
            questions=[],
            answers={},
        )
        # Explicitly set created_at to None (default is datetime.utcnow)
        answer.created_at = None

        result = answer.to_dict()

        assert result["created_at"] is None
