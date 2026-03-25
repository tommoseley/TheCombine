"""Tests for Progression Guard (WS-REWIND-012)."""

import pytest
from uuid import uuid4

from app.domain.services.progression_guard import (
    check_documents_current,
    check_document_promotable,
)
from app.domain.models.rewind_errors import STALE_INPUT
from app.persistence.models import DocumentStatus, StoredDocument


def _make_doc(status=DocumentStatus.ACTIVE, doc_type="technical_architecture"):
    return StoredDocument.create(
        document_type=doc_type,
        scope_type="project",
        scope_id=str(uuid4()),
        title="Test",
        content={},
        status=status,
    )


class TestCheckDocumentsCurrent:
    """Only current documents should pass."""

    def test_all_active_passes(self):
        docs = [_make_doc(DocumentStatus.ACTIVE), _make_doc(DocumentStatus.DRAFT)]
        result = check_documents_current(docs)
        assert result.passed
        assert result.errors == []

    def test_stale_document_fails(self):
        docs = [_make_doc(DocumentStatus.ACTIVE), _make_doc(DocumentStatus.STALE)]
        result = check_documents_current(docs)
        assert not result.passed
        assert len(result.errors) == 1
        assert result.errors[0].error_code == STALE_INPUT

    def test_archived_document_fails(self):
        docs = [_make_doc(DocumentStatus.ARCHIVED)]
        result = check_documents_current(docs)
        assert not result.passed

    def test_empty_list_passes(self):
        result = check_documents_current([])
        assert result.passed

    def test_multiple_stale_returns_multiple_errors(self):
        docs = [
            _make_doc(DocumentStatus.STALE),
            _make_doc(DocumentStatus.STALE),
            _make_doc(DocumentStatus.ACTIVE),
        ]
        result = check_documents_current(docs)
        assert not result.passed
        assert len(result.errors) == 2

    def test_error_includes_document_type(self):
        doc = _make_doc(DocumentStatus.STALE, doc_type="work_package")
        result = check_documents_current([doc])
        assert result.errors[0].document_type == "work_package"

    def test_error_includes_document_id(self):
        doc = _make_doc(DocumentStatus.STALE)
        result = check_documents_current([doc])
        assert result.errors[0].document_id == doc.document_id


class TestCheckDocumentPromotable:
    """Promotion/stabilization requires current status."""

    def test_active_is_promotable(self):
        doc = _make_doc(DocumentStatus.ACTIVE)
        result = check_document_promotable(doc)
        assert result.passed

    def test_draft_is_promotable(self):
        doc = _make_doc(DocumentStatus.DRAFT)
        result = check_document_promotable(doc)
        assert result.passed

    def test_stale_is_not_promotable(self):
        doc = _make_doc(DocumentStatus.STALE)
        result = check_document_promotable(doc)
        assert not result.passed
        assert result.errors[0].error_code == STALE_INPUT

    def test_archived_is_not_promotable(self):
        doc = _make_doc(DocumentStatus.ARCHIVED)
        result = check_document_promotable(doc)
        assert not result.passed

    def test_error_message_mentions_promote(self):
        doc = _make_doc(DocumentStatus.STALE)
        result = check_document_promotable(doc)
        assert "promote" in result.errors[0].message.lower()
