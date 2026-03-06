"""Tier-1 tests for the project binder renderer (WS-RENDER-002).

Tests the binder assembly service that concatenates all project documents
into a single Markdown file with cover, TOC, and ordered sections.
No DB, no HTTP, no side effects.
"""

import pytest
from datetime import datetime, timezone

from app.domain.services.binder_renderer import render_project_binder


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _ia(label, *binds):
    """Minimal IA with one section."""
    return {
        "version": 2,
        "sections": [{"id": "s1", "label": label, "binds": list(binds)}],
    }


def _doc(display_id, doc_type_id, title, content, ia=None, ws_index=None):
    """Build a document dict as the binder renderer expects it."""
    d = {
        "display_id": display_id,
        "doc_type_id": doc_type_id,
        "title": title,
        "content": content,
        "ia": ia,
    }
    if ws_index is not None:
        d["ws_index"] = ws_index
    return d


# ---------------------------------------------------------------------------
# Cover + TOC
# ---------------------------------------------------------------------------

class TestCoverBlock:
    def test_cover_includes_project_id(self):
        md = render_project_binder(
            project_id="HWCA-001",
            project_title="Hello World CLI",
            documents=[],
        )
        assert "HWCA-001" in md

    def test_cover_includes_generated_at(self):
        md = render_project_binder(
            project_id="HWCA-001",
            project_title="Test",
            documents=[],
        )
        # Should contain an ISO-like timestamp
        assert "Generated:" in md

    def test_empty_project_produces_cover_only(self):
        md = render_project_binder(
            project_id="HWCA-001",
            project_title="Test",
            documents=[],
        )
        assert "HWCA-001" in md
        assert "No documents produced yet" in md


class TestTOC:
    def test_toc_entries_match_documents(self):
        docs = [
            _doc("PD-001", "project_discovery", "Project Discovery", {"summary": "Test"},
                 ia=_ia("Overview", {"path": "summary", "render_as": "paragraph"})),
        ]
        md = render_project_binder(
            project_id="HWCA-001",
            project_title="Test",
            documents=docs,
        )
        assert "## Table of Contents" in md
        assert "PD-001" in md


# ---------------------------------------------------------------------------
# Pipeline ordering
# ---------------------------------------------------------------------------

class TestPipelineOrdering:
    def test_documents_in_pipeline_order(self):
        """Documents appear in pipeline order regardless of input order."""
        docs = [
            _doc("TA-001", "technical_architecture", "Tech Arch", {"summary": "TA"},
                 ia=_ia("Overview", {"path": "summary", "render_as": "paragraph"})),
            _doc("CI-001", "concierge_intake", "Intake", {"summary": "CI"},
                 ia=_ia("Overview", {"path": "summary", "render_as": "paragraph"})),
            _doc("PD-001", "project_discovery", "Discovery", {"summary": "PD"},
                 ia=_ia("Overview", {"path": "summary", "render_as": "paragraph"})),
        ]
        md = render_project_binder(
            project_id="HWCA-001",
            project_title="Test",
            documents=docs,
        )
        pos_ci = md.index("CI-001")
        pos_pd = md.index("PD-001")
        pos_ta = md.index("TA-001")
        assert pos_ci < pos_pd < pos_ta

    def test_wps_sort_by_display_id(self):
        """WP documents sort by display_id ascending."""
        docs = [
            _doc("WP-002", "work_package", "WP Two", {"title": "Two"},
                 ia=_ia("Overview", {"path": "title", "render_as": "paragraph"})),
            _doc("WP-001", "work_package", "WP One", {"title": "One"},
                 ia=_ia("Overview", {"path": "title", "render_as": "paragraph"})),
        ]
        md = render_project_binder(
            project_id="HWCA-001",
            project_title="Test",
            documents=docs,
        )
        pos_wp1 = md.index("WP-001")
        pos_wp2 = md.index("WP-002")
        assert pos_wp1 < pos_wp2

    def test_ws_within_wp_sort_by_ws_index(self):
        """WSs within a WP sort by ws_index order, not display_id."""
        docs = [
            _doc("WP-001", "work_package", "Auth Package",
                 {"title": "Auth"},
                 ia=_ia("Overview", {"path": "title", "render_as": "paragraph"}),
                 ws_index=[
                     {"ws_id": "ws_beta", "order_key": "a0"},
                     {"ws_id": "ws_alpha", "order_key": "a1"},
                 ]),
            # WSs — note display_id order is opposite ws_index order
            _doc("WS-002", "work_statement", "Alpha Statement",
                 {"ws_id": "ws_alpha", "parent_wp_id": "wp_auth", "title": "Alpha"},
                 ia=_ia("Overview", {"path": "title", "render_as": "paragraph"})),
            _doc("WS-001", "work_statement", "Beta Statement",
                 {"ws_id": "ws_beta", "parent_wp_id": "wp_auth", "title": "Beta"},
                 ia=_ia("Overview", {"path": "title", "render_as": "paragraph"})),
        ]
        md = render_project_binder(
            project_id="HWCA-001",
            project_title="Test",
            documents=docs,
        )
        # ws_index says beta first, alpha second
        pos_beta = md.index("Beta Statement")
        pos_alpha = md.index("Alpha Statement")
        assert pos_beta < pos_alpha


# ---------------------------------------------------------------------------
# Single document + determinism
# ---------------------------------------------------------------------------

class TestSingleDocument:
    def test_single_document_renders_with_cover_toc_content(self):
        docs = [
            _doc("PD-001", "project_discovery", "Project Discovery",
                 {"summary": "A brief summary"},
                 ia=_ia("Overview", {"path": "summary", "render_as": "paragraph"})),
        ]
        md = render_project_binder(
            project_id="HWCA-001",
            project_title="Test",
            documents=docs,
        )
        # Cover
        assert "HWCA-001" in md
        # TOC
        assert "Table of Contents" in md
        # Content
        assert "A brief summary" in md


class TestDeterminism:
    def test_same_input_same_output(self):
        docs = [
            _doc("PD-001", "project_discovery", "Discovery",
                 {"summary": "Test"},
                 ia=_ia("Overview", {"path": "summary", "render_as": "paragraph"})),
        ]
        md1 = render_project_binder(
            project_id="HWCA-001",
            project_title="Test",
            documents=docs,
            generated_at="2026-03-05T14:30:00Z",
        )
        md2 = render_project_binder(
            project_id="HWCA-001",
            project_title="Test",
            documents=docs,
            generated_at="2026-03-05T14:30:00Z",
        )
        assert md1 == md2
