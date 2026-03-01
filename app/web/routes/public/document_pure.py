"""
Pure data transformation functions extracted from document_routes.py.

No I/O, no DB, no logging. All functions are deterministic and testable in isolation.

WS-CRAP-006: Testability refactoring for CRAP score reduction.
"""

from typing import Optional


# =============================================================================
# Document Config (static fallback)
# =============================================================================

DOCUMENT_CONFIG = {
    "concierge_intake": {
        "title": "Concierge Intake",
        "icon": "clipboard-check",
        "template": "public/pages/partials/_concierge_intake_content.html",
    },
    "project_discovery": {
        "title": "Project Discovery",
        "icon": "compass",
        "template": "public/pages/partials/_project_discovery_content.html",
    },
    "technical_architecture": {
        "title": "Technical Architecture",
        "icon": "building",
        "template": "public/pages/partials/_technical_architecture_content.html",
        "view_docdef": "ArchitecturalSummaryView",
    },
    "story_backlog": {
        "title": "Story Backlog",
        "icon": "list-checks",
        "template": "public/pages/partials/_story_backlog_content.html",
        "view_docdef": "StoryBacklogView",
    },
}

DEFAULT_FALLBACK_CONFIG = {
    "title": None,  # Caller should fill with formatted doc_type_id
    "icon": "file-text",
    "template": "public/pages/partials/_document_not_found.html",
}


def get_fallback_config(doc_type_id: str) -> dict:
    """Get static fallback config for a document type.

    Returns a copy of the known config if found, otherwise generates
    a default config with a formatted title.
    """
    config = DOCUMENT_CONFIG.get(doc_type_id)
    if config:
        return dict(config)
    return {
        "title": doc_type_id.replace("_", " ").title(),
        "icon": "file-text",
        "template": "public/pages/partials/_document_not_found.html",
    }


def merge_doc_type_config(
    db_doc_type: Optional[dict],
    fallback_config: dict,
) -> dict:
    """Merge database document type config with static fallback.

    Returns a dict with resolved values for:
    - name: Document type display name
    - icon: Icon identifier
    - description: Document type description (may be None)
    - template: Template path for rendering
    - view_docdef: View docdef identifier (may be None)

    Args:
        db_doc_type: Dict from database with keys name, icon, description, view_docdef.
                     May be None if not found in database.
        fallback_config: Static fallback config dict.
    """
    name = db_doc_type["name"] if db_doc_type else fallback_config["title"]
    icon = (
        db_doc_type["icon"]
        if db_doc_type and db_doc_type.get("icon")
        else fallback_config["icon"]
    )
    description = db_doc_type["description"] if db_doc_type else None
    template = fallback_config.get("template", "public/pages/partials/_document_not_found.html")

    return {
        "name": name,
        "icon": icon,
        "description": description,
        "template": template,
    }


def resolve_view_docdef(
    doc_type_id: str,
    db_doc_type: Optional[dict],
    fallback_config: dict,
) -> Optional[str]:
    """Resolve view_docdef for a document type.

    Prefers DB value, falls back to DOCUMENT_CONFIG.
    Returns None for project_discovery (intake format uses different schema).

    Args:
        doc_type_id: The document type identifier.
        db_doc_type: Dict from database, may be None.
        fallback_config: Static fallback config dict.

    Returns:
        The view_docdef string, or None if not applicable.
    """
    # Skip new viewer for project_discovery
    if doc_type_id == "project_discovery":
        return None

    return (
        (db_doc_type.get("view_docdef") if db_doc_type else None)
        or fallback_config.get("view_docdef")
    )
