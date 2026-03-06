"""
Tier-1 tests for the Markdown block renderer (WS-RENDER-001).

Tests the pure function that converts document content + IA definitions
into Markdown output. No DB, no HTTP, no side effects.
"""
import pytest

# Import will fail until the module exists — that's the failing test.
from app.domain.services.markdown_renderer import render_document_to_markdown


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _ia_sections(*sections):
    """Wrap sections into a minimal IA dict."""
    return {"version": 2, "sections": list(sections)}


def _section(id, label, binds):
    return {"id": id, "label": label, "binds": binds}


# ---------------------------------------------------------------------------
# paragraph
# ---------------------------------------------------------------------------

class TestParagraph:
    def test_renders_text(self):
        ia = _ia_sections(
            _section("s1", "Overview", [{"path": "summary", "render_as": "paragraph"}])
        )
        content = {"summary": "This is a summary."}
        md = render_document_to_markdown(content, ia)
        assert "## Overview" in md
        assert "This is a summary." in md

    def test_missing_field_omitted(self):
        ia = _ia_sections(
            _section("s1", "Overview", [{"path": "summary", "render_as": "paragraph"}])
        )
        content = {}
        md = render_document_to_markdown(content, ia)
        # Section header may or may not appear; the field value must not
        assert "None" not in md


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

class TestList:
    def test_renders_bullet_list(self):
        ia = _ia_sections(
            _section("s1", "Scope", [{"path": "scope_in", "render_as": "list"}])
        )
        content = {"scope_in": ["Item A", "Item B", "Item C"]}
        md = render_document_to_markdown(content, ia)
        assert "## Scope" in md
        assert "- Item A" in md
        assert "- Item B" in md
        assert "- Item C" in md

    def test_empty_list_omitted(self):
        ia = _ia_sections(
            _section("s1", "Scope", [{"path": "scope_in", "render_as": "list"}])
        )
        content = {"scope_in": []}
        md = render_document_to_markdown(content, ia)
        assert "- " not in md


# ---------------------------------------------------------------------------
# ordered-list
# ---------------------------------------------------------------------------

class TestOrderedList:
    def test_renders_numbered_list(self):
        ia = _ia_sections(
            _section("s1", "Steps", [{"path": "steps", "render_as": "ordered-list"}])
        )
        content = {"steps": ["First", "Second", "Third"]}
        md = render_document_to_markdown(content, ia)
        assert "1. First" in md
        assert "2. Second" in md
        assert "3. Third" in md


# ---------------------------------------------------------------------------
# table
# ---------------------------------------------------------------------------

class TestTable:
    def test_renders_gfm_table(self):
        ia = _ia_sections(
            _section("s1", "Risks", [{
                "path": "risks",
                "render_as": "table",
                "columns": [
                    {"field": "id", "label": "ID"},
                    {"field": "description", "label": "Risk"},
                    {"field": "impact", "label": "Impact"},
                ],
            }])
        )
        content = {"risks": [
            {"id": "R-001", "description": "Data loss", "impact": "High"},
            {"id": "R-002", "description": "Latency", "impact": "Medium"},
        ]}
        md = render_document_to_markdown(content, ia)
        assert "## Risks" in md
        assert "| ID | Risk | Impact |" in md
        assert "| --- | --- | --- |" in md
        assert "| R-001 | Data loss | High |" in md
        assert "| R-002 | Latency | Medium |" in md

    def test_missing_column_value_shows_dash(self):
        ia = _ia_sections(
            _section("s1", "Items", [{
                "path": "items",
                "render_as": "table",
                "columns": [
                    {"field": "name", "label": "Name"},
                    {"field": "status", "label": "Status"},
                ],
            }])
        )
        content = {"items": [{"name": "Alpha"}]}  # missing "status"
        md = render_document_to_markdown(content, ia)
        assert "| Alpha | — |" in md

    def test_empty_table_omitted(self):
        ia = _ia_sections(
            _section("s1", "Items", [{
                "path": "items",
                "render_as": "table",
                "columns": [{"field": "name", "label": "Name"}],
            }])
        )
        content = {"items": []}
        md = render_document_to_markdown(content, ia)
        assert "| Name |" not in md


# ---------------------------------------------------------------------------
# key-value-pairs
# ---------------------------------------------------------------------------

