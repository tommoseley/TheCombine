"""
Repair Service (ADR-065, WS-REPAIR-002).

Generates component-scoped repair proposals for TA artifacts.
Uses LLM to produce corrected component, validates output,
stores as RepairProposal.

Pure service — no DB commits, caller owns transaction.
"""

import json
import logging
from typing import Any, Optional, Protocol, runtime_checkable
from uuid import UUID

from app.domain.models.repair_proposal import RepairProposalDTO
from app.domain.repositories.repair_proposal_repository import RepairProposalRepository
from app.domain.services.cross_layer_evaluator import TAOwnsValidationFinding

logger = logging.getLogger(__name__)


@runtime_checkable
class RepairLLMClient(Protocol):
    """Protocol for LLM client used by repair service."""

    async def complete(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str: ...


def build_repair_prompt(
    component: dict[str, Any],
    finding: TAOwnsValidationFinding,
    ta_context: list[dict[str, Any]],
) -> str:
    """Build the repair prompt from task template + inputs.

    Pure function — no I/O.
    """
    from app.config.package_loader import get_package_loader

    loader = get_package_loader()
    task = loader.get_task("repair_ta_component", "1.0.0")
    prompt = task.content

    # Substitute template variables
    prompt = prompt.replace("{{FINDING}}", json.dumps(finding.to_dict(), indent=2))
    prompt = prompt.replace("{{COMPONENT}}", json.dumps(component, indent=2))

    # Minimal context: other component names + their owns for reference
    context_summary = []
    for c in ta_context:
        if c.get("name") != component.get("name"):
            context_summary.append({
                "name": c.get("name"),
                "purpose": c.get("purpose", ""),
                "owns": c.get("owns", []),
            })
    prompt = prompt.replace("{{TA_CONTEXT}}", json.dumps(context_summary, indent=2))

    return prompt


def validate_repair_output(
    output: dict[str, Any],
    original: dict[str, Any],
) -> list[str]:
    """Validate repair output against constraints.

    Returns list of error messages. Empty = valid.
    """
    errors = []

    # Must have name matching original
    if output.get("name") != original.get("name"):
        errors.append(
            f"Component name changed: '{original.get('name')}' → '{output.get('name')}'"
        )

    # Must have non-empty owns
    owns = output.get("owns")
    if not isinstance(owns, list) or len(owns) == 0:
        errors.append("Repaired component still has empty or missing owns[]")
    elif all(not (isinstance(o, str) and o.strip()) for o in owns):
        errors.append("Repaired component owns[] contains only blank entries")

    return errors


async def generate_repair_proposal(
    artifact_id: UUID,
    component: dict[str, Any],
    finding: TAOwnsValidationFinding,
    ta_components: list[dict[str, Any]],
    llm_client: RepairLLMClient,
    repo: RepairProposalRepository,
    actor: str = "system",
) -> Optional[RepairProposalDTO]:
    """Generate a repair proposal for a TA component.

    Args:
        artifact_id: The TA document ID.
        component: The current component dict from the TA.
        finding: The TAOwnsValidationFinding that triggered repair.
        ta_components: All components from the TA (for context).
        llm_client: Injectable LLM client.
        repo: Repair proposal repository.
        actor: Who initiated the repair.

    Returns:
        RepairProposalDTO if valid proposal generated, None if LLM output invalid.
    """
    prompt = build_repair_prompt(component, finding, ta_components)

    # Role prompt
    from app.config.package_loader import get_package_loader
    loader = get_package_loader()
    role = loader.get_role("technical_architect")
    role_prompt = role.content

    logger.info(
        "Generating repair proposal for component '%s' in artifact %s",
        component.get("name"),
        artifact_id,
    )

    # LLM call
    raw_output = await llm_client.complete(
        messages=[{"role": "user", "content": prompt}],
        system_prompt=role_prompt,
    )

    # Parse JSON
    from app.domain.services.llm_response_parser import LLMResponseParser
    parser = LLMResponseParser()
    try:
        result = parser.parse(raw_output)
        if not result.success or result.data is None:
            logger.warning(f"Repair LLM output not valid JSON: {result.error}")
            return None
        proposed = result.data
    except Exception as e:
        logger.warning(f"Repair LLM output parsing failed: {e}")
        return None

    if not isinstance(proposed, dict):
        logger.warning("Repair LLM output is not a JSON object")
        return None

    # Validate constraints
    errors = validate_repair_output(proposed, component)
    if errors:
        logger.warning(f"Repair output validation failed: {errors}")
        return None

    # Create proposal
    proposal = RepairProposalDTO.create(
        artifact_id=artifact_id,
        artifact_type="TA",
        component_identifier=component.get("name", "unknown"),
        trigger_finding=finding.to_dict(),
        proposed_payload=proposed,
        created_by=actor,
    )

    await repo.add(proposal)
    logger.info(f"Created repair proposal {proposal.id}")

    return proposal
