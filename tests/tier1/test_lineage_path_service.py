"""Tier-1 tests for lineage path computation (WP-LINEAGE-001 WS-2, ADR-067).

Pure unit tests — no DB, no LLM.
Tests path computation logic with in-memory document sets.
"""

from datetime import datetime, timezone, timedelta
from uuid import uuid4

from app.domain.services.lineage_path_service import (
    PathDocument,
    compute_lineage_path,
)


def _doc(
    doc_type_id="project_discovery",
    display_id="PD-001",
    version=1,
    is_latest=True,
    is_stale=False,
    parent_document_id=None,
    created_at=None,
    title=None,
):
    return PathDocument(
        id=uuid4(),
        doc_type_id=doc_type_id,
        display_id=display_id,
        version=version,
        title=title or f"{display_id} v{version}",
        is_latest=is_latest,
        is_stale=is_stale,
        lifecycle_state="complete",
        created_at=created_at or datetime.now(timezone.utc),
        parent_document_id=parent_document_id,
    )


class TestBasicPathComputation:
    def test_single_document_path(self):
        """Checkpoint alone produces a path with one document."""
        doc = _doc()
        path = compute_lineage_path(doc, [doc])
        assert len(path.documents) == 1
        assert path.checkpoint_id == doc.id
        assert path.is_active is True

    def test_checkpoint_fields(self):
        """Path carries checkpoint metadata."""
        doc = _doc(doc_type_id="implementation_plan", version=3)
        path = compute_lineage_path(doc, [doc])
        assert path.checkpoint_doc_type == "implementation_plan"
        assert path.checkpoint_version == 3

    def test_stage_summary(self):
        """Stage summary counts documents per stage."""
        t = datetime.now(timezone.utc)
        pd = _doc(doc_type_id="project_discovery", created_at=t)
        ip = _doc(doc_type_id="implementation_plan", parent_document_id=pd.id,
                  created_at=t + timedelta(seconds=1))
        path = compute_lineage_path(ip, [pd, ip])
        assert path.stage_summary["project_discovery"] == 1
        assert path.stage_summary["implementation_plan"] == 1


class TestUpstreamTraversal:
    def test_follows_parent_document_id_upstream(self):
        """Path includes parent documents via parent_document_id chain."""
        t = datetime.now(timezone.utc)
        pd = _doc(doc_type_id="project_discovery", created_at=t)
        ip = _doc(doc_type_id="implementation_plan",
                  parent_document_id=pd.id,
                  created_at=t + timedelta(seconds=1))
        path = compute_lineage_path(ip, [pd, ip])
        assert len(path.documents) == 2
        assert path.documents[0].doc_type_id == "project_discovery"
        assert path.documents[1].doc_type_id == "implementation_plan"

    def test_multi_stage_upstream(self):
        """Path traverses multiple upstream stages."""
        t = datetime.now(timezone.utc)
        ci = _doc(doc_type_id="concierge_intake", created_at=t)
        pd = _doc(doc_type_id="project_discovery",
                  parent_document_id=ci.id,
                  created_at=t + timedelta(seconds=1))
        ip = _doc(doc_type_id="implementation_plan",
                  parent_document_id=pd.id,
                  created_at=t + timedelta(seconds=2))
        path = compute_lineage_path(ip, [ci, pd, ip])
        assert len(path.documents) == 3
        types = [d.doc_type_id for d in path.documents]
        assert types == ["concierge_intake", "project_discovery", "implementation_plan"]


class TestDownstreamTraversal:
    def test_includes_downstream_children(self):
        """Path includes downstream documents linked by parent_document_id."""
        t = datetime.now(timezone.utc)
        ip = _doc(doc_type_id="implementation_plan", created_at=t)
        ta = _doc(doc_type_id="technical_architecture",
                  parent_document_id=ip.id,
                  created_at=t + timedelta(seconds=1))
        path = compute_lineage_path(ip, [ip, ta])
        assert len(path.documents) == 2
        assert path.documents[1].doc_type_id == "technical_architecture"

    def test_excludes_unrelated_downstream(self):
        """Documents not in the parent chain are excluded."""
        t = datetime.now(timezone.utc)
        ip = _doc(doc_type_id="implementation_plan", created_at=t)
        ta_related = _doc(doc_type_id="technical_architecture",
                          parent_document_id=ip.id,
                          created_at=t + timedelta(seconds=1))
        ta_unrelated = _doc(doc_type_id="technical_architecture",
                            display_id="TA-002",
                            created_at=t + timedelta(seconds=2))
        path = compute_lineage_path(ip, [ip, ta_related, ta_unrelated])
        assert len(path.documents) == 2
        assert ta_unrelated.id not in path.doc_ids


