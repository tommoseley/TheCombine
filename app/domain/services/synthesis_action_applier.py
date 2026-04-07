"""
Synthesis Action Applier (ADR-070, WS-SYNTHESIS-005).

Converts accepted synthesis actions into correction briefs that route
through the existing correction gate (ADR-069). Each action type maps
to a specific pipeline stage and produces a correction brief with the
action's rationale and post-condition.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Action-to-correction mapping
# ---------------------------------------------------------------------------

# Which pipeline stage each action type targets for rewind
ACTION_STAGE_MAP = {
    "MERGE_WS": "work_statement",
    "SPLIT_WS": "work_statement",
    "REMOVE_WS": "work_statement",
    "NORMALIZE_BOUNDARY": "work_statement",
    "DEFER_COMPONENT": "technical_architecture",
}


@dataclass
class CorrectionBrief:
    """A correction ready to be applied via the rewind endpoint."""

    rewind_to_stage: str
    reason: str
    applies_to_stages: list[str]
    post_condition: str
    source_action_type: str
    source_targets: list[str]


def action_to_correction(action: dict[str, Any]) -> CorrectionBrief:
    """Convert an accepted synthesis action into a correction brief.

    The correction brief is structured to be passed to the rewind
    endpoint as the reason field (ADR-069). The post-condition is
    preserved for verification after regeneration.

    Args:
        action: A synthesis action dict with action_type, targets,
                rationale, and post_condition.

    Returns:
        CorrectionBrief ready for the rewind endpoint.

    Raises:
        ValueError: If action_type is not in the restricted set.
    """
    action_type = action.get("action_type")
    if action_type not in ACTION_STAGE_MAP:
        raise ValueError(f"Unknown action type: {action_type}")

    targets = action.get("targets", [])
    rationale = action.get("rationale", "")
    post_condition = action.get("post_condition", "")
    stage = ACTION_STAGE_MAP[action_type]

    reason = _build_correction_text(action_type, targets, rationale, post_condition)

    # Determine which stages the correction applies to
    applies_to = [stage]
    if action_type == "DEFER_COMPONENT":
        # TA change cascades to WP and WS
        applies_to = ["technical_architecture", "work_package", "work_statement"]

    return CorrectionBrief(
        rewind_to_stage=stage,
        reason=reason,
        applies_to_stages=applies_to,
        post_condition=post_condition,
        source_action_type=action_type,
        source_targets=targets,
    )


def _build_correction_text(
    action_type: str,
    targets: list[str],
    rationale: str,
    post_condition: str,
) -> str:
    """Build human-readable correction brief text from action fields."""
    target_str = ", ".join(targets)

    templates = {
        "MERGE_WS": (
            f"[Synthesis MERGE_WS] Merge {target_str} into a single Work Statement. "
            f"Reason: {rationale}. "
            f"Post-condition: {post_condition}."
        ),
        "SPLIT_WS": (
            f"[Synthesis SPLIT_WS] Split {target_str} into separate Work Statements, "
            f"each covering a single responsibility. "
            f"Reason: {rationale}. "
            f"Post-condition: {post_condition}."
        ),
        "REMOVE_WS": (
            f"[Synthesis REMOVE_WS] Remove {target_str} — scope is redundant. "
            f"Reason: {rationale}. "
            f"Post-condition: {post_condition}."
        ),
        "NORMALIZE_BOUNDARY": (
            f"[Synthesis NORMALIZE_BOUNDARY] Adjust scope boundaries for {target_str} "
            f"to eliminate overlap. Only modify scope_in, scope_out, allowed_paths, "
            f"or dependency references. Do NOT change objective, procedure, or "
            f"definition_of_done. "
            f"Reason: {rationale}. "
            f"Post-condition: {post_condition}."
        ),
        "DEFER_COMPONENT": (
            f"[Synthesis DEFER_COMPONENT] Mark {target_str} as deferred (not MVP) "
            f"in the Technical Architecture mvp_scope.deferred list. Do not remove "
            f"the component — mark it as explicitly deferred. "
            f"Reason: {rationale}. "
            f"Post-condition: {post_condition}."
        ),
    }

    return templates.get(action_type, f"[Synthesis {action_type}] {rationale}")


def verify_post_condition(
    action: dict[str, Any],
    regenerated_content: dict[str, Any],
) -> bool:
    """Verify a post-condition against regenerated content.

    This is a best-effort check. Post-conditions are human-readable
    assertions, not executable code. This function checks common
    patterns mechanically.

    Returns True if verification passes or is inconclusive,
    False if a clear violation is detected.
    """
    post_condition = action.get("post_condition", "")
    action_type = action.get("action_type", "")
    targets = action.get("targets", [])

    if action_type == "REMOVE_WS":
        # Check that removed WS IDs don't appear in content
        content_str = str(regenerated_content)
        for target in targets:
            if target in content_str:
                logger.warning(
                    "Post-condition violation: %s still present after REMOVE_WS",
                    target,
                )
                return False
        return True

    if action_type == "DEFER_COMPONENT":
        # Check that component appears in mvp_scope.deferred
        mvp_scope = regenerated_content.get("mvp_scope", {})
        deferred = mvp_scope.get("deferred", [])
        for target in targets:
            if not any(target.lower() in d.lower() for d in deferred):
                logger.warning(
                    "Post-condition violation: %s not in mvp_scope.deferred",
                    target,
                )
                return False
        return True

    # For other action types, return True (inconclusive — human should verify)
    logger.info(
        "Post-condition for %s is not mechanically verifiable; operator should check",
        action_type,
    )
    return True
