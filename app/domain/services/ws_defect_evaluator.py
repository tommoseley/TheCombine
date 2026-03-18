"""
WS Defect Evaluator (WS-PI-0B Step 4).

Evaluates parsed JSON output from WS-generation LLM runs against
structured defect categories. Produces a pass/fail/advisory/not_evaluable
report per check.

Scoped to work_statement artifact type only.
"""

import re
from dataclasses import dataclass, field


# Grounding cue patterns — references to upstream artifacts
_GROUNDING_PATTERNS = [
    re.compile(r"\bWP[-_]", re.IGNORECASE),
    re.compile(r"\bTA\b", re.IGNORECASE),
    re.compile(r"\btechnical\s+architecture\b", re.IGNORECASE),
    re.compile(r"\bwork\s+package\b", re.IGNORECASE),
    re.compile(r"\bPOL[-_]", re.IGNORECASE),
    re.compile(r"\bpolicy\b", re.IGNORECASE),
    re.compile(r"\bADR[-_]", re.IGNORECASE),
    re.compile(r"\bfrom\s+\w+[-_]\w+", re.IGNORECASE),
    re.compile(r"\bper\s+(the\s+)?specification\b", re.IGNORECASE),
    re.compile(r"\bsection\s+\d", re.IGNORECASE),
]

# Keywords indicating a test step
_TEST_KEYWORDS = re.compile(
    r"\b(test|tests|testing|verify|verification|validate|validation|assert|check)\b",
    re.IGNORECASE,
)

# Keywords indicating an implementation step
_IMPL_KEYWORDS = re.compile(
    r"\b(implement|create|build|add|write|develop|configure|deploy|install|set\s+up|modify)\b",
    re.IGNORECASE,
)

# Required top-level sections in a WS
_REQUIRED_SECTIONS = [
    "objective",
    "scope",
    "procedure",
    "verification_criteria",
    "allowed_paths",
    "prohibited_actions",
    "governance_pins",
]


@dataclass
class EvaluationReport:
    """Structured evaluation report for a WS output."""
    artifact_type: str = "work_statement"
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


def _check_governance_pins(ws: dict) -> dict:
    """Check governance_pins populated with ta_version_id and policy_refs."""
    pins = ws.get("governance_pins")
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


def _has_scope(ws: dict) -> bool:
    """Check if WS has scope in any accepted form.

    Accepts either:
    - "scope" key (nested dict with in_scope/out_of_scope)
    - "scope_in" + "scope_out" keys (flat legacy shape)
    """
    if "scope" in ws:
        return True
    if "scope_in" in ws or "scope_out" in ws:
        return True
    return False


def _check_required_sections(ws: dict) -> dict:
    """Check all required WS sections are present."""
    missing = []
    for s in _REQUIRED_SECTIONS:
        if s == "scope":
            if not _has_scope(ws):
                missing.append(s)
        elif s not in ws:
            missing.append(s)

    if missing:
        return _check(
            "required_sections_present", "fail",
            f"Missing sections: {', '.join(missing)}",
            f"{len(_REQUIRED_SECTIONS) - len(missing)}/{len(_REQUIRED_SECTIONS)} present",
        )

    return _check(
        "required_sections_present", "pass",
        f"All {len(_REQUIRED_SECTIONS)} required sections present",
        "",
    )


def _check_tests_before_implementation(ws: dict) -> dict:
    """Check that test steps precede implementation steps in procedure."""
    procedure = ws.get("procedure")
    if not procedure or not isinstance(procedure, list):
        return _check(
            "tests_before_implementation", "fail",
            "No procedure found or procedure is not a list",
            "",
        )

    first_test_idx = None
    first_impl_idx = None

    for i, step in enumerate(procedure):
        text = ""
        if isinstance(step, dict):
            text = step.get("action", "") or step.get("description", "") or str(step)
        elif isinstance(step, str):
            text = step

        is_test = bool(_TEST_KEYWORDS.search(text))
        is_impl = bool(_IMPL_KEYWORDS.search(text))

        # When both keywords present, classify by dominant intent:
        # "Write failing tests" is a test step — the object (tests) determines intent
        if is_test and is_impl:
            is_impl = False

        if is_test:
            if first_test_idx is None:
                first_test_idx = i
        elif is_impl:
            if first_impl_idx is None:
                first_impl_idx = i

    if first_test_idx is None:
        return _check(
            "tests_before_implementation", "fail",
            "No test steps identified in procedure",
            "Could not find steps with test/verify keywords that aren't also implementation steps",
        )

    if first_impl_idx is None:
        return _check(
            "tests_before_implementation", "pass",
            f"Test step at index {first_test_idx}, no pure implementation steps found",
            "",
        )

    if first_test_idx < first_impl_idx:
        return _check(
            "tests_before_implementation", "pass",
            f"First test at step {first_test_idx}, first impl at step {first_impl_idx}",
            "",
        )

    return _check(
        "tests_before_implementation", "fail",
        f"First implementation at step {first_impl_idx} precedes first test at step {first_test_idx}",
        "Tests must come before implementation per POL-QA-001",
    )


def _check_step_grounding(ws: dict) -> dict:
    """Heuristic: flag steps lacking grounding cues. Always advisory."""
    procedure = ws.get("procedure")
    if not procedure or not isinstance(procedure, list):
        return _check(
            "step_grounding_heuristic", "advisory",
            "No procedure found",
            "Cannot evaluate grounding without procedure steps",
        )

    ungrounded = []
    for i, step in enumerate(procedure):
        text = ""
        if isinstance(step, dict):
            text = step.get("action", "") or step.get("description", "") or str(step)
        elif isinstance(step, str):
            text = step

        has_grounding = any(p.search(text) for p in _GROUNDING_PATTERNS)
        if not has_grounding:
            ungrounded.append(f"step {i}: {text[:80]}")

    if ungrounded:
        return _check(
            "step_grounding_heuristic", "advisory",
            f"{len(ungrounded)} steps lack grounding cues: {'; '.join(ungrounded)}",
            "Heuristic check — steps may still be valid",
        )

    return _check(
        "step_grounding_heuristic", "advisory",
        f"0 ungrounded steps out of {len(procedure)}",
        "All steps contain grounding cues referencing upstream artifacts",
    )


def _check_contradiction_disclosure(ws: dict) -> dict:
    """Check whether contradiction notes are present. Pass or not_evaluable."""
    notes = ws.get("contradiction_notes")
    if notes and isinstance(notes, list) and len(notes) > 0:
        return _check(
            "contradiction_disclosure_present", "pass",
            f"{len(notes)} contradiction(s) disclosed",
            "; ".join(str(n)[:100] for n in notes),
        )

    # Also check for contradiction_flags or conflicts keys
    for key in ("contradiction_flags", "conflicts", "conflict_notes"):
        val = ws.get(key)
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


def evaluate_ws(ws: dict) -> EvaluationReport:
    """
    Evaluate a parsed WS JSON against defect categories.

    Returns an EvaluationReport with per-check results and summary counts.
    """
    checks = [
        _check_governance_pins(ws),
        _check_required_sections(ws),
        _check_tests_before_implementation(ws),
        _check_step_grounding(ws),
        _check_contradiction_disclosure(ws),
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

    return EvaluationReport(checks=checks, summary=summary)
