"""Tests for WS-ID-001: Document Identity Standard schema changes.

Validates ADR-055 model and configuration changes:
- Document model has display_id column (NOT NULL)
- Document model __table_args__ defines idx_documents_latest_display
- DocumentType model has display_prefix column, no instance_key
- DocumentType.to_dict() includes display_prefix, excludes instance_key
- instance_id column unchanged (still nullable, still present)
- Package.yaml files use display_prefix instead of instance_key

No runtime, no DB, no LLM.
"""

from pathlib import Path

import yaml
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestDocumentModelIdentity:
    """Verify Document model has correct identity columns and indexes."""

    def test_display_id_column_exists(self):
        """display_id column exists on Document model."""
        from app.api.models.document import Document
        assert hasattr(Document, 'display_id'), "Document model missing display_id column"

    def test_display_id_is_not_nullable(self):
        """display_id column is NOT NULL."""
        from app.api.models.document import Document
        col = Document.__table__.columns['display_id']
        assert col.nullable is False, "display_id must be NOT NULL"

    def test_display_id_max_length(self):
        """display_id column has VARCHAR(20)."""
        from app.api.models.document import Document
        col = Document.__table__.columns['display_id']
        assert col.type.length == 20, f"display_id length should be 20, got {col.type.length}"

    def test_instance_id_still_exists(self):
        """instance_id column is unchanged (still present, still nullable)."""
        from app.api.models.document import Document
        assert hasattr(Document, 'instance_id'), "instance_id must still exist"
        col = Document.__table__.columns['instance_id']
        assert col.nullable is True, "instance_id must remain nullable"

    def test_latest_display_index_defined(self):
        """__table_args__ defines idx_documents_latest_display unique index."""
        from app.api.models.document import Document
        index_names = [idx.name for idx in Document.__table__.indexes]
        assert 'idx_documents_latest_display' in index_names, (
            f"idx_documents_latest_display not found in indexes: {index_names}"
        )

    def test_latest_display_index_is_unique(self):
        """idx_documents_latest_display is a unique index."""
        from app.api.models.document import Document
        for idx in Document.__table__.indexes:
            if idx.name == 'idx_documents_latest_display':
                assert idx.unique is True, "idx_documents_latest_display must be unique"
                return
        pytest.fail("idx_documents_latest_display index not found")

    def test_latest_display_index_columns(self):
        """idx_documents_latest_display covers (space_type, space_id, doc_type_id, display_id)."""
        from app.api.models.document import Document
        for idx in Document.__table__.indexes:
            if idx.name == 'idx_documents_latest_display':
                col_names = [col.name for col in idx.columns]
                assert col_names == ['space_type', 'space_id', 'doc_type_id', 'display_id'], (
                    f"Index columns should be [space_type, space_id, doc_type_id, display_id], got {col_names}"
                )
                return
        pytest.fail("idx_documents_latest_display index not found")

    def test_stale_unique_latest_index_removed(self):
        """idx_documents_unique_latest (stale pre-ADR-055 index) is no longer in model."""
        from app.api.models.document import Document
        index_names = [idx.name for idx in Document.__table__.indexes]
        assert 'idx_documents_unique_latest' not in index_names, (
            "Stale idx_documents_unique_latest should be removed from model __table_args__"
        )


