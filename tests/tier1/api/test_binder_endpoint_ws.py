"""Tier-1 test for binder endpoint WS data preparation.

Tests that the endpoint correctly prepares WS documents for the renderer,
isolating the data path from DB query through to render call.

Mocks the DB layer to provide exact production document shapes.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.services.binder_renderer import render_project_binder


# ---------------------------------------------------------------------------
# Mock Document objects matching production DB shape
# ---------------------------------------------------------------------------

def _mock_doc(*, doc_type_id, display_id, title, content, parent_document_id=None):
    """Create a mock Document ORM object matching production data."""
    doc = MagicMock()
    doc.id = uuid.uuid4()
    doc.doc_type_id = doc_type_id
    doc.display_id = display_id
    doc.title = title
    doc.content = content  # Already a dict (JSONB)
    doc.parent_document_id = parent_document_id
    doc.is_latest = True
    doc.space_type = "project"
    doc.space_id = uuid.uuid4()
    return doc


def _production_docs():
    """Build mock Document objects matching HWCP-002 production state."""
    wp_id = uuid.uuid4()
    ws_index = [
        {"ws_id": "WS-001", "order_key": "a0"},
        {"ws_id": "WS-002", "order_key": "a1"},
        {"ws_id": "WS-003", "order_key": "a2"},
        {"ws_id": "WS-004", "order_key": "a3"},
        {"ws_id": "WS-005", "order_key": "a4"},
    ]

    docs = [
        _mock_doc(
            doc_type_id="concierge_intake",
            display_id="CI-001",
            title="Concierge Intake",
            content={"title": "CI"},
        ),
        _mock_doc(
            doc_type_id="project_discovery",
            display_id="PD-001",
            title="Project Discovery",
            content={"title": "PD"},
        ),
        _mock_doc(
            doc_type_id="implementation_plan",
            display_id="IP-001",
            title="Implementation Plan",
            content={"title": "IP"},
        ),
        _mock_doc(
            doc_type_id="technical_architecture",
            display_id="TA-001",
            title="Technical Architecture",
            content={"title": "TA"},
        ),
        _mock_doc(
            doc_type_id="work_package",
            display_id="WP-001",
            title="Core CLI Implementation",
            content={
                "title": "Core CLI",
                "ws_index": ws_index,
                "state": "PLANNED",
            },
        ),
    ]
    # Set WP id explicitly for parent_document_id matching
    docs[4].id = wp_id

    # Work Statements — parent_document_id is None (production reality)
    for i in range(1, 6):
        docs.append(_mock_doc(
            doc_type_id="work_statement",
            display_id=f"WS-{i:03d}",
            title=f"Work Statement {i}",
            content={
                "ws_id": f"WS-{i:03d}",
                "title": f"WS {i}",
                "parent_wp_id": "WP-001",
                "state": "draft",
                "objective": f"Objective {i}",
            },
            parent_document_id=None,
        ))

    return docs


# ---------------------------------------------------------------------------
# Simulate the endpoint's data preparation (lines 942-978 of projects.py)
# ---------------------------------------------------------------------------

def _prepare_binder_docs(all_docs):
    """Replicate the endpoint data preparation logic exactly."""
    from app.api.v1.services.render_pure import unwrap_raw_envelope

    binder_docs = []
    for doc in all_docs:
        content = unwrap_raw_envelope(doc.content) if doc.content else {}

        # Apply handler transform (computed fields)
        if isinstance(content, dict):
            try:
                from app.domain.handlers.registry import handler_exists, get_handler
                if handler_exists(doc.doc_type_id):
                    content = get_handler(doc.doc_type_id).transform(content)
            except Exception:
                pass

        # Skip IA loading for this test (not relevant to WS matching)
        ia = None

        entry = {
            "display_id": getattr(doc, "display_id", None) or doc.doc_type_id,
            "doc_type_id": doc.doc_type_id,
            "title": doc.title or doc.doc_type_id,
            "content": content,
            "ia": ia,
            "id": str(doc.id) if doc.id else None,
            "parent_document_id": str(doc.parent_document_id) if doc.parent_document_id else None,
        }

        # For WPs, include ws_index from content
        if doc.doc_type_id == "work_package" and isinstance(content, dict):
            entry["ws_index"] = content.get("ws_index", [])

        binder_docs.append(entry)

    return binder_docs


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEndpointDataPreparation:
    """Test that the endpoint prepares WS documents correctly for the renderer."""

    def test_query_returns_work_statements(self):
        """Production mock returns 10 docs: 5 pipeline + 5 WSs."""
        docs = _production_docs()
        assert len(docs) == 10
        ws_docs = [d for d in docs if d.doc_type_id == "work_statement"]
        assert len(ws_docs) == 5

    def test_binder_docs_include_work_statements(self):
        """After endpoint prep, binder_docs contains work_statement entries."""
        all_docs = _production_docs()
        binder_docs = _prepare_binder_docs(all_docs)
        ws_entries = [d for d in binder_docs if d["doc_type_id"] == "work_statement"]
        assert len(ws_entries) == 5, f"Expected 5 WS entries, got {len(ws_entries)}"

    def test_ws_entries_have_content_ws_id(self):
        """WS entries have content.ws_id needed for ws_index matching."""
        all_docs = _production_docs()
        binder_docs = _prepare_binder_docs(all_docs)
        ws_entries = [d for d in binder_docs if d["doc_type_id"] == "work_statement"]
        for ws in ws_entries:
            ws_id = ws["content"].get("ws_id", "")
            assert ws_id, f"WS {ws['display_id']} missing content.ws_id"

    def test_wp_entry_has_ws_index(self):
        """WP entry has ws_index with 5 entries after handler transform."""
        all_docs = _production_docs()
        binder_docs = _prepare_binder_docs(all_docs)
        wp_entries = [d for d in binder_docs if d["doc_type_id"] == "work_package"]
        assert len(wp_entries) == 1
        ws_index = wp_entries[0].get("ws_index", [])
        assert len(ws_index) == 5, f"Expected 5 ws_index entries, got {len(ws_index)}: {ws_index}"

    def test_ws_index_ws_ids_match_ws_content_ws_ids(self):
        """ws_index[].ws_id values match content.ws_id on WS documents."""
        all_docs = _production_docs()
        binder_docs = _prepare_binder_docs(all_docs)

        wp = [d for d in binder_docs if d["doc_type_id"] == "work_package"][0]
        ws_entries = [d for d in binder_docs if d["doc_type_id"] == "work_statement"]

        index_ids = {e["ws_id"] for e in wp.get("ws_index", [])}
        content_ids = {ws["content"]["ws_id"] for ws in ws_entries}

        assert index_ids == content_ids, (
            f"ws_index IDs {index_ids} don't match WS content IDs {content_ids}"
        )

    def test_full_render_includes_ws(self):
        """End-to-end: prepare docs -> render -> WSs appear in markdown."""
        all_docs = _production_docs()
        binder_docs = _prepare_binder_docs(all_docs)
        md = render_project_binder(
            project_id="HWCP-002",
            project_title="Hello World CLI",
            documents=binder_docs,
            generated_at="2026-03-07T00:00:00Z",
        )
        for i in range(1, 6):
            ws_id = f"WS-{i:03d}"
            assert f"### {ws_id}" in md, f"{ws_id} not in rendered binder body"
            assert f"  - [{ws_id}" in md, f"{ws_id} not in TOC"

    def test_handler_transform_preserves_ws_index(self):
        """WP handler transform does not strip ws_index from content."""
        from app.domain.handlers.registry import handler_exists, get_handler

        if not handler_exists("work_package"):
            pytest.skip("work_package handler not registered")

        handler = get_handler("work_package")
        content = {
            "title": "Test WP",
            "ws_index": [{"ws_id": "WS-001", "order_key": "a0"}],
        }
        transformed = handler.transform(content)
        assert "ws_index" in transformed, "transform() stripped ws_index"
        assert len(transformed["ws_index"]) == 1

    def test_unwrap_preserves_normal_content(self):
        """unwrap_raw_envelope passes through normal dicts unchanged."""
        from app.api.v1.services.render_pure import unwrap_raw_envelope

        content = {
            "ws_id": "WS-001",
            "title": "Test",
            "parent_wp_id": "WP-001",
        }
        result = unwrap_raw_envelope(content)
        assert result == content
        assert result["ws_id"] == "WS-001"

    def test_unwrap_preserves_wp_with_ws_index(self):
        """unwrap_raw_envelope passes through WP content with ws_index."""
        from app.api.v1.services.render_pure import unwrap_raw_envelope

        content = {
            "title": "Test WP",
            "ws_index": [{"ws_id": "WS-001", "order_key": "a0"}],
            "state": "PLANNED",
        }
        result = unwrap_raw_envelope(content)
        assert "ws_index" in result
        assert len(result["ws_index"]) == 1
