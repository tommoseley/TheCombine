"""
Candidate Import Service — WS-WB-003.

Extracts WP candidates from a committed Implementation Plan and
transforms them into frozen work_package_candidate documents.

Pure module -- no DB, no handlers, no external dependencies.
All functions are stateless and side-effect-free for Tier-1 testability.
"""

from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# IP field name priority (v3 > v2 > v1)
# ---------------------------------------------------------------------------

_CANDIDATE_FIELD_PRIORITY = [
    "work_package_candidates",      # v3 (current)
    "candidate_work_packages",      # v2 (legacy)
    "work_packages",                # v1 (legacy)
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_candidates_from_ip(ip_content: dict) -> list[dict]:
    """
    Extract WP candidate entries from IP content.

    Supports three field name conventions (priority order):
      1. work_package_candidates (v3, current)
      2. candidate_work_packages (v2, legacy)
      3. work_packages (v1, legacy)

    Returns a list of raw candidate dicts from the IP.
    Returns empty list if no candidates found.
    Does not mutate ip_content.
    """
    for field_name in _CANDIDATE_FIELD_PRIORITY:
        candidates = ip_content.get(field_name)
        if candidates is not None and isinstance(candidates, list):
            # Return a copy to avoid mutation of the input
            return list(candidates)
    return []


def build_wpc_document(
    candidate: dict,
    source_ip_id: str,
    source_ip_version: str,
    frozen_by: str,
) -> dict:
    """
    Transform an IP candidate entry into a WPC document.

    Field mappings:
      - candidate_id -> wpc_id
      - scope_in -> scope_summary
      - title, rationale preserved as-is
      - frozen_at set to current UTC timestamp (ISO format)
      - source_ip_id, source_ip_version, frozen_by set from arguments

    Returns a dict conforming to the work_package_candidate schema.
    Output contains only the fields defined in the WPC schema.
    """
    return {
        "wpc_id": candidate.get("candidate_id", ""),
        "title": candidate.get("title", ""),
        "rationale": candidate.get("rationale", ""),
        "scope_summary": candidate.get("scope_in", []),
        "source_ip_id": source_ip_id,
        "source_ip_version": source_ip_version,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "frozen_by": frozen_by,
    }


def import_candidates(
    ip_content: dict,
    source_ip_id: str,
    source_ip_version: str,
    frozen_by: str = "system",
) -> list[dict]:
    """
    Full import pipeline: extract candidates from IP + transform to WPC documents.

    Args:
        ip_content: The IP document's content dict.
        source_ip_id: The IP document's ID (for provenance).
        source_ip_version: The IP document's version at freeze time.
        frozen_by: Who/what performed the freeze (default: "system").

    Returns:
        List of WPC document dicts, one per candidate found in the IP.
        Empty list if no candidates found.
    """
    raw_candidates = extract_candidates_from_ip(ip_content)
    return [
        build_wpc_document(candidate, source_ip_id, source_ip_version, frozen_by)
        for candidate in raw_candidates
    ]
