"""
Binder Synthesis Service (ADR-070).

Executes dual-instance binder analysis and produces a Synthesis Delta
containing mechanical actions and judgment questions. Each instance
analyzes the binder independently; findings are compared mechanically
for agreement scoring.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.domain.services.task_execution_service import (
    execute_task,
    TaskOutputValidationError,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SYNTHESIS_TASK_ID = "binder_synthesis"
SYNTHESIS_TASK_VERSION = "1.1.0"
SYNTHESIS_SCHEMA_ID = "synthesis_delta"

VALID_ACTION_TYPES = frozenset(
    ["MERGE_WS", "SPLIT_WS", "DEFER_COMPONENT", "REMOVE_WS", "NORMALIZE_BOUNDARY"]
)
VALID_LENSES = frozenset(
    ["platform_realism", "mvp_discipline", "authority_hygiene", "execution_readiness"]
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class SynthesisFinding:
    """A single finding from one instance, normalized for comparison."""

    finding_type: str  # "action" or "question"
    action_type: str | None  # e.g. MERGE_WS, or None for questions
    lens: str | None  # e.g. platform_realism, or None for actions
    target_ids: frozenset[str]  # sorted artifact IDs for comparison
    raw: dict[str, Any]  # original finding dict


@dataclass
class SynthesisDelta:
    """The complete synthesis output with agreement scoring."""

    project_id: str
    binder_document_count: int
    instance_a_finding_count: int
    instance_b_finding_count: int
    agreement_count: int
    actions: list[dict[str, Any]]
    questions: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "binder_document_count": self.binder_document_count,
            "instance_a_finding_count": self.instance_a_finding_count,
            "instance_b_finding_count": self.instance_b_finding_count,
            "agreement_count": self.agreement_count,
            "actions": self.actions,
            "questions": self.questions,
        }


# ---------------------------------------------------------------------------
# Core service
# ---------------------------------------------------------------------------


async def execute_synthesis(
    project_id: str,
    binder_content: str,
    binder_document_count: int,
    *,
    llm_client: Any = None,
) -> SynthesisDelta:
    """Execute dual-instance binder synthesis analysis.

    Calls the LLM twice independently with the same prompt and binder,
    normalizes findings, scores agreement, and produces a SynthesisDelta.

    Args:
        project_id: Project identifier
        binder_content: Full binder markdown content
        binder_document_count: Number of documents in the binder
        llm_client: Optional LLM client (injected for testing)

    Returns:
        SynthesisDelta with classified findings and agreement scores
    """
    inputs = {"binder_content": binder_content}

    # --- Instance A ---
    logger.info("Synthesis instance A: starting analysis")
    result_a = await execute_task(
        task_id=SYNTHESIS_TASK_ID,
        version=SYNTHESIS_TASK_VERSION,
        inputs=inputs,
        expected_schema_id=SYNTHESIS_SCHEMA_ID,
        llm_client=llm_client,
    )
    output_a = result_a["output"]

    # --- Instance B ---
    logger.info("Synthesis instance B: starting analysis")
    result_b = await execute_task(
        task_id=SYNTHESIS_TASK_ID,
        version=SYNTHESIS_TASK_VERSION,
        inputs=inputs,
        expected_schema_id=SYNTHESIS_SCHEMA_ID,
        llm_client=llm_client,
    )
    output_b = result_b["output"]

    # --- Normalize and compare ---
    findings_a = _extract_findings(output_a)
    findings_b = _extract_findings(output_b)

    merged = _merge_findings(findings_a, findings_b)

    # --- Build delta ---
    actions = [f["raw"] for f in merged if f["finding_type"] == "action"]
    questions = [f["raw"] for f in merged if f["finding_type"] == "question"]
    agreement_count = sum(1 for f in merged if f["confidence"] == "high")

    delta = SynthesisDelta(
        project_id=project_id,
        binder_document_count=binder_document_count,
        instance_a_finding_count=len(findings_a),
        instance_b_finding_count=len(findings_b),
        agreement_count=agreement_count,
        actions=actions,
        questions=questions,
    )

    logger.info(
        "Synthesis complete: %d actions, %d questions, %d agreements",
        len(actions),
        len(questions),
        agreement_count,
    )
    return delta


# ---------------------------------------------------------------------------
# Finding extraction and normalization
# ---------------------------------------------------------------------------


def _extract_findings(output: dict[str, Any]) -> list[SynthesisFinding]:
    """Extract and normalize findings from a single instance output."""
    findings = []

    for action in output.get("actions", []):
        findings.append(
            SynthesisFinding(
                finding_type="action",
                action_type=action.get("action_type"),
                lens=None,
                target_ids=frozenset(action.get("targets", [])),
                raw=action,
            )
        )

    for question in output.get("questions", []):
        findings.append(
            SynthesisFinding(
                finding_type="question",
                action_type=None,
                lens=question.get("lens"),
                target_ids=frozenset(question.get("artifacts", [])),
                raw=question,
            )
        )

    return findings


def _normalize_key(finding: SynthesisFinding) -> tuple:
    """Produce a canonical key for agreement comparison.

    Two findings match if they have the same type, action_type/lens,
    and target the same artifacts (regardless of order).
    """
    return (
        finding.finding_type,
        finding.action_type or finding.lens,
        finding.target_ids,
    )


def _merge_findings(
    findings_a: list[SynthesisFinding],
    findings_b: list[SynthesisFinding],
) -> list[dict[str, Any]]:
    """Merge findings from two instances with agreement scoring.

    - If both instances produced a matching finding: confidence = "high"
    - If only one instance produced it: confidence = "moderate"
    - When both match, instance A's raw output is used (arbitrary but consistent)

    Returns list of dicts with finding_type, confidence, and raw fields.
    """
    keys_a = {_normalize_key(f): f for f in findings_a}
    keys_b = {_normalize_key(f): f for f in findings_b}

    all_keys = set(keys_a.keys()) | set(keys_b.keys())
    merged = []

    for key in all_keys:
        in_a = key in keys_a
        in_b = key in keys_b
        confidence = "high" if (in_a and in_b) else "moderate"

        # Use A's version if available, else B's
        finding = keys_a.get(key) or keys_b[key]
        raw = dict(finding.raw)
        raw["confidence"] = confidence

        merged.append(
            {
                "finding_type": finding.finding_type,
                "confidence": confidence,
                "raw": raw,
            }
        )

    return merged
