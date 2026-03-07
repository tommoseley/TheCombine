"""Tier-1 tests for WS inclusion in project binder (WS-RENDER-005).

Verifies that Work Statement documents appear in binder output nested under
their parent Work Package, using ws_index matching as the primary path and
parent_document_id as a fallback.

No DB, no HTTP, no side effects.
"""

import pytest

from app.domain.services.binder_renderer import render_project_binder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ia(label, *binds):
    """Minimal IA with one section."""
    return {
        "version": 2,
        "sections": [{"id": "s1", "label": label, "binds": list(binds)}],
    }


def _doc(display_id, doc_type_id, title, content, ia=None, ws_index=None,
         id=None, parent_document_id=None):
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
    if id is not None:
        d["id"] = id
    if parent_document_id is not None:
        d["parent_document_id"] = parent_document_id
    return d


_SIMPLE_IA = _ia("Overview", {"path": "title", "render_as": "paragraph"})

FIXED_TS = "2026-03-06T12:00:00Z"


# ---------------------------------------------------------------------------
# WS inclusion via ws_index matching (primary path)
# ---------------------------------------------------------------------------

class TestWSInclusionViaWSIndex:
    """WSs matched to WPs via ws_index[].ws_id -> content.ws_id."""

    def test_binder_includes_ws_nested_under_wp(self):
        """WP-001 with WS-001 and WS-002 -> output includes all three."""
        docs = [
            _doc("WP-001", "work_package", "Auth Package",
                 {"title": "Auth", "ws_index": [
                     {"ws_id": "ws_login", "order_key": "a0"},
                     {"ws_id": "ws_logout", "order_key": "a1"},
                 ]},
                 ia=_SIMPLE_IA,
                 ws_index=[
                     {"ws_id": "ws_login", "order_key": "a0"},
                     {"ws_id": "ws_logout", "order_key": "a1"},
                 ],
                 id="wp-uuid-001"),
            _doc("WS-001", "work_statement", "Login Flow",
                 {"ws_id": "ws_login", "parent_wp_id": "wp_auth", "title": "Login"},
                 ia=_SIMPLE_IA,
                 parent_document_id="wp-uuid-001"),
            _doc("WS-002", "work_statement", "Logout Flow",
                 {"ws_id": "ws_logout", "parent_wp_id": "wp_auth", "title": "Logout"},
                 ia=_SIMPLE_IA,
                 parent_document_id="wp-uuid-001"),
        ]
        md = render_project_binder(
            project_id="HWCA-001",
            project_title="Test",
            documents=docs,
            generated_at=FIXED_TS,
        )
        assert "WP-001" in md
        assert "WS-001" in md
        assert "WS-002" in md

    def test_ws_appears_after_parent_wp(self):
        """WS content appears after its parent WP, not before or at end."""
        docs = [
            _doc("CI-001", "concierge_intake", "Intake",
                 {"title": "CI"},
                 ia=_SIMPLE_IA),
            _doc("WP-001", "work_package", "Auth Package",
                 {"title": "Auth", "ws_index": [
                     {"ws_id": "ws_login", "order_key": "a0"},
                 ]},
                 ia=_SIMPLE_IA,
                 ws_index=[
                     {"ws_id": "ws_login", "order_key": "a0"},
                 ],
                 id="wp-uuid-001"),
            _doc("WS-001", "work_statement", "Login Flow",
                 {"ws_id": "ws_login", "parent_wp_id": "wp_auth", "title": "Login"},
                 ia=_SIMPLE_IA,
                 parent_document_id="wp-uuid-001"),
        ]
        md = render_project_binder(
            project_id="HWCA-001",
            project_title="Test",
            documents=docs,
            generated_at=FIXED_TS,
        )
        pos_ci = md.index("# CI-001")
        pos_wp = md.index("# WP-001")
        pos_ws = md.index("### WS-001")
        assert pos_ci < pos_wp < pos_ws

    def test_ws_ordered_by_ws_index_not_display_id(self):
        """WSs within a WP follow ws_index order, not display_id order."""
        docs = [
            _doc("WP-001", "work_package", "Auth Package",
                 {"title": "Auth", "ws_index": [
                     {"ws_id": "ws_second", "order_key": "a0"},
                     {"ws_id": "ws_first", "order_key": "a1"},
                 ]},
                 ia=_SIMPLE_IA,
                 ws_index=[
                     {"ws_id": "ws_second", "order_key": "a0"},
                     {"ws_id": "ws_first", "order_key": "a1"},
                 ],
                 id="wp-uuid-001"),
            # display_id order: WS-001 (first) < WS-002 (second)
            # but ws_index order: ws_second (a0) < ws_first (a1)
            _doc("WS-001", "work_statement", "First Statement",
                 {"ws_id": "ws_first", "parent_wp_id": "wp_auth", "title": "First"},
                 ia=_SIMPLE_IA,
                 parent_document_id="wp-uuid-001"),
            _doc("WS-002", "work_statement", "Second Statement",
                 {"ws_id": "ws_second", "parent_wp_id": "wp_auth", "title": "Second"},
                 ia=_SIMPLE_IA,
                 parent_document_id="wp-uuid-001"),
        ]
        md = render_project_binder(
            project_id="HWCA-001",
            project_title="Test",
            documents=docs,
            generated_at=FIXED_TS,
        )
        # ws_index says ws_second first, ws_first second
        pos_second = md.index("Second Statement")
        pos_first = md.index("First Statement")
        assert pos_second < pos_first


