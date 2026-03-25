"""Tests for AuthorityService.

WS-AUTH-003: Tier 1 verification criteria 1-11.
"""

from uuid import uuid4

import pytest

from app.domain.models.authority_record import AuthorityRecordDTO
from app.domain.repositories.authority_repository import InMemoryAuthorityRepository
from app.domain.services.authority_service import AuthorityService


def _make_service() -> tuple:
    """Create service with in-memory repo."""
    repo = InMemoryAuthorityRepository()
    service = AuthorityService(repo)
    return service, repo


@pytest.fixture
def service_and_repo():
    return _make_service()


class TestRecordAuthority:
    """Criteria 1-4: record_authority creates, supersedes, respects type scope."""

    @pytest.mark.asyncio
    async def test_creates_current_record(self):
        """Criterion 1: new record has status=current."""
        service, repo = _make_service()
        project_id = uuid4()
        exec_id = uuid4()

        record = await service.record_authority(
            project_id=project_id,
            authority_type="pgc_answer",
            stage="PD",
            key="q_language",
            value="Python 3.12",
            source_execution_id=exec_id,
            lineage_path_id=exec_id,
            actor="user",
        )

        assert record.status == "current"
        assert record.project_id == project_id
        assert record.key == "q_language"
        assert record.value == "Python 3.12"

    @pytest.mark.asyncio
    async def test_supersedes_existing_same_type_key(self):
        """Criterion 2: supersedes existing for same (project, type, key)."""
        service, repo = _make_service()
        project_id = uuid4()
        exec_id = uuid4()

        old = await service.record_authority(
            project_id=project_id, authority_type="pgc_answer",
            stage="PD", key="q_lang", value="Python 3.11",
            source_execution_id=exec_id, lineage_path_id=exec_id, actor="user",
        )

        new = await service.record_authority(
            project_id=project_id, authority_type="pgc_answer",
            stage="PD", key="q_lang", value="Python 3.12",
            source_execution_id=exec_id, lineage_path_id=exec_id, actor="user",
        )

        # Old should be superseded
        records = await repo.get_by_lineage_path(exec_id)
        old_record = next(r for r in records if r.id == old.id)
        assert old_record.status == "superseded"
        assert old_record.superseded_by == new.id

        # New should be current
        assert new.status == "current"

    @pytest.mark.asyncio
    async def test_does_not_supersede_cross_type(self):
        """Criterion 3: pgc_answer with key=X does not supersede bound_constraint with key=X."""
        service, repo = _make_service()
        project_id = uuid4()
        exec_id = uuid4()

        pgc = await service.record_authority(
            project_id=project_id, authority_type="pgc_answer",
            stage="PD", key="shared_key", value="pgc_value",
            source_execution_id=exec_id, lineage_path_id=exec_id, actor="user",
        )

        constraint = await service.record_authority(
            project_id=project_id, authority_type="bound_constraint",
            stage="PD", key="shared_key", value="constraint_value",
            source_execution_id=exec_id, lineage_path_id=exec_id, actor="system",
        )

        # Both should be current — different authority types
        current = await service.get_current_authority(project_id)
        assert len(current) == 2
        current_ids = {r.id for r in current}
        assert pgc.id in current_ids
        assert constraint.id in current_ids

    @pytest.mark.asyncio
    async def test_does_not_supersede_historical(self):
        """Criterion 4: historical record not touched when new current created."""
        service, repo = _make_service()
        project_id = uuid4()
        exec_id = uuid4()

        # Create and mark as historical
        historical = AuthorityRecordDTO(
            project_id=project_id, authority_type="pgc_answer",
            stage="PD", key="q_lang", value="old_value",
            source_execution_id=exec_id, lineage_path_id=exec_id,
            actor="user", status="historical",
        )
        await repo.add(historical)

        # Create new current with same key
        new = await service.record_authority(
            project_id=project_id, authority_type="pgc_answer",
            stage="PD", key="q_lang", value="new_value",
            source_execution_id=exec_id, lineage_path_id=exec_id, actor="user",
        )

        # Historical should remain historical
        all_records = await repo.get_by_lineage_path(exec_id)
        hist = next(r for r in all_records if r.id == historical.id)
        assert hist.status == "historical"
        assert hist.superseded_by is None


class TestGetCurrentAuthority:
    """Criteria 5-6: filtering and empty project."""

    @pytest.mark.asyncio
    async def test_returns_only_current(self):
        """Criterion 5: filters out superseded and historical."""
        service, repo = _make_service()
        project_id = uuid4()
        exec_id = uuid4()

        await repo.add(AuthorityRecordDTO(
            project_id=project_id, authority_type="pgc_answer",
            stage="PD", key="q1", value="v1",
            source_execution_id=exec_id, lineage_path_id=exec_id,
            actor="user", status="current",
        ))
        await repo.add(AuthorityRecordDTO(
            project_id=project_id, authority_type="pgc_answer",
            stage="PD", key="q2", value="v2",
            source_execution_id=exec_id, lineage_path_id=exec_id,
            actor="user", status="superseded",
        ))
        await repo.add(AuthorityRecordDTO(
            project_id=project_id, authority_type="pgc_answer",
            stage="PD", key="q3", value="v3",
            source_execution_id=exec_id, lineage_path_id=exec_id,
            actor="user", status="historical",
        ))

        results = await service.get_current_authority(project_id)
        assert len(results) == 1
        assert results[0].key == "q1"

    @pytest.mark.asyncio
    async def test_returns_empty_for_unknown_project(self):
        """Criterion 6: returns empty list, not error."""
        service, _ = _make_service()
        results = await service.get_current_authority(uuid4())
        assert results == []


