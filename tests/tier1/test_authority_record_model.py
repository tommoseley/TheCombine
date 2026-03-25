"""Tests for AuthorityRecord ORM model and AuthorityRecordDTO domain model.

WS-AUTH-001: Tier 1 verification criteria 1-6.
"""

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest


class TestAuthorityRecordDTO:
    """Criterion 2: Domain dataclass importable and well-formed."""

    def test_dto_importable(self):
        from app.domain.models.authority_record import AuthorityRecordDTO
        assert AuthorityRecordDTO is not None

    def test_dto_creates_with_required_fields(self):
        from app.domain.models.authority_record import AuthorityRecordDTO

        project_id = uuid4()
        execution_id = uuid4()
        dto = AuthorityRecordDTO(
            project_id=project_id,
            authority_type="pgc_answer",
            stage="PD",
            key="q_language",
            value="Python 3.12",
            source_execution_id=execution_id,
            lineage_path_id=execution_id,
            actor="user",
        )
        assert dto.project_id == project_id
        assert dto.authority_type == "pgc_answer"
        assert dto.stage == "PD"
        assert dto.key == "q_language"
        assert dto.value == "Python 3.12"
        assert dto.status == "current"
        assert dto.superseded_by is None
        assert dto.id is not None
        assert dto.created_at is not None

    def test_dto_status_defaults_to_current(self):
        from app.domain.models.authority_record import AuthorityRecordDTO

        dto = AuthorityRecordDTO(
            project_id=uuid4(),
            authority_type="pgc_answer",
            stage="PD",
            key="q1",
            value="v1",
            source_execution_id=uuid4(),
            lineage_path_id=uuid4(),
            actor="user",
        )
        assert dto.status == "current"

    def test_dto_accepts_all_status_values(self):
        from app.domain.models.authority_record import AuthorityRecordDTO

        for status in ("current", "superseded", "historical"):
            dto = AuthorityRecordDTO(
                project_id=uuid4(),
                authority_type="pgc_answer",
                stage="PD",
                key="q1",
                value="v1",
                source_execution_id=uuid4(),
                lineage_path_id=uuid4(),
                actor="user",
                status=status,
            )
            assert dto.status == status

    def test_dto_accepts_pgc_answer_type(self):
        from app.domain.models.authority_record import AuthorityRecordDTO

        dto = AuthorityRecordDTO(
            project_id=uuid4(),
            authority_type="pgc_answer",
            stage="PD",
            key="q1",
            value="v1",
            source_execution_id=uuid4(),
            lineage_path_id=uuid4(),
            actor="user",
        )
        assert dto.authority_type == "pgc_answer"

    def test_dto_value_accepts_complex_json(self):
        """Criterion 6: value stores arbitrary JSON."""
        from app.domain.models.authority_record import AuthorityRecordDTO

        complex_value = {
            "language": "Python",
            "version": "3.12",
            "features": ["async", "type hints"],
            "config": {"debug": True, "port": 8000},
        }
        dto = AuthorityRecordDTO(
            project_id=uuid4(),
            authority_type="pgc_answer",
            stage="PD",
            key="q_stack",
            value=complex_value,
            source_execution_id=uuid4(),
            lineage_path_id=uuid4(),
            actor="user",
        )
        assert dto.value == complex_value
        # Must be JSON-serializable
        json.dumps(dto.value)

    def test_dto_unique_ids(self):
        """Each DTO gets a unique id."""
        from app.domain.models.authority_record import AuthorityRecordDTO

        dto1 = AuthorityRecordDTO(
            project_id=uuid4(), authority_type="pgc_answer", stage="PD",
            key="q1", value="v1", source_execution_id=uuid4(),
            lineage_path_id=uuid4(), actor="user",
        )
        dto2 = AuthorityRecordDTO(
            project_id=uuid4(), authority_type="pgc_answer", stage="PD",
            key="q1", value="v1", source_execution_id=uuid4(),
            lineage_path_id=uuid4(), actor="user",
        )
        assert dto1.id != dto2.id


class TestAuthorityRecordORM:
    """Criterion 1: ORM model importable and well-formed."""

    def test_orm_importable(self):
        from app.api.models.authority_record import AuthorityRecord
        assert AuthorityRecord is not None

    def test_orm_tablename(self):
        from app.api.models.authority_record import AuthorityRecord
        assert AuthorityRecord.__tablename__ == "authority_records"

    def test_orm_has_all_adr064_columns(self):
        """Criterion 3: all columns from ADR-064 Section 4.2."""
        from app.api.models.authority_record import AuthorityRecord

        required_columns = [
            "id", "project_id", "authority_type", "stage", "key", "value",
            "source_execution_id", "lineage_path_id", "status",
            "superseded_by", "created_at", "actor",
        ]
        table_columns = {c.name for c in AuthorityRecord.__table__.columns}
        for col in required_columns:
            assert col in table_columns, f"Missing column: {col}"

    def test_orm_value_is_jsonb(self):
        """Criterion 6: value column is JSONB."""
        from app.api.models.authority_record import AuthorityRecord
        from sqlalchemy.dialects.postgresql import JSONB

        col = AuthorityRecord.__table__.columns["value"]
        assert isinstance(col.type, JSONB)

    def test_orm_has_indexes(self):
        """Verify the three required indexes exist."""
        from app.api.models.authority_record import AuthorityRecord

        index_names = {idx.name for idx in AuthorityRecord.__table__.indexes}
        assert "idx_authority_project_status" in index_names
        assert "idx_authority_supersession" in index_names
        assert "idx_authority_lineage_path" in index_names

    def test_orm_registered_in_init_database(self):
        """ORM model is imported in init_database()."""
        import inspect
        from app.core.database import init_database

        source = inspect.getsource(init_database)
        assert "AuthorityRecord" in source


class TestAlembicMigration:
    """Criteria 7-8: migration applies and downgrades cleanly.

    These are structural tests — they verify the migration file
    exists and has the correct revision chain. Actual DB application
    is verified at Tier 3 / deploy time.
    """

    def test_migration_file_exists(self):
        from pathlib import Path
        migration = Path(__file__).parent.parent.parent / (
            "alembic/versions/20260323_001_authority_records.py"
        )
        assert migration.exists(), "Migration file not found"

    def test_migration_revision_chain(self):
        from pathlib import Path
        migration = Path(__file__).parent.parent.parent / (
            "alembic/versions/20260323_001_authority_records.py"
        )
        content = migration.read_text()
        assert "revision = '20260323_001'" in content
        assert "down_revision = '20260321_001'" in content

    def test_migration_has_upgrade_and_downgrade(self):
        from pathlib import Path
        migration = Path(__file__).parent.parent.parent / (
            "alembic/versions/20260323_001_authority_records.py"
        )
        content = migration.read_text()
        assert "def upgrade()" in content
        assert "def downgrade()" in content
        assert "authority_records" in content
