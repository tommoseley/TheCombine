"""
Linear Rewind Impact Evaluator (ADR-063, WS-REWIND-003).

Given a rewind trigger at stage N, determines the invalidation set
using the linear dependency model: everything at N and after.

Pure functions — no side effects, no database mutations.
"""

import logging
from typing import List
from uuid import UUID

from app.domain.models.pipeline_stage import PipelineStage

logger = logging.getLogger(__name__)


def evaluate_rewind_impact(rewind_stage: PipelineStage) -> List[PipelineStage]:
    """
    Determine which stages are affected by a rewind to the given stage.

    Returns the rewind stage itself plus all downstream stages.
    This is the invalidation set — all documents at these stages
    must be marked stale.

    Args:
        rewind_stage: The stage to rewind to.

    Returns:
        List of affected stages in pipeline order.
    """
    return rewind_stage.stages_at_and_after()


def evaluate_rewind_impact_safe(stage_name: str) -> List[PipelineStage]:
    """
    Same as evaluate_rewind_impact but accepts a string stage name.

    If the stage name is invalid, applies the conservative default:
    rewind to CI (earliest stage), invalidating the entire pipeline.

    Args:
        stage_name: Stage name (e.g., "TA", "WP") or doc_type_id.

    Returns:
        List of affected stages in pipeline order.
    """
    # Try by enum name first
    try:
        stage = PipelineStage[stage_name.upper()]
        return evaluate_rewind_impact(stage)
    except KeyError:
        pass

    # Try by doc_type_id
    try:
        stage = PipelineStage.from_doc_type_id(stage_name)
        return evaluate_rewind_impact(stage)
    except ValueError:
        pass

    # Conservative default: rewind to CI (full pipeline invalidation)
    logger.warning(
        "Unknown stage '%s' — applying conservative default: "
        "rewind to CI (full pipeline invalidation)",
        stage_name,
    )
    return evaluate_rewind_impact(PipelineStage.CI)


def get_affected_doc_type_ids(rewind_stage: PipelineStage) -> List[str]:
    """
    Get the document type IDs that would be affected by a rewind.

    Includes non-stage artifact types that are derived from affected stages:
    - work_package_candidate: derived from IP, must be invalidated when IP is affected.

    Args:
        rewind_stage: The stage to rewind to.

    Returns:
        List of doc_type_id strings for affected stages + derived types.
    """
    affected_stages = evaluate_rewind_impact(rewind_stage)
    doc_type_ids = [stage.doc_type_id for stage in affected_stages]

    # WPCs are derived from IP — invalidate them when IP is in the affected set
    if any(s == PipelineStage.IP for s in affected_stages):
        if "work_package_candidate" not in doc_type_ids:
            doc_type_ids.append("work_package_candidate")

    return doc_type_ids
