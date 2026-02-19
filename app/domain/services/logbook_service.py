"""
Project Logbook service — pure functions on dicts.

Provides:
- Logbook creation and entry append
- WS acceptance orchestration (atomic via deepcopy)

All functions are pure (dict in, dict out) for Tier 1 testability.
"""

import copy
import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.domain.services.work_statement_state import validate_ws_transition
from app.domain.services.work_statement_registration import apply_ws_accepted_to_wp


class LogbookAppendError(ValueError):
    """Raised when appending a logbook entry fails."""


def create_empty_logbook(project_id: str) -> Dict[str, Any]:
    """
    Create an empty project logbook.

    Args:
        project_id: The project this logbook belongs to

    Returns:
        Logbook dict with header fields and empty entries list
    """
    return {
        "schema_version": "1.0",
        "project_id": project_id,
        "mode_b_rate": 0.0,
        "verification_debt_open": 0,
        "program_ref": None,
        "entries": [],
    }


def create_logbook_entry(
    ws_id: str,
    parent_wp_id: str,
    result: str = "ACCEPTED",
    mode_b_list: Optional[List[str]] = None,
    tier0_json: Optional[Dict[str, Any]] = None,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a single logbook entry dict.

    Args:
        ws_id: Work Statement ID
        parent_wp_id: Parent Work Package ID
        result: Acceptance result (default "ACCEPTED")
        mode_b_list: List of Mode B items (default empty)
        tier0_json: Tier 0 verification results (default empty)
        timestamp: ISO 8601 timestamp (default utcnow)

    Returns:
        Entry dict
    """
    if timestamp is None:
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    return {
        "timestamp": timestamp,
        "ws_id": ws_id,
        "parent_wp_id": parent_wp_id,
        "result": result,
        "mode_b_list": mode_b_list if mode_b_list is not None else [],
        "tier0_json": tier0_json if tier0_json is not None else {},
    }


def append_logbook_entry(
    logbook_data: Dict[str, Any], entry: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Append an entry to the logbook's entries list.

    Args:
        logbook_data: Logbook dict (modified in place and returned)
        entry: Entry dict to append

    Returns:
        Modified logbook_data

    Raises:
        LogbookAppendError: If entries is not a list
    """
    entries = logbook_data.get("entries")
    if not isinstance(entries, list):
        raise LogbookAppendError(
            f"Logbook 'entries' must be a list, got {type(entries).__name__}"
        )
    entries.append(entry)
    return logbook_data


def execute_ws_acceptance(
    ws_data: Dict[str, Any],
    wp_data: Dict[str, Any],
    logbook_data: Optional[Dict[str, Any]],
    project_id: str,
    mode_b_list: Optional[List[str]] = None,
    tier0_json: Optional[Dict[str, Any]] = None,
    timestamp: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    Atomically accept a Work Statement and append a logbook entry.

    Operates on deep copies — originals are unchanged on failure.

    Steps:
    1. Validate WS transition (IN_PROGRESS -> ACCEPTED)
    2. Deep copy all inputs
    3. Lazy-create logbook if None
    4. Create and append logbook entry
    5. Set WS state to ACCEPTED
    6. Apply WS accepted rollup to WP

    Args:
        ws_data: Work Statement dict
        wp_data: Parent Work Package dict
        logbook_data: Project logbook dict (None triggers lazy creation)
        project_id: Project ID for lazy logbook creation
        mode_b_list: Optional Mode B items for the entry
        tier0_json: Optional Tier 0 results for the entry
        timestamp: Optional ISO 8601 timestamp for the entry

    Returns:
        Tuple of (ws_result, wp_result, logbook_result) — all deep copies

    Raises:
        InvalidWSTransitionError: If WS is not in valid state for acceptance
        LogbookAppendError: If logbook entries field is malformed
    """
    # 1. Validate transition before any mutation
    validate_ws_transition(ws_data["state"], "ACCEPTED")

    # 2. Deep copy all inputs
    ws_result = copy.deepcopy(ws_data)
    wp_result = copy.deepcopy(wp_data)
    lb_result = (
        copy.deepcopy(logbook_data)
        if logbook_data is not None
        else create_empty_logbook(project_id)
    )

    # 3. Create and append logbook entry (may raise LogbookAppendError)
    entry = create_logbook_entry(
        ws_id=ws_result["ws_id"],
        parent_wp_id=ws_result["parent_wp_id"],
        result="ACCEPTED",
        mode_b_list=mode_b_list,
        tier0_json=tier0_json,
        timestamp=timestamp,
    )
    append_logbook_entry(lb_result, entry)

    # 4. Set WS state
    ws_result["state"] = "ACCEPTED"

    # 5. Apply WP rollup
    apply_ws_accepted_to_wp(wp_result)

    return ws_result, wp_result, lb_result