# ---------------------------------------------------------------------------
# WS inclusion via parent_document_id fallback
# ---------------------------------------------------------------------------

class TestWSInclusionViaParentDocumentId:
    """When ws_index matching returns empty, fall back to parent_document_id."""

    def test_fallback_when_ws_index_empty(self):
        """WP has no ws_index but WS docs have parent_document_id -> WSs appear."""
        docs = [
            _doc("WP-001", "work_package", "Auth Package",
                 {"title": "Auth"},
                 ia=_SIMPLE_IA,
                 ws_index=[],  # empty ws_index
                 id="wp-uuid-001"),
            _doc("WS-001", "work_statement", "Login Flow",
                 {"ws_id": "ws_login", "parent_wp_id": "wp_auth", "title": "Login"},
                 ia=_SIMPLE_IA,
                 parent_document_id="wp-uuid-001"),
        ]
        md = render_project_binder(
            project_id="HWCA-001",
            project_title="Test",
            documents=docs,
            generated_at=FIXED_TS,
        )
        assert "WS-001" in md
        assert "Login Flow" in md

    def test_fallback_when_ws_index_missing(self):
        """WP has no ws_index key at all but WS docs have parent_document_id."""
        docs = [
            _doc("WP-001", "work_package", "Auth Package",
                 {"title": "Auth"},
                 ia=_SIMPLE_IA,
                 id="wp-uuid-001"),
            _doc("WS-001", "work_statement", "Login Flow",
                 {"ws_id": "ws_login", "parent_wp_id": "wp_auth", "title": "Login"},
                 ia=_SIMPLE_IA,
                 parent_document_id="wp-uuid-001"),
        ]
        md = render_project_binder(
            project_id="HWCA-001",
            project_title="Test",
            documents=docs,
            generated_at=FIXED_TS,
        )
        assert "WS-001" in md
        assert "Login Flow" in md

    def test_fallback_orders_by_display_id(self):
        """Fallback WSs are ordered by display_id when ws_index is unavailable."""
        docs = [
            _doc("WP-001", "work_package", "Auth Package",
                 {"title": "Auth"},
                 ia=_SIMPLE_IA,
                 ws_index=[],
                 id="wp-uuid-001"),
            _doc("WS-002", "work_statement", "Logout Flow",
                 {"ws_id": "ws_logout", "parent_wp_id": "wp_auth", "title": "Logout"},
                 ia=_SIMPLE_IA,
                 parent_document_id="wp-uuid-001"),
            _doc("WS-001", "work_statement", "Login Flow",
                 {"ws_id": "ws_login", "parent_wp_id": "wp_auth", "title": "Login"},
                 ia=_SIMPLE_IA,
                 parent_document_id="wp-uuid-001"),
        ]
        md = render_project_binder(
            project_id="HWCA-001",
            project_title="Test",
            documents=docs,
            generated_at=FIXED_TS,
        )
        pos_ws1 = md.index("WS-001")
        pos_ws2 = md.index("WS-002")
        assert pos_ws1 < pos_ws2


