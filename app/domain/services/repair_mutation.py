"""
Repair Mutation Service (ADR-065, WS-REPAIR-004).

Applies accepted repair proposals to TA documents (pre-stabilization only).
Reruns evaluation after mutation to verify finding clearance.

Pure functions where possible — mutation requires DB access.
"""

import logging
from typing import Any

from app.domain.models.repair_proposal import RepairProposalDTO
from app.domain.services.cross_layer_evaluator import validate_ta_owns

logger = logging.getLogger(__name__)


# Pre-stabilization states that allow mutation
MUTABLE_STATES = {"draft", "qa_failed", "active", None}


def replace_component(
    ta_content: dict[str, Any],
    component_name: str,
    new_component: dict[str, Any],
) -> dict[str, Any]:
    """Replace a single component in TA content by name.

    Pure function — returns new content dict, does not mutate input.
    Raises ValueError if component not found.
    """
    components = ta_content.get("components") or []
    found = False
    new_components = []

    for comp in components:
        if comp.get("name") == component_name:
            new_components.append(new_component)
            found = True
        else:
            new_components.append(comp)

    if not found:
        raise ValueError(f"Component '{component_name}' not found in TA content")

    result = dict(ta_content)
    result["components"] = new_components
    return result


def verify_finding_cleared(
    updated_content: dict[str, Any],
    component_name: str,
) -> bool:
    """Check that the specific component's ownership finding is cleared.

    Returns True if the component no longer has a finding.
    """
    report = validate_ta_owns(updated_content)
    for f in report.findings:
        if f.component_name == component_name:
            return False
    return True


async def apply_accepted_proposal(
    proposal: RepairProposalDTO,
    db,
) -> dict[str, Any]:
    """Apply an accepted repair proposal to the TA document.

    Pre-conditions:
    - proposal.status == "accepted"
    - TA document is in a mutable state (draft, qa_failed)

    Returns dict with:
    - success: bool
    - finding_cleared: bool
    - error: str | None

    Does NOT commit — caller owns transaction.
    """
    from sqlalchemy import select
    from app.api.models.document import Document

    if proposal.status != "accepted":
        return {"success": False, "finding_cleared": False, "error": "Proposal is not accepted"}

    # Load the TA document
    result = await db.execute(
        select(Document).where(Document.id == proposal.artifact_id)
    )
    doc = result.scalar_one_or_none()

    if not doc:
        return {"success": False, "finding_cleared": False, "error": "Document not found"}

    # Check lifecycle state
    lifecycle = getattr(doc, "lifecycle_state", None)
    if lifecycle and lifecycle not in MUTABLE_STATES:
        return {
            "success": False,
            "finding_cleared": False,
            "error": f"Document is in '{lifecycle}' state — only pre-stabilization mutation allowed",
        }

    # Replace component
    try:
        updated_content = replace_component(
            doc.content or {},
            proposal.component_identifier,
            proposal.proposed_payload,
        )
    except ValueError as e:
        return {"success": False, "finding_cleared": False, "error": str(e)}

    # Persist updated content
    doc.content = updated_content

    # Verify finding cleared
    finding_cleared = verify_finding_cleared(updated_content, proposal.component_identifier)

    logger.info(
        "Applied repair proposal %s to document %s (component: %s, finding_cleared: %s)",
        proposal.id, proposal.artifact_id, proposal.component_identifier, finding_cleared,
    )

    return {
        "success": True,
        "finding_cleared": finding_cleared,
        "error": None,
    }
