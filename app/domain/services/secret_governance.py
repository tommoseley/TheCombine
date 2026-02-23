"""
Orchestrator Tier-0 Secret Governance Gate.

Per GOV-SEC-T0-002 Section 7: detector must run on PGC user answers,
generated artifacts before stabilization, render inputs, and replay payloads.

If secret detected: HARD_STOP — abort node execution, roll back transaction,
prevent persistence, emit structured governance event.

This is Gate 2 of the dual-gate architecture.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from app.core.secret_detector import scan_text, scan_dict, redact_for_logging, ScanResult

logger = logging.getLogger(__name__)


class SecretHardStop(Exception):
    """HARD_STOP: secret material detected at Tier-0 governance boundary.

    Per GOV-SEC-T0-002 Section 8:
    - Immediate termination of current workflow node
    - Transaction rollback
    - No stabilization, rendering, or artifact persistence
    - Redacted logging only
    """

    def __init__(self, scan_result: ScanResult, context: str = ""):
        self.scan_result = scan_result
        self.context = context
        self.audit = redact_for_logging(scan_result)
        super().__init__(
            f"HARD_STOP: secret detected at {context} "
            f"(classification={scan_result.classification})"
        )


@dataclass(frozen=True)
class GovernanceEvent:
    """Structured governance event emitted on detection."""
    event_type: str  # "secret_hard_stop" or "secret_scan_clean"
    context: str  # Where detection occurred
    detector_version: str
    verdict: str
    classification: Optional[str]


def check_pgc_answers(answers: dict) -> ScanResult:
    """Scan PGC user answers for secret material.

    Called after user submits answers, before context_state mutation.
    """
    return scan_dict(answers)


def check_artifact(content: dict | str) -> ScanResult:
    """Scan generated artifact before stabilization.

    Called after LLM generation, before document persistence.
    """
    if isinstance(content, dict):
        return scan_dict(content)
    return scan_text(str(content))


def check_render_input(content: str) -> ScanResult:
    """Scan content before rendering to HTML or PDF.

    Called before detail_html or pdf render.
    """
    return scan_text(content)


def check_replay_payload(payload: dict | str) -> ScanResult:
    """Scan replay/connector payload for secret material.

    Called on replay ingestion before LLM execution.
    """
    if isinstance(payload, dict):
        return scan_dict(payload)
    return scan_text(str(payload))


def enforce(scan_result: ScanResult, context: str) -> GovernanceEvent:
    """Enforce governance policy on a scan result.

    If secret detected: raises SecretHardStop.
    If clean: returns GovernanceEvent for audit.

    Args:
        scan_result: Result from any scan_* function
        context: Description of where the scan occurred (for audit)

    Returns:
        GovernanceEvent for clean results

    Raises:
        SecretHardStop: If secret material detected
    """
    if scan_result.verdict == "SECRET_DETECTED":
        audit = redact_for_logging(scan_result)
        logger.warning(
            "HARD_STOP: Secret detected at %s | %s",
            context, audit,
        )
        raise SecretHardStop(scan_result, context)

    return GovernanceEvent(
        event_type="secret_scan_clean",
        context=context,
        detector_version=scan_result.detector_version,
        verdict=scan_result.verdict,
        classification=scan_result.classification,
    )


def audit_metadata(scan_result: ScanResult) -> dict:
    """Produce audit metadata for workflow execution records.

    Per WS-PGC-SEC-002 Section 4: every scan must record
    detector_version, verdict, and entropy_score.
    """
    meta = {
        "secret_scan": {
            "detector_version": scan_result.detector_version,
            "verdict": scan_result.verdict,
        }
    }
    if scan_result.verdict == "SECRET_DETECTED":
        meta["secret_scan"]["classification"] = scan_result.classification
    else:
        meta["secret_scan"]["entropy_score"] = round(scan_result.entropy_score, 3)
    return meta
