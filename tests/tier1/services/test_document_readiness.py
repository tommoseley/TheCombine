"""Tier-1 tests for document_readiness.py.

Pure predicate tests -- no DB, no I/O, no filesystem.
Tests the mechanical document readiness gate for downstream consumption.

WS-WB-020: Define Mechanical Document Readiness Gate for TA Consumption.
"""

from dataclasses import dataclass

from app.domain.services.document_readiness import is_doc_ready_for_downstream


# =========================================================================
# Test fixtures -- lightweight duck-typed document stubs
# =========================================================================


@dataclass
class FakeDoc:
    """Minimal document-like object for testing."""
    status: str = "active"
    lifecycle_state: str = "complete"


# =========================================================================
# Happy path
# =========================================================================


class TestDocReadyHappyPath:
    """Document with status=active + lifecycle_state=complete is ready."""

    def test_active_complete_is_ready(self):
        doc = FakeDoc(status="active", lifecycle_state="complete")
        assert is_doc_ready_for_downstream(doc) is True


# =========================================================================
# Status rejections
# =========================================================================


class TestDocReadyStatusAcceptance:
    """Documents with lifecycle_state=complete and acceptable status are ready."""

    def test_draft_complete_is_ready(self):
        """Pipeline creates docs as status=draft; complete+draft must be ready."""
        doc = FakeDoc(status="draft", lifecycle_state="complete")
        assert is_doc_ready_for_downstream(doc) is True

    def test_active_complete_is_ready(self):
        doc = FakeDoc(status="active", lifecycle_state="complete")
        assert is_doc_ready_for_downstream(doc) is True

    def test_stale_complete_not_ready(self):
        doc = FakeDoc(status="stale", lifecycle_state="complete")
        assert is_doc_ready_for_downstream(doc) is False

    def test_archived_complete_not_ready(self):
        doc = FakeDoc(status="archived", lifecycle_state="complete")
        assert is_doc_ready_for_downstream(doc) is False


# =========================================================================
# Lifecycle state rejections
# =========================================================================


class TestDocReadyLifecycleRejections:
    """Documents with non-complete lifecycle_state are not ready."""

    def test_active_partial_not_ready(self):
        doc = FakeDoc(status="active", lifecycle_state="partial")
        assert is_doc_ready_for_downstream(doc) is False

    def test_active_generating_not_ready(self):
        doc = FakeDoc(status="active", lifecycle_state="generating")
        assert is_doc_ready_for_downstream(doc) is False

    def test_active_stale_lifecycle_not_ready(self):
        doc = FakeDoc(status="active", lifecycle_state="stale")
        assert is_doc_ready_for_downstream(doc) is False


# =========================================================================
# None input
# =========================================================================


class TestDocReadyNoneInput:
    """None document returns False."""

    def test_none_doc_returns_false(self):
        assert is_doc_ready_for_downstream(None) is False


# =========================================================================
# Missing attributes
# =========================================================================


class TestDocReadyMissingAttributes:
    """Documents missing required attributes return False."""

    def test_missing_lifecycle_state_returns_false(self):
        doc = type("BareDoc", (), {"status": "active"})()
        assert is_doc_ready_for_downstream(doc) is False

    def test_missing_status_returns_false(self):
        doc = type("BareDoc", (), {"lifecycle_state": "complete"})()
        assert is_doc_ready_for_downstream(doc) is False

    def test_missing_both_returns_false(self):
        doc = type("BareDoc", (), {"id": "some-id"})()
        assert is_doc_ready_for_downstream(doc) is False
