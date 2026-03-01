"""
Tier-1 tests for project_pure.py -- pure data transformations extracted from project_routes.

No DB, no I/O. All tests use plain dicts and simple stub objects.
WS-CRAP-006: Testability refactoring.
"""

from types import SimpleNamespace
from datetime import datetime, timezone

from app.web.routes.public.project_pure import (
    derive_documents_and_summary,
    derive_status_summary,
    normalize_document_status,
    validate_soft_delete,
)


# =============================================================================
# Helpers
# =============================================================================

def _make_doc_status(doc_type_id="doc1", title="Doc 1", icon="file",
                     readiness="ready", acceptance_state=None, subtitle=None):
    """Create a mock document status object with attributes."""
    return SimpleNamespace(
        doc_type_id=doc_type_id,
        title=title,
        icon=icon,
        readiness=readiness,
        acceptance_state=acceptance_state,
        subtitle=subtitle,
    )


# =============================================================================
# derive_status_summary
# =============================================================================

class TestDeriveStatusSummary:
    def test_empty_list(self):
        result = derive_status_summary([])
        assert result == {"ready": 0, "stale": 0, "blocked": 0, "waiting": 0, "needs_acceptance": 0}

    def test_all_ready(self):
        docs = [_make_doc_status(readiness="ready") for _ in range(3)]
        result = derive_status_summary(docs)
        assert result["ready"] == 3
        assert result["stale"] == 0

    def test_mixed_states(self):
        docs = [
            _make_doc_status(readiness="ready"),
            _make_doc_status(readiness="stale"),
            _make_doc_status(readiness="blocked"),
            _make_doc_status(readiness="waiting"),
            _make_doc_status(readiness="ready"),
        ]
        result = derive_status_summary(docs)
        assert result["ready"] == 2
        assert result["stale"] == 1
        assert result["blocked"] == 1
        assert result["waiting"] == 1

    def test_unknown_readiness_ignored(self):
        docs = [_make_doc_status(readiness="custom_state")]
        result = derive_status_summary(docs)
        assert all(v == 0 for v in result.values())

    def test_dict_items_with_readiness(self):
        docs = [{"readiness": "ready"}, {"readiness": "stale"}]
        result = derive_status_summary(docs)
        assert result["ready"] == 1
        assert result["stale"] == 1

    def test_dict_items_without_readiness(self):
        docs = [{"other_key": "value"}]
        result = derive_status_summary(docs)
        assert all(v == 0 for v in result.values())


# =============================================================================
# normalize_document_status
# =============================================================================

class TestNormalizeDocumentStatus:
    def test_object_with_readiness(self):
        doc = _make_doc_status(
            doc_type_id="intake",
            title="Intake",
            icon="clipboard",
            readiness="ready",
            acceptance_state="accepted",
            subtitle="v1.0",
        )
        result = normalize_document_status(doc)
        assert result["doc_type_id"] == "intake"
        assert result["title"] == "Intake"
        assert result["icon"] == "clipboard"
        assert result["readiness"] == "ready"
        assert result["acceptance_state"] == "accepted"
        assert result["subtitle"] == "v1.0"

    def test_dict_with_readiness(self):
        doc = {"readiness": "stale", "doc_type_id": "arch", "title": "Architecture",
               "icon": "building"}
        result = normalize_document_status(doc)
        assert result["readiness"] == "stale"
        assert result["doc_type_id"] == "arch"

    def test_dict_without_readiness(self):
        doc = {"some_key": "some_value"}
        result = normalize_document_status(doc)
        assert result == {"some_key": "some_value"}

    def test_object_without_readiness(self):
        doc = SimpleNamespace(name="test")
        result = normalize_document_status(doc)
        assert result == {}


# =============================================================================
# derive_documents_and_summary
# =============================================================================

class TestDeriveDocumentsAndSummary:
    def test_empty_list(self):
        docs, summary = derive_documents_and_summary([])
        assert docs == []
        assert summary["ready"] == 0

    def test_single_ready_doc(self):
        statuses = [_make_doc_status(readiness="ready", doc_type_id="intake")]
        docs, summary = derive_documents_and_summary(statuses)
        assert len(docs) == 1
        assert docs[0]["doc_type_id"] == "intake"
        assert summary["ready"] == 1

    def test_multiple_statuses(self):
        statuses = [
            _make_doc_status(readiness="ready"),
            _make_doc_status(readiness="stale"),
            _make_doc_status(readiness="blocked"),
        ]
        docs, summary = derive_documents_and_summary(statuses)
        assert len(docs) == 3
        assert summary["ready"] == 1
        assert summary["stale"] == 1
        assert summary["blocked"] == 1

    def test_mixed_with_no_readiness(self):
        """Items without readiness are passed through as-is."""
        statuses = [
            _make_doc_status(readiness="ready"),
            {"custom": "data"},
        ]
        docs, summary = derive_documents_and_summary(statuses)
        assert len(docs) == 2
        assert docs[0]["readiness"] == "ready"
        assert docs[1] == {"custom": "data"}
        assert summary["ready"] == 1


# =============================================================================
# validate_soft_delete
# =============================================================================

class TestValidateSoftDelete:
    def test_valid_delete(self):
        now = datetime.now(timezone.utc)
        result = validate_soft_delete(
            project_archived_at=now,
            project_deleted_at=None,
            confirmation="PRJ-001",
            project_id_upper="PRJ-001",
        )
        assert result is None  # No error

    def test_not_archived(self):
        result = validate_soft_delete(
            project_archived_at=None,
            project_deleted_at=None,
            confirmation="PRJ-001",
            project_id_upper="PRJ-001",
        )
        assert result == "Project must be archived before deletion"

    def test_already_deleted(self):
        now = datetime.now(timezone.utc)
        result = validate_soft_delete(
            project_archived_at=now,
            project_deleted_at=now,
            confirmation="PRJ-001",
            project_id_upper="PRJ-001",
        )
        assert result == "already_deleted"

    def test_confirmation_mismatch(self):
        now = datetime.now(timezone.utc)
        result = validate_soft_delete(
            project_archived_at=now,
            project_deleted_at=None,
            confirmation="WRONG",
            project_id_upper="PRJ-001",
        )
        assert result.startswith("confirmation_mismatch:")

    def test_confirmation_case_insensitive(self):
        now = datetime.now(timezone.utc)
        result = validate_soft_delete(
            project_archived_at=now,
            project_deleted_at=None,
            confirmation="prj-001",
            project_id_upper="PRJ-001",
        )
        assert result is None  # Passes (case-insensitive)

    def test_confirmation_strips_whitespace(self):
        now = datetime.now(timezone.utc)
        result = validate_soft_delete(
            project_archived_at=now,
            project_deleted_at=None,
            confirmation="  PRJ-001  ",
            project_id_upper="PRJ-001",
        )
        assert result is None  # Passes