# ---------------------------------------------------------------------------
# WP with no child WSs
# ---------------------------------------------------------------------------

class TestWPWithNoWS:
    """WP with no child WSs should render normally."""

    def test_wp_without_ws_renders_normally(self):
        docs = [
            _doc("WP-001", "work_package", "Auth Package",
                 {"title": "Auth"},
                 ia=_SIMPLE_IA,
                 ws_index=[],
                 id="wp-uuid-001"),
        ]
        md = render_project_binder(
            project_id="HWCA-001",
            project_title="Test",
            documents=docs,
            generated_at=FIXED_TS,
        )
        assert "WP-001" in md
        assert "Auth Package" in md
        # No WS entries
        assert "###" not in md


# ---------------------------------------------------------------------------
# TOC entries for WSs
# ---------------------------------------------------------------------------

class TestTOCWSEntries:
    """TOC should show WS entries indented under their parent WP."""

    def test_toc_ws_indented_under_wp(self):
        docs = [
            _doc("WP-001", "work_package", "Auth Package",
                 {"title": "Auth", "ws_index": [
                     {"ws_id": "ws_login", "order_key": "a0"},
                 ]},
                 ia=_SIMPLE_IA,
                 ws_index=[
                     {"ws_id": "ws_login", "order_key": "a0"},
                 ],
                 id="wp-uuid-001"),
            _doc("WS-001", "work_statement", "Login Flow",
                 {"ws_id": "ws_login", "parent_wp_id": "wp_auth", "title": "Login"},
                 ia=_SIMPLE_IA,
                 parent_document_id="wp-uuid-001"),
        ]
        md = render_project_binder(
            project_id="HWCA-001",
            project_title="Test",
            documents=docs,
            generated_at=FIXED_TS,
        )
        # Find the TOC section
        toc_start = md.index("## Table of Contents")
        toc_end = md.index("---", toc_start)
        toc = md[toc_start:toc_end]

        # WP entry is non-indented, WS entry is indented
        assert "- [WP-001" in toc
        assert "  - [WS-001" in toc

    def test_toc_wp_followed_by_ws_entries(self):
        """TOC: WP-001 entry is immediately followed by WS-001, WS-002."""
        docs = [
            _doc("WP-001", "work_package", "Auth Package",
                 {"title": "Auth", "ws_index": [
                     {"ws_id": "ws_login", "order_key": "a0"},
                     {"ws_id": "ws_logout", "order_key": "a1"},
                 ]},
                 ia=_SIMPLE_IA,
                 ws_index=[
                     {"ws_id": "ws_login", "order_key": "a0"},
                     {"ws_id": "ws_logout", "order_key": "a1"},
                 ],
                 id="wp-uuid-001"),
            _doc("WS-001", "work_statement", "Login Flow",
                 {"ws_id": "ws_login", "parent_wp_id": "wp_auth", "title": "Login"},
                 ia=_SIMPLE_IA,
                 parent_document_id="wp-uuid-001"),
            _doc("WS-002", "work_statement", "Logout Flow",
                 {"ws_id": "ws_logout", "parent_wp_id": "wp_auth", "title": "Logout"},
                 ia=_SIMPLE_IA,
                 parent_document_id="wp-uuid-001"),
        ]
        md = render_project_binder(
            project_id="HWCA-001",
            project_title="Test",
            documents=docs,
            generated_at=FIXED_TS,
        )
        toc_start = md.index("## Table of Contents")
        toc_end = md.index("---", toc_start)
        toc = md[toc_start:toc_end]

        pos_wp = toc.index("WP-001")
        pos_ws1 = toc.index("WS-001")
        pos_ws2 = toc.index("WS-002")
        assert pos_wp < pos_ws1 < pos_ws2


# ---------------------------------------------------------------------------
# Multiple WPs with multiple WSs
# ---------------------------------------------------------------------------

