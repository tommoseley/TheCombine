"""Pure functions for QA response parsing and validation -- WS-CRAP-001.

Extracted from QANodeExecutor._parse_qa_response() (Target 4, CC=27, CRAP=714.0)
and QANodeExecutor.execute() (Target 2, CC=40, CRAP=1580.7).
These functions contain no I/O, no logging, and no side effects.
"""

import json
import re
from typing import Any, Dict, List, Optional


def strip_code_fences(text: str) -> str:
    """Strip markdown code fences from text.

    Handles ```json and ``` wrapping commonly used by LLMs.

    Args:
        text: Raw text potentially wrapped in code fences

    Returns:
        Text with code fences removed, stripped
    """
    s = text.strip()
    if s.startswith("```json"):
        s = s[7:]
    if s.startswith("```"):
        s = s[3:]
    if s.endswith("```"):
        s = s[:-3]
    return s.strip()


def try_parse_json_qa(text: str) -> Optional[Dict[str, Any]]:
    """Try to parse QA response as structured JSON.

    Expects a JSON object with at least a "passed" key.
    Normalizes issues from list-of-dicts to list-of-strings.

    Args:
        text: Raw LLM response (may have code fences)

    Returns:
        Dict with passed, issues, feedback -- or None if not valid JSON QA
    """
    json_str = strip_code_fences(text)
    try:
        parsed = json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(parsed, dict) or "passed" not in parsed:
        return None

    passed = bool(parsed["passed"])
    issues = parsed.get("issues", [])
    # Normalize issues: list of dicts -> list of strings
    if issues and isinstance(issues[0], dict):
        issues = [issue.get("message", str(issue)) for issue in issues]
    summary = parsed.get("summary", "")

    return {
        "passed": passed,
        "issues": issues,
        "feedback": summary or text,
    }


# Compiled regex for Result: PASS/FAIL detection
_RESULT_PATTERN = re.compile(r"\*?\*?result\*?\*?:?\s*(pass|fail)")

# Keyword indicators for pass/fail heuristics
PASS_INDICATORS = [
    "passes all",
    "meets requirements",
    "approved",
    "no issues found",
    "quality: pass",
]

FAIL_INDICATORS = [
    "fails",
    "issues found",
    "rejected",
    "needs revision",
    "quality: fail",
]


def detect_pass_fail(text: str) -> bool:
    """Detect pass/fail from free-text QA response.

    Uses three tiers:
    1. Regex match for explicit "Result: PASS/FAIL"
    2. Keyword heuristics
    3. Ambiguous default -> pass

    Args:
        text: QA response text (not JSON)

    Returns:
        True if pass, False if fail
    """
    text_lower = text.lower()

    # Tier 1: Explicit Result line
    result_match = _RESULT_PATTERN.search(text_lower)
    if result_match:
        return result_match.group(1) == "pass"

    # Tier 2: Keyword heuristics
    if any(ind in text_lower for ind in PASS_INDICATORS):
        return True
    if any(ind in text_lower for ind in FAIL_INDICATORS):
        return False

    # Tier 3: Ambiguous default
    return True


# Bullet prefixes for issue extraction (includes mojibake bullet from legacy code)
_BULLET_PREFIXES = ("-", "*", "\xe2\x80\xa2", "[")
_BULLET_CLEAN_RE = re.compile(r"^[-*\xe2\x80\xa2\[\]]+\s*")


def extract_issues_from_text(text: str) -> List[str]:
    """Extract issue bullet points from QA response text.

    Looks for a "### Issues" or "issues found" section and extracts
    up to 9 bullet points.

    Args:
        text: QA response text

    Returns:
        List of issue strings
    """
    text_lower = text.lower()
    issues: List[str] = []

    issues_start = text_lower.find("### issues")
    if issues_start == -1:
        issues_start = text_lower.find("issues found")
    if issues_start == -1:
        return []

    issues_section = text[issues_start:]
    for line in issues_section.split("\n")[1:10]:
        line = line.strip()
        if line and line.startswith(_BULLET_PREFIXES):
            cleaned = _BULLET_CLEAN_RE.sub("", line)
            if cleaned and len(cleaned) > 5:
                issues.append(cleaned)

    return issues


def parse_qa_response(response: str) -> Dict[str, Any]:
    """Parse LLM QA response into structured result.

    Tries JSON parsing first, falls back to text heuristics.

    Args:
        response: Raw LLM response string

    Returns:
        Dict with keys: passed (bool), issues (List[str]), feedback (str)
    """
    # Try structured JSON first
    json_result = try_parse_json_qa(response)
    if json_result is not None:
        return json_result

    # Fall back to text parsing
    passed = detect_pass_fail(response)
    issues = [] if passed else extract_issues_from_text(response)

    return {
        "passed": passed,
        "issues": issues,
        "feedback": response,
    }