class TestVersioning:
    def test_active_when_checkpoint_is_latest(self):
        """Path is_active when checkpoint document has is_latest=True."""
        t = datetime.now(timezone.utc)
        pd = _doc(is_latest=True, created_at=t)
        ip = _doc(doc_type_id="implementation_plan", is_latest=True,
                  parent_document_id=pd.id,
                  created_at=t + timedelta(seconds=1))
        path = compute_lineage_path(ip, [pd, ip])
        assert path.is_active is True

    def test_not_active_when_checkpoint_not_latest(self):
        """Path is NOT active when checkpoint has is_latest=False."""
        t = datetime.now(timezone.utc)
        pd = _doc(is_latest=True, created_at=t)
        ip = _doc(doc_type_id="implementation_plan", is_latest=False,
                  parent_document_id=pd.id,
                  created_at=t + timedelta(seconds=1))
        path = compute_lineage_path(ip, [pd, ip])
        assert path.is_active is False

    def test_active_even_if_upstream_stale(self):
        """is_active depends on checkpoint only, not upstream docs."""
        t = datetime.now(timezone.utc)
        pd = _doc(is_latest=False, created_at=t)
        ip = _doc(doc_type_id="implementation_plan", is_latest=True,
                  parent_document_id=pd.id,
                  created_at=t + timedelta(seconds=1))
        path = compute_lineage_path(ip, [pd, ip])
        assert path.is_active is True


class TestSerialization:
    def test_to_dict(self):
        """Path serializes to dict with all expected fields."""
        doc = _doc()
        path = compute_lineage_path(doc, [doc])
        d = path.to_dict()
        assert "checkpoint_id" in d
        assert "checkpoint_doc_type" in d
        assert "checkpoint_version" in d
        assert "document_count" in d
        assert "is_active" in d
        assert "stage_summary" in d
        assert "documents" in d
        assert d["document_count"] == 1

    def test_path_document_to_dict(self):
        """PathDocument serializes correctly."""
        doc = _doc()
        d = doc.to_dict()
        assert "id" in d
        assert "doc_type_id" in d
        assert "display_id" in d
        assert "version" in d
        assert "is_latest" in d


class TestEdgeCases:
    def test_no_duplicates_in_path(self):
        """Path never contains the same document twice."""
        t = datetime.now(timezone.utc)
        pd = _doc(created_at=t)
        ip = _doc(doc_type_id="implementation_plan",
                  parent_document_id=pd.id,
                  created_at=t + timedelta(seconds=1))
        path = compute_lineage_path(ip, [pd, ip, pd])  # pd appears twice in input
        ids = [d.id for d in path.documents]
        assert len(ids) == len(set(ids))

    def test_empty_all_documents(self):
        """Checkpoint alone when no other documents exist."""
        doc = _doc()
        path = compute_lineage_path(doc, [doc])
        assert len(path.documents) == 1

    def test_sorted_by_stage_order(self):
        """Documents in path are sorted by pipeline stage order."""
        t = datetime.now(timezone.utc)
        ta = _doc(doc_type_id="technical_architecture",
                  created_at=t + timedelta(seconds=2))
        pd = _doc(doc_type_id="project_discovery", created_at=t)
        ip = _doc(doc_type_id="implementation_plan",
                  parent_document_id=pd.id,
                  created_at=t + timedelta(seconds=1))
        ta.parent_document_id = ip.id
        # Pass in reverse order
        path = compute_lineage_path(ip, [ta, ip, pd])
        types = [d.doc_type_id for d in path.documents]
        assert types == ["project_discovery", "implementation_plan", "technical_architecture"]
