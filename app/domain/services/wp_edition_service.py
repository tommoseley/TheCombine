"""
WP Edition Tracking + Mechanical Change Summary (WS-WB-005).

Implements two-plane versioning for Work Packages:
- Edition increments only on WP-level field changes
- change_summary[] is system-computed from JSON diff (never human-narrated)
- WS content changes do NOT increment WP edition

Pure module -- no DB, no handlers, no external dependencies.
"""

from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# WP-level fields (exhaustive, per WS-WB-005 / D2)
# ---------------------------------------------------------------------------
# Changes to these fields trigger a WP edition bump.
# Everything else (ws_child_refs, ws_total, ws_done, mode_b_count,
# wp_id, revision, change_summary, _lineage, etc.) is excluded.

WP_LEVEL_FIELDS: set[str] = {
    "title",
    "rationale",
    "scope_in",
    "scope_out",
    "dependencies",
    "definition_of_done",
    "governance_pins",
    "ws_index",
    "state",
    "source_candidate_ids",
    "transformation",
    "transformation_notes",
}


# ---------------------------------------------------------------------------
# Sentinel for missing keys (distinct from None)
# ---------------------------------------------------------------------------
_MISSING = object()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_change_summary(old_content: dict, new_content: dict) -> list[str]:
    """
    Compare WP-level fields between old and new content.

    Returns a list of mechanical diff entries. Empty list if no WP-level
    fields changed.  Entries are deterministically ordered by field name.

    Examples:
        - "title: 'Old Title' -> 'New Title'"
        - "ws_index: added WS-WB-014"
        - "dependencies: removed must_complete_first -> wp_schema"
        - "state: PLANNED -> READY"
    """
    entries: list[str] = []

    for field in sorted(WP_LEVEL_FIELDS):
        old_val = old_content.get(field, _MISSING)
        new_val = new_content.get(field, _MISSING)

        if old_val is _MISSING and new_val is _MISSING:
            continue

        if old_val is _MISSING:
            entries.append(_format_field_added(field, new_val))
            continue

        if new_val is _MISSING:
            entries.append(_format_field_removed(field, old_val))
            continue

        if old_val == new_val:
            continue

        # Field changed -- format depends on type
        field_entries = _format_field_change(field, old_val, new_val)
        entries.extend(field_entries)

    return entries


def apply_edition_bump(
    content: dict,
    old_content: dict,
    updated_by: str,
) -> dict:
    """
    Compute change_summary and conditionally bump edition.

    If no WP-level fields changed, returns content unchanged (no edition bump).
    If changes exist:
      - Increments revision.edition
      - Sets revision.updated_at to current UTC timestamp
      - Sets revision.updated_by
      - Populates change_summary[]

    Returns the (possibly updated) content dict. Does NOT strip non-WP-level
    fields -- all existing fields are preserved.
    """
    summary = compute_change_summary(old_content, content)

    if not summary:
        # No WP-level changes -- no edition bump
        return content

    old_revision = old_content.get("revision", {})
    old_edition = old_revision.get("edition", 0)

    content["revision"] = {
        "edition": old_edition + 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": updated_by,
    }
    content["change_summary"] = summary

    return content


def get_edition_history(editions: list[dict]) -> list[dict]:
    """
    Return editions in reverse chronological order (newest first).

    Sorts by revision.edition descending. Does not mutate the input list.
    """
    return sorted(
        editions,
        key=lambda e: e.get("revision", {}).get("edition", 0),
        reverse=True,
    )


# ---------------------------------------------------------------------------
# Internal formatting helpers
# ---------------------------------------------------------------------------


def _format_field_added(field: str, value) -> str:
    """Format entry for a field that was absent and is now present."""
    return f"{field}: set to {_short_repr(value)}"


def _format_field_removed(field: str, value) -> str:
    """Format entry for a field that was present and is now absent."""
    return f"{field}: removed (was {_short_repr(value)})"


def _format_field_change(field: str, old_val, new_val) -> list[str]:
    """
    Format change entries for a field whose value changed.

    For list fields with identifiable items (ws_index, dependencies,
    scope_in, scope_out, etc.), produce granular added/removed entries.
    For scalar/dict fields, produce a single 'old -> new' entry.
    """
    # ws_index: compare by ws_id membership
    if field == "ws_index":
        return _diff_ws_index(old_val, new_val)

    # dependencies: compare by wp_id + dependency_type
    if field == "dependencies":
        return _diff_dependencies(old_val, new_val)

    # Simple string lists: scope_in, scope_out, definition_of_done,
    # source_candidate_ids
    if field in ("scope_in", "scope_out", "definition_of_done", "source_candidate_ids"):
        return _diff_string_list(field, old_val, new_val)

    # Scalar or complex (governance_pins, transformation, etc.)
    return [f"{field}: {_short_repr(old_val)} -> {_short_repr(new_val)}"]


def _diff_ws_index(old_index: list, new_index: list) -> list[str]:
    """Diff ws_index by ws_id membership."""
    old_ids = {entry["ws_id"] for entry in (old_index or [])}
    new_ids = {entry["ws_id"] for entry in (new_index or [])}

    entries = []
    for ws_id in sorted(new_ids - old_ids):
        entries.append(f"ws_index: added {ws_id}")
    for ws_id in sorted(old_ids - new_ids):
        entries.append(f"ws_index: removed {ws_id}")

    # If membership unchanged but order changed, note reorder
    if old_ids == new_ids and old_index != new_index:
        entries.append("ws_index: reordered")

    return entries


def _diff_dependencies(old_deps: list, new_deps: list) -> list[str]:
    """Diff dependencies by wp_id + dependency_type."""
    def dep_key(d: dict) -> str:
        return f"{d.get('dependency_type', '?')} -> {d.get('wp_id', '?')}"

    old_keys = {dep_key(d) for d in (old_deps or [])}
    new_keys = {dep_key(d) for d in (new_deps or [])}

    entries = []
    for key in sorted(new_keys - old_keys):
        entries.append(f"dependencies: added {key}")
    for key in sorted(old_keys - new_keys):
        entries.append(f"dependencies: removed {key}")

    return entries


def _diff_string_list(field: str, old_list: list, new_list: list) -> list[str]:
    """Diff simple string lists by set membership."""
    old_set = set(old_list or [])
    new_set = set(new_list or [])

    entries = []
    for item in sorted(new_set - old_set):
        entries.append(f"{field}: added '{item}'")
    for item in sorted(old_set - new_set):
        entries.append(f"{field}: removed '{item}'")

    return entries


def _short_repr(value) -> str:
    """Short human-readable representation for change summary entries."""
    if isinstance(value, str):
        return f"'{value}'"
    if isinstance(value, list):
        if len(value) <= 3:
            return repr(value)
        return f"[{len(value)} items]"
    if isinstance(value, dict):
        return repr(value)
    return repr(value)
