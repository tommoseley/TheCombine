"""Tests for AuthorityRepository protocol and InMemoryAuthorityRepository.

WS-AUTH-002: Tier 1 verification criteria 1-9.
"""

from uuid import uuid4

import pytest

from app.domain.models.authority_record import AuthorityRecordDTO
from app.domain.repositories.authority_repository import (
    AuthorityRepository,
    InMemoryAuthorityRepository,
    PostgresAuthorityRepository,
)


def _make_record(**overrides) -> AuthorityRecordDTO:
    """Helper to create an authority record with sensible defaults."""
    defaults = dict(
        project_id=uuid4(),
        authority_type="pgc_answer",
        stage="PD",
        key="q_language",
        value="Python 3.12",
        source_execution_id=uuid4(),
        lineage_path_id=uuid4(),
        actor="user",
    )
    defaults.update(overrides)
    return AuthorityRecordDTO(**defaults)


class TestProtocol:
    """Criterion 1: Protocol importable."""

    def test_protocol_importable(self):
        assert AuthorityRepository is not None

    def test_inmemory_implements_protocol(self):
        """Criterion 2: InMemoryAuthorityRepository satisfies Protocol."""
        repo = InMemoryAuthorityRepository()
        assert isinstance(repo, AuthorityRepository)


class TestPostgresRepoImportable:
    """Criterion 9: PostgresAuthorityRepository importable."""

    def test_postgres_repo_importable(self):
        assert PostgresAuthorityRepository is not None

    def test_postgres_repo_takes_session(self):
        """Constructor accepts a session-like object."""
        repo = PostgresAuthorityRepository(db="fake_session")
        assert repo._db == "fake_session"


class TestInMemoryAdd:
    """Criterion 3: add() persists and makes retrievable."""

    @pytest.mark.asyncio
    async def test_add_makes_retrievable(self):
        repo = InMemoryAuthorityRepository()
        record = _make_record()
        await repo.add(record)
        results = await repo.get_current_by_project(record.project_id)
        assert len(results) == 1
        assert results[0].id == record.id


class TestGetCurrentByProject:
    """Criterion 4: only returns status=current."""

    @pytest.mark.asyncio
    async def test_filters_by_status(self):
        repo = InMemoryAuthorityRepository()
        project_id = uuid4()

        current = _make_record(project_id=project_id, key="q1")
        superseded = _make_record(project_id=project_id, key="q2", status="superseded")
        historical = _make_record(project_id=project_id, key="q3", status="historical")

        await repo.add(current)
        await repo.add(superseded)
        await repo.add(historical)

        results = await repo.get_current_by_project(project_id)
        assert len(results) == 1
        assert results[0].key == "q1"

    @pytest.mark.asyncio
    async def test_returns_empty_for_unknown_project(self):
        repo = InMemoryAuthorityRepository()
        results = await repo.get_current_by_project(uuid4())
        assert results == []


class TestGetCurrentByProjectTypeKey:
    """Criterion 5: returns matching record for (project, type, key) triple."""

    @pytest.mark.asyncio
    async def test_returns_matching_record(self):
        repo = InMemoryAuthorityRepository()
        project_id = uuid4()
        record = _make_record(project_id=project_id, key="q_lang")
        await repo.add(record)

        result = await repo.get_current_by_project_type_key(
            project_id, "pgc_answer", "q_lang"
        )
        assert result is not None
        assert result.id == record.id

    @pytest.mark.asyncio
    async def test_returns_none_for_wrong_type(self):
        repo = InMemoryAuthorityRepository()
        project_id = uuid4()
        record = _make_record(project_id=project_id, authority_type="pgc_answer", key="q1")
        await repo.add(record)

        result = await repo.get_current_by_project_type_key(
            project_id, "bound_constraint", "q1"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_superseded(self):
        repo = InMemoryAuthorityRepository()
        project_id = uuid4()
        record = _make_record(project_id=project_id, key="q1", status="superseded")
        await repo.add(record)

        result = await repo.get_current_by_project_type_key(
            project_id, "pgc_answer", "q1"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_no_match(self):
        repo = InMemoryAuthorityRepository()
        result = await repo.get_current_by_project_type_key(
            uuid4(), "pgc_answer", "nonexistent"
        )
        assert result is None


class TestGetByLineagePath:
    """Criterion 6: returns all records on a lineage path."""

    @pytest.mark.asyncio
    async def test_returns_all_statuses_on_path(self):
        repo = InMemoryAuthorityRepository()
        path_id = uuid4()

        r1 = _make_record(lineage_path_id=path_id, key="q1")
        r2 = _make_record(lineage_path_id=path_id, key="q2", status="superseded")
        r3 = _make_record(lineage_path_id=uuid4(), key="q3")  # different path

        await repo.add(r1)
        await repo.add(r2)
        await repo.add(r3)

        results = await repo.get_by_lineage_path(path_id)
        assert len(results) == 2
        result_ids = {r.id for r in results}
        assert r1.id in result_ids
        assert r2.id in result_ids
        assert r3.id not in result_ids


class TestUpdateStatus:
    """Criteria 7-8: update_status changes status and handles nonexistent."""

    @pytest.mark.asyncio
    async def test_updates_status(self):
        repo = InMemoryAuthorityRepository()
        record = _make_record()
        await repo.add(record)

        updated = await repo.update_status(record.id, "superseded")
        assert updated is not None
        assert updated.status == "superseded"

    @pytest.mark.asyncio
    async def test_sets_superseded_by(self):
        repo = InMemoryAuthorityRepository()
        record = _make_record()
        new_id = uuid4()
        await repo.add(record)

        updated = await repo.update_status(record.id, "superseded", superseded_by=new_id)
        assert updated is not None
        assert updated.superseded_by == new_id

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent(self):
        """Criterion 8: nonexistent record returns None."""
        repo = InMemoryAuthorityRepository()
        result = await repo.update_status(uuid4(), "superseded")
        assert result is None