class TestMultipleWPsWithWSs:
    """Multiple WPs with multiple WSs each -> all correctly nested."""

    def test_multiple_wps_multiple_ws_correct_nesting(self):
        docs = [
            _doc("WP-001", "work_package", "Auth Package",
                 {"title": "Auth", "ws_index": [
                     {"ws_id": "ws_login", "order_key": "a0"},
                 ]},
                 ia=_SIMPLE_IA,
                 ws_index=[
                     {"ws_id": "ws_login", "order_key": "a0"},
                 ],
                 id="wp-uuid-001"),
            _doc("WP-002", "work_package", "API Package",
                 {"title": "API", "ws_index": [
                     {"ws_id": "ws_endpoints", "order_key": "a0"},
                 ]},
                 ia=_SIMPLE_IA,
                 ws_index=[
                     {"ws_id": "ws_endpoints", "order_key": "a0"},
                 ],
                 id="wp-uuid-002"),
            _doc("WS-001", "work_statement", "Login Flow",
                 {"ws_id": "ws_login", "parent_wp_id": "wp_auth", "title": "Login"},
                 ia=_SIMPLE_IA,
                 parent_document_id="wp-uuid-001"),
            _doc("WS-002", "work_statement", "API Endpoints",
                 {"ws_id": "ws_endpoints", "parent_wp_id": "wp_api", "title": "Endpoints"},
                 ia=_SIMPLE_IA,
                 parent_document_id="wp-uuid-002"),
        ]
        md = render_project_binder(
            project_id="HWCA-001",
            project_title="Test",
            documents=docs,
            generated_at=FIXED_TS,
        )
        # Check ordering: WP-001 < WS-001 < WP-002 < WS-002
        pos_wp1 = md.index("# WP-001")
        pos_ws1 = md.index("### WS-001")
        pos_wp2 = md.index("# WP-002")
        pos_ws2 = md.index("### WS-002")
        assert pos_wp1 < pos_ws1 < pos_wp2 < pos_ws2

    def test_ws_not_duplicated_across_wps(self):
        """A WS only appears under its matching WP, not duplicated."""
        docs = [
            _doc("WP-001", "work_package", "Auth Package",
                 {"title": "Auth", "ws_index": [
                     {"ws_id": "ws_login", "order_key": "a0"},
                 ]},
                 ia=_SIMPLE_IA,
                 ws_index=[
                     {"ws_id": "ws_login", "order_key": "a0"},
                 ],
                 id="wp-uuid-001"),
            _doc("WP-002", "work_package", "API Package",
                 {"title": "API"},
                 ia=_SIMPLE_IA,
                 ws_index=[],
                 id="wp-uuid-002"),
            _doc("WS-001", "work_statement", "Login Flow",
                 {"ws_id": "ws_login", "parent_wp_id": "wp_auth", "title": "Login"},
                 ia=_SIMPLE_IA,
                 parent_document_id="wp-uuid-001"),
        ]
        md = render_project_binder(
            project_id="HWCA-001",
            project_title="Test",
            documents=docs,
            generated_at=FIXED_TS,
        )
        # WS-001 appears exactly once in body (as ### header)
        assert md.count("### WS-001") == 1


# ---------------------------------------------------------------------------
# Document count includes WSs
# ---------------------------------------------------------------------------

class TestDocumentCount:
    """Cover block document count should include WS documents."""

    def test_document_count_includes_ws(self):
        docs = [
            _doc("WP-001", "work_package", "Auth Package",
                 {"title": "Auth", "ws_index": [
                     {"ws_id": "ws_login", "order_key": "a0"},
                 ]},
                 ia=_SIMPLE_IA,
                 ws_index=[
                     {"ws_id": "ws_login", "order_key": "a0"},
                 ],
                 id="wp-uuid-001"),
            _doc("WS-001", "work_statement", "Login Flow",
                 {"ws_id": "ws_login", "parent_wp_id": "wp_auth", "title": "Login"},
                 ia=_SIMPLE_IA,
                 parent_document_id="wp-uuid-001"),
        ]
        md = render_project_binder(
            project_id="HWCA-001",
            project_title="Test",
            documents=docs,
            generated_at=FIXED_TS,
        )
        # 2 documents: WP-001 + WS-001
        assert "Documents: 2" in md
