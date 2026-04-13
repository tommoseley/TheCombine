"""
Release manager: active_releases.json manipulation.

Functions for updating active_releases.json for various artifact types
(workflows, document types, roles, templates, schemas).
Extracted from workspace_service.py.
"""

import json
from pathlib import Path
from typing import Optional


class ReleaseUpdateError(Exception):
    """Error updating active_releases.json."""
    pass


def _load_releases(config_path: Path) -> dict:
    """Load active_releases.json from the config path."""
    releases_path = config_path / "_active" / "active_releases.json"
    if not releases_path.exists():
        raise ReleaseUpdateError("active_releases.json not found")

    with open(releases_path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _save_releases(config_path: Path, releases: dict) -> None:
    """Save active_releases.json to the config path."""
    releases_path = config_path / "_active" / "active_releases.json"
    releases_path.write_text(
        json.dumps(releases, indent=2) + "\n",
        encoding="utf-8",
    )


def update_active_releases_for_workflow(
    config_path: Path,
    workflow_id: str,
    version: Optional[str],
) -> None:
    """
    Update active_releases.json for a workflow.

    Args:
        config_path: Path to combine-config directory
        workflow_id: Workflow ID
        version: Version to set, or None to remove
    """
    releases = _load_releases(config_path)

    if "workflows" not in releases:
        releases["workflows"] = {}

    if version is None:
        releases["workflows"].pop(workflow_id, None)
    else:
        releases["workflows"][workflow_id] = version

    _save_releases(config_path, releases)


def update_active_releases_for_doc_type(
    config_path: Path,
    doc_type_id: str,
    version: Optional[str],
) -> None:
    """
    Update active_releases.json for a document type.

    Args:
        config_path: Path to combine-config directory
        doc_type_id: Document type ID
        version: Version to set, or None to remove
    """
    releases = _load_releases(config_path)

    if "document_types" not in releases:
        releases["document_types"] = {}
    if "schemas" not in releases:
        releases["schemas"] = {}

    if version is None:
        releases["document_types"].pop(doc_type_id, None)
        releases["schemas"].pop(doc_type_id, None)
    else:
        releases["document_types"][doc_type_id] = version
        releases["schemas"][doc_type_id] = version

    _save_releases(config_path, releases)


def update_active_releases_for_role(
    config_path: Path,
    role_id: str,
    version: Optional[str],
) -> None:
    """
    Update active_releases.json for a role.

    Args:
        config_path: Path to combine-config directory
        role_id: Role ID
        version: Version to set, or None to remove
    """
    releases = _load_releases(config_path)

    if "roles" not in releases:
        releases["roles"] = {}

    if version is None:
        releases["roles"].pop(role_id, None)
    else:
        releases["roles"][role_id] = version

    _save_releases(config_path, releases)


def update_active_releases_for_template(
    config_path: Path,
    template_id: str,
    version: Optional[str],
) -> None:
    """
    Update active_releases.json for a template.

    Args:
        config_path: Path to combine-config directory
        template_id: Template ID
        version: Version to set, or None to remove
    """
    releases = _load_releases(config_path)

    if "templates" not in releases:
        releases["templates"] = {}

    if version is None:
        releases["templates"].pop(template_id, None)
    else:
        releases["templates"][template_id] = version

    _save_releases(config_path, releases)


def update_active_releases_for_schema(
    config_path: Path,
    schema_id: str,
    version: Optional[str],
) -> None:
    """
    Update active_releases.json for a standalone schema.

    Args:
        config_path: Path to combine-config directory
        schema_id: Schema ID
        version: Version to set, or None to remove
    """
    releases = _load_releases(config_path)

    if "schemas" not in releases:
        releases["schemas"] = {}

    if version is None:
        releases["schemas"].pop(schema_id, None)
    else:
        releases["schemas"][schema_id] = version

    _save_releases(config_path, releases)
