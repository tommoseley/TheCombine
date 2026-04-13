"""Tier-1 tests for restore_preview_service (ADR-067 WS-6).

Tests the advisory restore impact evaluation.
"""

from datetime import datetime, timezone, timedelta
from uuid import uuid4

from app.domain.services.lineage_path_service import PathDocument, LineagePath
from app.domain.services.restore_preview_service import (
    evaluate_restore_preview,
    RestorePreview,
    RestoreWarning,
)


def _doc(
    doc_type_id="project_discovery",
    display_id="PD-001",
    version=1,
    is_latest=True,
    is_stale=False,
):
    return PathDocument(
        id=uuid4(),
        doc_type_id=doc_type_id,
        display_id=display_id,
        version=version,
        title=f"{display_id} v{version}",
        is_latest=is_latest,
        is_stale=is_stale,
        lifecycle_state="complete",
        created_at=datetime.now(timezone.utc),
    )


def _path(checkpoint, docs, is_active=False):
    return LineagePath(
        checkpoint_id=checkpoint.id,
        checkpoint_doc_type=checkpoint.doc_type_id,
        checkpoint_version=checkpoint.version,
        documents=docs,
        is_active=is_active,
    )


class TestRestorePreview:
    def test_no_changes_for_active_path(self):
        """Restoring the active path produces no activations or demotions."""
        pd = _doc(is_latest=True)
        ip = _doc(doc_type_id="implementation_plan", display_id="IP-001", is_latest=True)
        path = _path(ip, [pd, ip], is_active=True)
        current = [pd, ip]

        preview = evaluate_restore_preview(path, current)
        assert len(preview.documents_to_activate) == 0
        assert len(preview.documents_to_demote) == 0

    def test_activates_non_latest_path_docs(self):
        """Path docs that aren't is_latest should be in documents_to_activate."""
        pd_old = _doc(is_latest=False, version=1)
        pd_current = _doc(is_latest=True, version=2)
        path = _path(pd_old, [pd_old])
        current = [pd_current]

        preview = evaluate_restore_preview(path, current)
        assert len(preview.documents_to_activate) == 1
        assert preview.documents_to_activate[0]["id"] == str(pd_old.id)

    def test_demotes_current_docs_sharing_key(self):
        """Current docs sharing (doc_type, display_id) with path should be demoted."""
        pd_old = _doc(is_latest=False, version=1)
        pd_current = _doc(doc_type_id="project_discovery", display_id="PD-001",
                          is_latest=True, version=2)
        path = _path(pd_old, [pd_old])
        current = [pd_current]

        preview = evaluate_restore_preview(path, current)
        assert len(preview.documents_to_demote) == 1

    def test_warns_on_stale_docs_in_path(self):
        """Stale documents in path produce advisory warnings."""
        pd = _doc(is_latest=False, is_stale=True)
        path = _path(pd, [pd])

        preview = evaluate_restore_preview(path, [])
        stale_warnings = [w for w in preview.warnings if w.category == "stale_document"]
        assert len(stale_warnings) == 1
        assert preview.is_safe is False

    def test_warns_on_missing_upstream(self):
        """Missing upstream stages in path produce warnings."""
        # Path starts at IP — no CI or PD
        ip = _doc(doc_type_id="implementation_plan", display_id="IP-001",
                  is_latest=False, version=1)
        path = _path(ip, [ip])

        preview = evaluate_restore_preview(path, [])
        missing_warnings = [w for w in preview.warnings if w.category == "missing_upstream"]
        assert len(missing_warnings) >= 1  # At least CI and PD missing

    def test_safe_when_no_warnings(self):
        """Preview is_safe when no warnings — use CI (root stage) to avoid missing upstream."""
        ci = _doc(doc_type_id="concierge_intake", display_id="CI-001", is_latest=True)
        path = _path(ci, [ci])

        preview = evaluate_restore_preview(path, [ci])
        assert preview.is_safe is True

    def test_serialization(self):
        """Preview serializes to dict."""
        pd = _doc(is_latest=True)
        path = _path(pd, [pd])
        preview = evaluate_restore_preview(path, [pd])
        d = preview.to_dict()
        assert "checkpoint_id" in d
        assert "documents_to_activate" in d
        assert "documents_to_demote" in d
        assert "warnings" in d
        assert "is_safe" in d

    def test_warning_serialization(self):
        """Warning serializes correctly."""
        w = RestoreWarning(
            category="stale_document",
            message="PD-001 v1 was stale",
            document_id="abc",
            doc_type_id="project_discovery",
        )
        d = w.to_dict()
        assert d["category"] == "stale_document"
        assert d["document_id"] == "abc"