class TestDocumentTypeModelIdentity:
    """Verify DocumentType model has display_prefix and no instance_key."""

    def test_display_prefix_column_exists(self):
        """display_prefix column exists on DocumentType model."""
        from app.api.models.document_type import DocumentType
        assert hasattr(DocumentType, 'display_prefix'), "DocumentType model missing display_prefix"

    def test_display_prefix_is_not_nullable(self):
        """display_prefix column is NOT NULL."""
        from app.api.models.document_type import DocumentType
        col = DocumentType.__table__.columns['display_prefix']
        assert col.nullable is False, "display_prefix must be NOT NULL"

    def test_display_prefix_max_length(self):
        """display_prefix column has VARCHAR(4)."""
        from app.api.models.document_type import DocumentType
        col = DocumentType.__table__.columns['display_prefix']
        assert col.type.length == 4, f"display_prefix length should be 4, got {col.type.length}"

    def test_instance_key_column_removed(self):
        """instance_key column no longer exists on DocumentType model."""
        from app.api.models.document_type import DocumentType
        col_names = [col.name for col in DocumentType.__table__.columns]
        assert 'instance_key' not in col_names, (
            "instance_key column should be removed from DocumentType model"
        )

    def test_to_dict_includes_display_prefix(self):
        """to_dict() includes display_prefix."""
        from app.api.models.document_type import DocumentType
        import uuid
        dt = DocumentType(
            id=uuid.uuid4(),
            doc_type_id='test_type',
            name='Test',
            category='test',
            builder_role='test',
            builder_task='test',
            handler_id='test',
            display_prefix='WP',
            cardinality='single',
        )
        result = dt.to_dict()
        assert 'display_prefix' in result, "to_dict() must include display_prefix"
        assert result['display_prefix'] == 'WP'

    def test_to_dict_excludes_instance_key(self):
        """to_dict() does not include instance_key."""
        from app.api.models.document_type import DocumentType
        import uuid
        dt = DocumentType(
            id=uuid.uuid4(),
            doc_type_id='test_type',
            name='Test',
            category='test',
            builder_role='test',
            builder_task='test',
            handler_id='test',
            display_prefix='WP',
            cardinality='single',
        )
        result = dt.to_dict()
        assert 'instance_key' not in result, "to_dict() must not include instance_key"


class TestPackageYamlDisplayPrefix:
    """Verify package.yaml files use display_prefix instead of instance_key."""

    PACKAGE_YAML_PATHS = [
        "combine-config/document_types/work_package_candidate/releases/1.0.0/package.yaml",
        "combine-config/document_types/work_package/releases/1.0.0/package.yaml",
        "combine-config/document_types/work_package/releases/1.1.0/package.yaml",
        "combine-config/document_types/work_statement/releases/1.0.0/package.yaml",
        "combine-config/document_types/work_statement/releases/1.1.0/package.yaml",
    ]

    EXPECTED_PREFIXES = {
        "work_package_candidate": "WPC",
        "work_package": "WP",
        "work_statement": "WS",
    }

    @pytest.mark.parametrize("rel_path", PACKAGE_YAML_PATHS)
    def test_no_instance_key(self, rel_path):
        """package.yaml does not contain instance_key."""
        path = REPO_ROOT / rel_path
        data = yaml.safe_load(path.read_text())
        assert 'instance_key' not in data, (
            f"{rel_path} still contains instance_key — should use display_prefix"
        )

    @pytest.mark.parametrize("rel_path", PACKAGE_YAML_PATHS)
    def test_has_display_prefix(self, rel_path):
        """package.yaml contains display_prefix with correct value."""
        path = REPO_ROOT / rel_path
        data = yaml.safe_load(path.read_text())
        assert 'display_prefix' in data, f"{rel_path} missing display_prefix"
        doc_type_id = data['doc_type_id']
        expected = self.EXPECTED_PREFIXES.get(doc_type_id)
        if expected:
            assert data['display_prefix'] == expected, (
                f"{rel_path}: display_prefix should be {expected}, got {data['display_prefix']}"
            )


class TestMigrationFileExists:
    """Verify the migration file exists with correct revision chain."""

    def test_migration_file_exists(self):
        """Alembic migration 20260304_001 exists."""
        path = REPO_ROOT / "alembic" / "versions" / "20260304_001_document_identity_standard.py"
        assert path.exists(), "Migration file 20260304_001_document_identity_standard.py not found"

    def test_migration_revision_chain(self):
        """Migration revises 20260301_001 (current head)."""
        path = REPO_ROOT / "alembic" / "versions" / "20260304_001_document_identity_standard.py"
        content = path.read_text()
        assert "revision: str = '20260304_001'" in content
        assert "down_revision: Union[str, None] = '20260301_001'" in content
