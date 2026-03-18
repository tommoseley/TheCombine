"""
WP Defect Evaluator (WS-PI-3A).

Evaluates parsed JSON output from WP-generation LLM runs against
structured defect categories. Produces a pass/fail/advisory/not_evaluable
report per check.

Scoped to work_package artifact type only.
Same pattern as ws_defect_evaluator.py.
"""

from dataclasses import dataclass, field


# Required top-level sections in a WP
_REQUIRED_SECTIONS = [
    "wp_id",
    "title",
    "rationale",
    "governance_pins",
]

# Required fields that accept scope_in/scope_out as alternative to scope
_SCOPE_FIELDS = ["scope_in", "scope_out", "scope"]


@dataclass
class WPEvaluationReport:
    """Structured evaluation report for a WP output."""
    artifact_type: str = "work_package"
    evaluator_version: str = "1.0"
    checks: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def _check(check_id: str, status: str, evidence: str, notes: str) -> dict:
    return {
        "check_id": check_id,
        "status": status,
        "evidence": evidence,
        "notes": notes,
    }


def _check_governance_pins(wp: dict) -> dict:
    """Check governance_pins populated with ta_version_id and policy_refs."""
    pins = wp.get("governance_pins")
    if not pins or not isinstance(pins, dict):
        return _check(
            "governance_pins_populated", "fail",
            "governance_pins section missing or not a dict",
            "",
        )

    issues = []
    ta_id = pins.get("ta_version_id")
    if not ta_id or (isinstance(ta_id, str) and not ta_id.strip()):
        issues.append("ta_version_id missing or empty")

    policy_refs = pins.get("policy_refs")
    if not policy_refs or (isinstance(policy_refs, list) and len(policy_refs) == 0):
        issues.append("policy_refs missing or empty")

    if issues:
        return _check(
            "governance_pins_populated", "fail",
            "; ".join(issues),
            "",
        )

    return _check(
        "governance_pins_populated", "pass",
        f"ta_version_id={ta_id}, policy_refs={policy_refs}",
        "",
    )


def _check_required_sections(wp: dict) -> dict:
    """Check all required WP sections are present."""
    missing = []
    for s in _REQUIRED_SECTIONS:
        if s not in wp:
            missing.append(s)

    # Scope: accept scope, scope_in, or scope_out
    has_scope = any(s in wp for s in _SCOPE_FIELDS)
    if not has_scope:
        missing.append("scope (or scope_in/scope_out)")

    if missing:
        total = len(_REQUIRED_SECTIONS) + 1  # +1 for scope
        present = total - len(missing)
        return _check(
            "required_sections_present", "fail",
            f"Missing sections: {', '.join(missing)}",
            f"{present}/{total} present",
        )

    total = len(_REQUIRED_SECTIONS) + 1
    return _check(
        "required_sections_present", "pass",
        f"All {total} required sections present",
        "",
    )


def _check_policy_floor(wp: dict) -> dict:
    """Check that POL-ADR-EXEC-001 is in governance_pins.policy_refs."""
    pins = wp.get("governance_pins") or {}
    policy_refs = pins.get("policy_refs") or []

    if "POL-ADR-EXEC-001" in policy_refs:
        return _check(
            "policy_floor_present", "pass",
            f"POL-ADR-EXEC-001 found in policy_refs ({len(policy_refs)} total)",
            "",
        )

    return _check(
        "policy_floor_present", "fail",
        f"POL-ADR-EXEC-001 not in policy_refs: {policy_refs}",
        "WP governance floor requires POL-ADR-EXEC-001 per ADR-058",
    )


def _check_contradiction_disclosure(wp: dict) -> dict:
    """Check whether contradiction notes are present. Pass or not_evaluable."""
    notes = wp.get("contradiction_notes")
    if notes and isinstance(notes, list) and len(notes) > 0:
        return _check(
            "contradiction_disclosure_present", "pass",
            f"{len(notes)} contradiction(s) disclosed",
            "; ".join(str(n)[:100] for n in notes),
        )

    for key in ("contradiction_flags", "conflicts", "conflict_notes"):
        val = wp.get(key)
        if val and isinstance(val, list) and len(val) > 0:
            return _check(
                "contradiction_disclosure_present", "pass",
                f"{len(val)} item(s) in {key}",
                "; ".join(str(v)[:100] for v in val),
            )

    return _check(
        "contradiction_disclosure_present", "not_evaluable",
        "No contradiction/conflict disclosure fields found",
        "Cannot confirm absence of contradictions from output alone",
    )


def _check_ws_index_present(wp: dict) -> dict:
    """Check whether ws_index exists and is non-empty (advisory)."""
    ws_index = wp.get("ws_index")
    if ws_index and isinstance(ws_index, list) and len(ws_index) > 0:
        return _check(
            "ws_index_present", "pass",
            f"ws_index contains {len(ws_index)} entries",
            "",
        )

    if ws_index is not None and isinstance(ws_index, list) and len(ws_index) == 0:
        return _check(
            "ws_index_present", "advisory",
            "ws_index exists but is empty",
            "WP has no Work Statement references — may be newly created",
        )

    return _check(
        "ws_index_present", "advisory",
        "ws_index not present",
        "WP may not yet have Work Statements assigned",
    )


def evaluate_wp(wp: dict) -> WPEvaluationReport:
    """
    Evaluate a parsed WP JSON against defect categories.

    Returns a WPEvaluationReport with per-check results and summary counts.
    """
    checks = [
        _check_governance_pins(wp),
        _check_required_sections(wp),
        _check_policy_floor(wp),
        _check_contradiction_disclosure(wp),
        _check_ws_index_present(wp),
    ]

    summary = {"passed": 0, "failed": 0, "advisory": 0, "not_evaluable": 0}
    for c in checks:
        status = c["status"]
        if status == "pass":
            summary["passed"] += 1
        elif status == "fail":
            summary["failed"] += 1
        elif status == "advisory":
            summary["advisory"] += 1
        elif status == "not_evaluable":
            summary["not_evaluable"] += 1

    return WPEvaluationReport(checks=checks, summary=summary)
