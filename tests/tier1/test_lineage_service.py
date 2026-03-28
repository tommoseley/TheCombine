"""Tests for Lineage Service (WS-REWIND-006, WS-LINEAGE-001)."""

import pytest
from uuid import uuid4

from app.domain.models.lineage_event import LineageEvent
from app.domain.services.lineage_service import (
    InMemoryLineageRepository,
    LineageService,
    PostgresLineageRepository,
)


@pytest.fixture
def repo():
    return InMemoryLineageRepository()


@pytest.fixture
def service(repo):
    return LineageService(repository=repo)


@pytest.fixture
def project_id():
    return uuid4()


class TestRecordRewind:
    """Recording rewind events."""

    @pytest.mark.asyncio
    async def test_record_rewind_creates_event(self, service, project_id):
        doc_ids = [uuid4(), uuid4()]
        event = await service.record_rewind(
            project_id=project_id,
            rewind_to_stage="TA",
            reason="TA content updated",
            actor="user:tom",
            affected_document_ids=doc_ids,
        )
        assert event.event_type == "rewind"
        assert event.project_id == project_id
        assert event.rewind_to_stage == "TA"
        assert event.reason == "TA content updated"
        assert event.actor == "user:tom"
        assert event.affected_document_ids == doc_ids

    @pytest.mark.asyncio
    async def test_record_rewind_persists(self, service, repo, project_id):
        await service.record_rewind(
            project_id=project_id,
            rewind_to_stage="PD",
            reason="test",
            actor="test",
            affected_document_ids=[uuid4()],
        )
        events = await repo.get_by_project(project_id)
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_record_rewind_has_timestamp(self, service, project_id):
        event = await service.record_rewind(
            project_id=project_id,
            rewind_to_stage="TA",
            reason="test",
            actor="test",
            affected_document_ids=[],
        )
        assert event.created_at is not None

    @pytest.mark.asyncio
    async def test_record_rewind_has_unique_id(self, service, project_id):
        e1 = await service.record_rewind(
            project_id=project_id,
            rewind_to_stage="TA",
            reason="first",
            actor="test",
            affected_document_ids=[],
        )
        e2 = await service.record_rewind(
            project_id=project_id,
            rewind_to_stage="PD",
            reason="second",
            actor="test",
            affected_document_ids=[],
        )
        assert e1.id != e2.id


class TestRecordRegeneration:
    """Recording regeneration events."""

    @pytest.mark.asyncio
    async def test_record_regeneration_creates_event(self, service, project_id):
        new_ids = [uuid4()]
        event = await service.record_regeneration(
            project_id=project_id,
            from_stage="TA",
            reason="regenerating after rewind",
            actor="system",
            new_document_ids=new_ids,
        )
        assert event.event_type == "regeneration"
        assert event.rewind_to_stage == "TA"
        assert event.affected_document_ids == new_ids

    @pytest.mark.asyncio
    async def test_regeneration_persists(self, service, repo, project_id):
        await service.record_regeneration(
            project_id=project_id,
            from_stage="IP",
            reason="test",
            actor="test",
            new_document_ids=[uuid4()],
        )
        events = await repo.get_by_project(project_id)
        assert len(events) == 1
        assert events[0].event_type == "regeneration"