class TestKeyValuePairs:
    def test_renders_kv_pairs(self):
        ia = _ia_sections(
            _section("s1", "Meta", [{"path": "meta", "render_as": "key-value-pairs"}])
        )
        content = {"meta": {"Author": "Tom", "Version": "1.0"}}
        md = render_document_to_markdown(content, ia)
        assert "**Author:** Tom" in md
        assert "**Version:** 1.0" in md


# ---------------------------------------------------------------------------
# nested-object
# ---------------------------------------------------------------------------

class TestNestedObject:
    def test_renders_sub_fields(self):
        ia = _ia_sections(
            _section("s1", "Summary", [{
                "path": "summary",
                "render_as": "nested-object",
                "fields": [
                    {"path": "problem", "render_as": "paragraph"},
                    {"path": "approach", "render_as": "paragraph"},
                ],
            }])
        )
        content = {"summary": {"problem": "Too slow", "approach": "Cache it"}}
        md = render_document_to_markdown(content, ia)
        assert "## Summary" in md
        assert "Too slow" in md
        assert "Cache it" in md

    def test_nested_list_field(self):
        ia = _ia_sections(
            _section("s1", "Summary", [{
                "path": "summary",
                "render_as": "nested-object",
                "fields": [
                    {"path": "decisions", "render_as": "list"},
                ],
            }])
        )
        content = {"summary": {"decisions": ["Use Redis", "Drop Postgres"]}}
        md = render_document_to_markdown(content, ia)
        assert "- Use Redis" in md
        assert "- Drop Postgres" in md


# ---------------------------------------------------------------------------
# card-list
# ---------------------------------------------------------------------------

class TestCardList:
    def test_renders_cards(self):
        ia = _ia_sections(
            _section("s1", "Decisions", [{
                "path": "decisions",
                "render_as": "card-list",
                "card": {
                    "title": "area",
                    "fields": [
                        {"path": "rationale", "render_as": "paragraph"},
                        {"path": "options", "render_as": "list"},
                    ],
                },
            }])
        )
        content = {"decisions": [
            {
                "area": "Auth System",
                "rationale": "JWT is standard",
                "options": ["JWT", "Session cookies"],
            },
            {
                "area": "Database",
                "rationale": "Postgres is reliable",
                "options": ["Postgres", "MySQL"],
            },
        ]}
        md = render_document_to_markdown(content, ia)
        assert "### Auth System" in md
        assert "JWT is standard" in md
        assert "- JWT" in md
        assert "- Session cookies" in md
        assert "### Database" in md
        assert "Postgres is reliable" in md


# ---------------------------------------------------------------------------
# Section ordering
# ---------------------------------------------------------------------------

class TestSectionOrdering:
    def test_sections_render_in_ia_order(self):
        ia = _ia_sections(
            _section("s1", "First Section", [{"path": "a", "render_as": "paragraph"}]),
            _section("s2", "Second Section", [{"path": "b", "render_as": "paragraph"}]),
            _section("s3", "Third Section", [{"path": "c", "render_as": "paragraph"}]),
        )
        content = {"a": "Alpha", "b": "Beta", "c": "Gamma"}
        md = render_document_to_markdown(content, ia)
        pos_first = md.index("## First Section")
        pos_second = md.index("## Second Section")
        pos_third = md.index("## Third Section")
        assert pos_first < pos_second < pos_third


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_input_same_output(self):
        ia = _ia_sections(
            _section("s1", "Overview", [{"path": "summary", "render_as": "paragraph"}]),
            _section("s2", "Items", [{
                "path": "items",
                "render_as": "table",
                "columns": [{"field": "name", "label": "Name"}],
            }]),
        )
        content = {"summary": "Test", "items": [{"name": "A"}, {"name": "B"}]}
        md1 = render_document_to_markdown(content, ia)
        md2 = render_document_to_markdown(content, ia)
        assert md1 == md2


# ---------------------------------------------------------------------------
# Multiple binds in one section
# ---------------------------------------------------------------------------

class TestMultipleBinds:
    def test_multiple_binds_in_section(self):
        ia = _ia_sections(
            _section("s1", "Overview", [
                {"path": "title", "render_as": "paragraph"},
                {"path": "tags", "render_as": "list"},
            ])
        )
        content = {"title": "My Project", "tags": ["fast", "secure"]}
        md = render_document_to_markdown(content, ia)
        assert "## Overview" in md
        assert "My Project" in md
        assert "- fast" in md
        assert "- secure" in md