# =========================================================================
# Semantic QA contract validation (Target 2)
# =========================================================================


def validate_semantic_qa_contract(
    report: Dict[str, Any],
    expected_constraint_count: int,
    provided_constraint_ids: List[str],
) -> List[str]:
    """Validate semantic QA contract rules.

    Checks coverage count, constraint ID validity, gate consistency,
    and summary count accuracy.

    Args:
        report: Parsed semantic QA report
        expected_constraint_count: Number of constraints provided
        provided_constraint_ids: List of valid constraint IDs

    Returns:
        List of warning messages (empty if all rules pass)
    """
    warnings: List[str] = []
    coverage = report.get("coverage", {})
    findings = report.get("findings", [])
    summary = report.get("summary", {})
    gate = report.get("gate")

    # Rule 1: Coverage count must match
    if coverage.get("expected_count") != expected_constraint_count:
        warnings.append(
            f"Coverage expected_count mismatch: got {coverage.get('expected_count')}, "
            f"expected {expected_constraint_count}"
        )

    # Rule 2: All constraint IDs must be valid
    provided_ids_lower = [cid.lower() for cid in provided_constraint_ids]
    for item in coverage.get("items", []):
        cid = item.get("constraint_id", "")
        if cid.lower() not in provided_ids_lower and cid != "SYSTEM":
            warnings.append(f"Unknown constraint_id in coverage: {cid}")

    for finding in findings:
        cid = finding.get("constraint_id", "")
        if cid.lower() not in provided_ids_lower and cid != "SYSTEM":
            warnings.append(f"Unknown constraint_id in findings: {cid}")

    # Rule 3: Gate must be fail if any contradicted/reopened
    has_error_status = any(
        item.get("status") in ["contradicted", "reopened"]
        for item in coverage.get("items", [])
    )
    if has_error_status and gate != "fail":
        warnings.append(
            f"Gate should be 'fail' due to contradicted/reopened status, but got '{gate}'"
        )

    # Rule 4: Summary counts should match findings
    error_count = len([f for f in findings if f.get("severity") == "error"])
    warning_count = len([f for f in findings if f.get("severity") == "warning"])
    if summary.get("errors") != error_count:
        warnings.append(
            f"Summary errors mismatch: got {summary.get('errors')}, "
            f"counted {error_count}"
        )
    if summary.get("warnings") != warning_count:
        warnings.append(
            f"Summary warnings mismatch: got {summary.get('warnings')}, "
            f"counted {warning_count}"
        )

    return warnings


def convert_semantic_findings_to_feedback(
    report: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Convert semantic QA findings to feedback format.

    Transforms raw semantic QA findings into remediation-compatible
    feedback issues.

    Args:
        report: Semantic QA report

    Returns:
        List of feedback issues compatible with remediation
    """
    feedback_issues: List[Dict[str, Any]] = []

    for finding in report.get("findings", []):
        feedback_issues.append({
            "type": "semantic_qa",
            "check_id": finding.get("code"),
            "severity": finding.get("severity"),
            "message": finding.get("message"),
            "constraint_id": finding.get("constraint_id"),
            "evidence_pointers": finding.get("evidence_pointers", []),
            "remediation": finding.get("suggested_fix"),
        })

    return feedback_issues


def build_qa_success_metadata(
    node_id: str,
    drift_warnings: List[Dict[str, Any]],
    code_validation_warnings: List[Dict[str, Any]],
    semantic_warnings: List[Dict[str, Any]],
    semantic_qa_report: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build metadata dict for a successful QA result.

    Assembles all warning and report data into a single metadata dict.

    Args:
        node_id: The QA node identifier
        drift_warnings: Drift validation warnings
        code_validation_warnings: Code validation warnings
        semantic_warnings: Semantic QA warnings
        semantic_qa_report: Full semantic QA report (if available)

    Returns:
        Metadata dict for NodeResult.success()
    """
    metadata: Dict[str, Any] = {
        "node_id": node_id,
        "qa_passed": True,
    }

    if drift_warnings:
        metadata["drift_warnings"] = drift_warnings

    if code_validation_warnings:
        metadata["code_validation_warnings"] = code_validation_warnings

    if semantic_warnings:
        metadata["semantic_qa_warnings"] = semantic_warnings

    if semantic_qa_report:
        metadata["semantic_qa_report"] = semantic_qa_report

    return metadata