class TestGetProjectHistory:
    """Querying lineage history."""

    @pytest.mark.asyncio
    async def test_empty_project_returns_empty(self, service):
        events = await service.get_project_history(uuid4())
        assert events == []

    @pytest.mark.asyncio
    async def test_returns_events_newest_first(self, service, project_id):
        await service.record_rewind(
            project_id=project_id,
            rewind_to_stage="TA",
            reason="first",
            actor="test",
            affected_document_ids=[],
        )
        await service.record_rewind(
            project_id=project_id,
            rewind_to_stage="PD",
            reason="second",
            actor="test",
            affected_document_ids=[],
        )
        events = await service.get_project_history(project_id)
        assert len(events) == 2
        assert events[0].reason == "second"
        assert events[1].reason == "first"

    @pytest.mark.asyncio
    async def test_filter_by_event_type(self, service, project_id):
        await service.record_rewind(
            project_id=project_id,
            rewind_to_stage="TA",
            reason="rewind",
            actor="test",
            affected_document_ids=[],
        )
        await service.record_regeneration(
            project_id=project_id,
            from_stage="TA",
            reason="regen",
            actor="test",
            new_document_ids=[uuid4()],
        )
        rewinds = await service.get_project_history(project_id, event_type="rewind")
        assert len(rewinds) == 1
        assert rewinds[0].event_type == "rewind"

        regens = await service.get_project_history(
            project_id, event_type="regeneration"
        )
        assert len(regens) == 1
        assert regens[0].event_type == "regeneration"

    @pytest.mark.asyncio
    async def test_does_not_return_other_project_events(self, service):
        p1 = uuid4()
        p2 = uuid4()
        await service.record_rewind(
            project_id=p1,
            rewind_to_stage="TA",
            reason="p1 event",
            actor="test",
            affected_document_ids=[],
        )
        events = await service.get_project_history(p2)
        assert events == []


class TestGetEvent:
    """Single event retrieval."""

    @pytest.mark.asyncio
    async def test_get_existing_event(self, service, project_id):
        event = await service.record_rewind(
            project_id=project_id,
            rewind_to_stage="TA",
            reason="test",
            actor="test",
            affected_document_ids=[],
        )
        retrieved = await service.get_event(event.id)
        assert retrieved is not None
        assert retrieved.id == event.id

    @pytest.mark.asyncio
    async def test_get_nonexistent_event(self, service):
        retrieved = await service.get_event(uuid4())
        assert retrieved is None


class TestPostgresLineageRepositoryContract:
    """WS-LINEAGE-001: verify PostgresLineageRepository exists and follows Protocol."""

    def test_class_exists(self):
        """PostgresLineageRepository is importable."""
        assert PostgresLineageRepository is not None

    def test_has_save_method(self):
        """Repository has save() method."""
        assert hasattr(PostgresLineageRepository, "save")
        assert callable(getattr(PostgresLineageRepository, "save"))

    def test_has_get_by_project_method(self):
        """Repository has get_by_project() method."""
        assert hasattr(PostgresLineageRepository, "get_by_project")

    def test_has_get_by_id_method(self):
        """Repository has get_by_id() method."""
        assert hasattr(PostgresLineageRepository, "get_by_id")

    def test_constructor_accepts_db_session(self):
        """Constructor takes a db session parameter."""
        # Verify it can be instantiated with a mock db
        repo = PostgresLineageRepository(db=None)
        assert repo._db is None

    def test_to_domain_static_method_exists(self):
        """_to_domain helper for ORM → domain conversion."""
        assert hasattr(PostgresLineageRepository, "_to_domain")


class TestLineageEventModel:
    """LineageEvent dataclass behavior."""

    def test_create_rewind_event_factory(self):
        pid = uuid4()
        doc_ids = [uuid4(), uuid4()]
        event = LineageEvent.create_rewind_event(
            project_id=pid,
            rewind_to_stage="WP",
            reason="test reason",
            actor="user:admin",
            affected_document_ids=doc_ids,
        )
        assert event.event_type == "rewind"
        assert event.project_id == pid
        assert event.affected_document_ids == doc_ids
        assert event.regeneration_event_id is None

    def test_create_regeneration_event_factory(self):
        pid = uuid4()
        new_ids = [uuid4()]
        event = LineageEvent.create_regeneration_event(
            project_id=pid,
            from_stage="TA",
            reason="regen after rewind",
            actor="system",
            new_document_ids=new_ids,
        )
        assert event.event_type == "regeneration"
        assert event.affected_document_ids == new_ids