class TestGetAuthorityBundle:
    """Criteria 7-8: bundle structure and empty case."""

    @pytest.mark.asyncio
    async def test_structures_correctly(self):
        """Criterion 7: returns dict with canonical keys."""
        service, repo = _make_service()
        project_id = uuid4()
        exec_id = uuid4()

        await service.record_authority(
            project_id=project_id, authority_type="pgc_answer",
            stage="PD", key="q_lang", value="Python",
            source_execution_id=exec_id, lineage_path_id=exec_id, actor="user",
        )
        await service.record_authority(
            project_id=project_id, authority_type="pgc_answer",
            stage="PD", key="q_framework", value="FastAPI",
            source_execution_id=exec_id, lineage_path_id=exec_id, actor="user",
        )

        bundle = await service.get_authority_bundle(project_id)

        assert bundle["pgc_answers"] == {"q_lang": "Python", "q_framework": "FastAPI"}
        assert set(bundle["pgc_questions"]) == {"q_lang", "q_framework"}
        assert len(bundle["authority_record_ids"]) == 2
        assert bundle["authority_source"] == "durable_store"

    @pytest.mark.asyncio
    async def test_empty_bundle(self):
        """Criterion 8: empty authority returns correct structure."""
        service, _ = _make_service()
        bundle = await service.get_authority_bundle(uuid4())

        assert bundle["pgc_answers"] == {}
        assert bundle["pgc_questions"] == []
        assert bundle["authority_record_ids"] == []
        assert bundle["authority_source"] == "none"


class TestSupersedeRecord:
    """Criterion 9: supersede_record links records."""

    @pytest.mark.asyncio
    async def test_links_records(self):
        service, repo = _make_service()
        project_id = uuid4()
        exec_id = uuid4()

        old = AuthorityRecordDTO(
            project_id=project_id, authority_type="pgc_answer",
            stage="PD", key="q1", value="old",
            source_execution_id=exec_id, lineage_path_id=exec_id, actor="user",
        )
        new = AuthorityRecordDTO(
            project_id=project_id, authority_type="pgc_answer",
            stage="PD", key="q1", value="new",
            source_execution_id=exec_id, lineage_path_id=exec_id, actor="user",
        )
        await repo.add(old)
        await repo.add(new)

        result = await service.supersede_record(old.id, new.id)
        assert result is not None
        assert result.status == "superseded"
        assert result.superseded_by == new.id


class TestMarkPathHistorical:
    """Criteria 10-11: path-scoped historical marking."""

    @pytest.mark.asyncio
    async def test_marks_all_on_path(self):
        """Criterion 10: all records on path become historical."""
        service, repo = _make_service()
        path_id = uuid4()
        project_id = uuid4()

        r1 = AuthorityRecordDTO(
            project_id=project_id, authority_type="pgc_answer",
            stage="PD", key="q1", value="v1",
            source_execution_id=uuid4(), lineage_path_id=path_id, actor="user",
        )
        r2 = AuthorityRecordDTO(
            project_id=project_id, authority_type="pgc_answer",
            stage="PD", key="q2", value="v2",
            source_execution_id=uuid4(), lineage_path_id=path_id, actor="user",
        )
        await repo.add(r1)
        await repo.add(r2)

        count = await service.mark_path_historical(path_id)
        assert count == 2

        path_records = await repo.get_by_lineage_path(path_id)
        assert all(r.status == "historical" for r in path_records)

    @pytest.mark.asyncio
    async def test_does_not_affect_other_paths(self):
        """Criterion 11: records on different paths unchanged."""
        service, repo = _make_service()
        path_a = uuid4()
        path_b = uuid4()
        project_id = uuid4()

        r_a = AuthorityRecordDTO(
            project_id=project_id, authority_type="pgc_answer",
            stage="PD", key="q1", value="v1",
            source_execution_id=uuid4(), lineage_path_id=path_a, actor="user",
        )
        r_b = AuthorityRecordDTO(
            project_id=project_id, authority_type="pgc_answer",
            stage="PD", key="q2", value="v2",
            source_execution_id=uuid4(), lineage_path_id=path_b, actor="user",
        )
        await repo.add(r_a)
        await repo.add(r_b)

        await service.mark_path_historical(path_a)

        # Path B should be unaffected
        path_b_records = await repo.get_by_lineage_path(path_b)
        assert all(r.status == "current" for r in path_b_records)

    @pytest.mark.asyncio
    async def test_skips_already_historical(self):
        """Already-historical records are not double-marked."""
        service, repo = _make_service()
        path_id = uuid4()

        r1 = AuthorityRecordDTO(
            project_id=uuid4(), authority_type="pgc_answer",
            stage="PD", key="q1", value="v1",
            source_execution_id=uuid4(), lineage_path_id=path_id,
            actor="user", status="historical",
        )
        await repo.add(r1)

        count = await service.mark_path_historical(path_id)
        assert count == 0
