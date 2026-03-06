"""
IA gate for render endpoints (WS-RENDER-003).

Verifies that a document's content has sufficient IA-declared fields
before allowing rendering. Returns PASS/FAIL/SKIP status.

The gate uses a coverage threshold (default 50%): if at least half of the
IA-declared fields are present, the document passes. Individual missing
fields are reported as warnings but do not block rendering. A document
only fails when fewer than the threshold of declared fields are present,
indicating the content is fundamentally incomplete or corrupt.

Pure function — no DB, no side effects.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Minimum fraction of IA-declared fields that must be present to pass.
_COVERAGE_THRESHOLD = 0.5


def verify_document_ia(
    content: Dict[str, Any],
    ia: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Verify that document content has sufficient IA-declared fields.

    Args:
        content: Document content dict (canonical JSON body).
        ia: Information architecture dict from package.yaml.
            If None, the document type has no IA definitions.

    Returns:
        Dict with:
            - status: "PASS" | "FAIL" | "SKIP"
            - warnings: List of missing field descriptions (present even on PASS)
            - failures: List of failure descriptions (non-empty only on FAIL)
            - coverage: fraction of IA fields present (0.0-1.0)
    """
    # No IA definitions → gate skipped (not failed)
    if ia is None:
        return {"status": "SKIP", "failures": [], "warnings": [], "coverage": None}

    sections = ia.get("sections", [])
    if not sections:
        return {"status": "PASS", "failures": [], "warnings": [], "coverage": 1.0}

    # Collect all bind paths and check presence
    total = 0
    present = 0
    missing: List[str] = []

    for section in sections:
        binds = section.get("binds", [])
        for bind in binds:
            path = bind.get("path", "")
            if not path:
                continue
            total += 1
            value = _resolve_path(content, path)
            if value is None:
                missing.append(f"Missing field: {path}")
            else:
                present += 1

    if total == 0:
        return {"status": "PASS", "failures": [], "warnings": [], "coverage": 1.0}

    coverage = present / total

    if coverage < _COVERAGE_THRESHOLD:
        return {
            "status": "FAIL",
            "failures": missing,
            "warnings": [],
            "coverage": coverage,
        }

    return {
        "status": "PASS",
        "failures": [],
        "warnings": missing,
        "coverage": coverage,
    }


def _resolve_path(content: Dict[str, Any], path: str) -> Any:
    """Resolve a dot-separated path in the content dict."""
    if not path:
        return None
    if "." not in path:
        return content.get(path)
    parts = path.split(".")
    current = content
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current
