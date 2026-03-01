"""
Tier-1 tests for document_pure.py -- pure data transformations extracted from document_routes.

No DB, no I/O. All tests use plain dicts.
WS-CRAP-006: Testability refactoring.
"""

from app.web.routes.public.document_pure import (
    get_fallback_config,
    merge_doc_type_config,
    resolve_view_docdef,
)


# =============================================================================
# get_fallback_config
# =============================================================================

class TestGetFallbackConfig:
    def test_known_type_concierge_intake(self):
        result = get_fallback_config("concierge_intake")
        assert result["title"] == "Concierge Intake"
        assert result["icon"] == "clipboard-check"
        assert "template" in result

    def test_known_type_project_discovery(self):
        result = get_fallback_config("project_discovery")
        assert result["title"] == "Project Discovery"
        assert result["icon"] == "compass"

    def test_known_type_technical_architecture(self):
        result = get_fallback_config("technical_architecture")
        assert result["title"] == "Technical Architecture"
        assert result.get("view_docdef") == "ArchitecturalSummaryView"

    def test_known_type_story_backlog(self):
        result = get_fallback_config("story_backlog")
        assert result["title"] == "Story Backlog"
        assert result.get("view_docdef") == "StoryBacklogView"

    def test_unknown_type_formatted_title(self):
        result = get_fallback_config("my_custom_doc")
        assert result["title"] == "My Custom Doc"
        assert result["icon"] == "file-text"
        assert result["template"] == "public/pages/partials/_document_not_found.html"

    def test_unknown_type_underscores_replaced(self):
        result = get_fallback_config("some_long_type_name")
        assert result["title"] == "Some Long Type Name"

    def test_returns_copy(self):
        """Ensure known configs return copies, not references."""
        r1 = get_fallback_config("concierge_intake")
        r2 = get_fallback_config("concierge_intake")
        r1["title"] = "MUTATED"
        assert r2["title"] == "Concierge Intake"


# =============================================================================
# merge_doc_type_config
# =============================================================================

class TestMergeDocTypeConfig:
    def test_db_config_takes_priority(self):
        db = {"name": "DB Name", "icon": "star", "description": "DB desc", "view_docdef": "X"}
        fallback = {"title": "Fallback", "icon": "default", "template": "t.html"}
        result = merge_doc_type_config(db, fallback)
        assert result["name"] == "DB Name"
        assert result["icon"] == "star"
        assert result["description"] == "DB desc"

    def test_fallback_when_no_db(self):
        fallback = {"title": "Fallback Title", "icon": "folder", "template": "t.html"}
        result = merge_doc_type_config(None, fallback)
        assert result["name"] == "Fallback Title"
        assert result["icon"] == "folder"
        assert result["description"] is None

    def test_fallback_icon_when_db_icon_none(self):
        db = {"name": "Doc", "icon": None, "description": "desc"}
        fallback = {"title": "F", "icon": "backup-icon", "template": "t.html"}
        result = merge_doc_type_config(db, fallback)
        assert result["icon"] == "backup-icon"

    def test_template_always_from_fallback(self):
        db = {"name": "Doc", "icon": "star", "description": "d"}
        fallback = {"title": "F", "icon": "x", "template": "my/template.html"}
        result = merge_doc_type_config(db, fallback)
        assert result["template"] == "my/template.html"

    def test_fallback_missing_template(self):
        fallback = {"title": "F", "icon": "x"}
        result = merge_doc_type_config(None, fallback)
        assert result["template"] == "public/pages/partials/_document_not_found.html"


# =============================================================================
# resolve_view_docdef
# =============================================================================

class TestResolveViewDocdef:
    def test_project_discovery_always_none(self):
        """project_discovery skips new viewer regardless of config."""
        db = {"view_docdef": "ProjectDiscoveryView"}
        fallback = {"view_docdef": "ProjectDiscoveryView"}
        result = resolve_view_docdef("project_discovery", db, fallback)
        assert result is None

    def test_db_value_preferred(self):
        db = {"view_docdef": "DBView"}
        fallback = {"view_docdef": "FallbackView"}
        result = resolve_view_docdef("technical_architecture", db, fallback)
        assert result == "DBView"

    def test_fallback_when_db_none(self):
        fallback = {"view_docdef": "FallbackView"}
        result = resolve_view_docdef("story_backlog", None, fallback)
        assert result == "FallbackView"

    def test_fallback_when_db_docdef_none(self):
        db = {"view_docdef": None}
        fallback = {"view_docdef": "FallbackView"}
        result = resolve_view_docdef("story_backlog", db, fallback)
        assert result == "FallbackView"

    def test_none_when_neither_has_docdef(self):
        result = resolve_view_docdef("concierge_intake", None, {})
        assert result is None

    def test_none_when_fallback_has_no_key(self):
        result = resolve_view_docdef("concierge_intake", None, {"title": "X"})
        assert result is None
