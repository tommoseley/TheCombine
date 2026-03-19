"""Duplicate WS objective detection per ADR-062.

Detects duplicate implementation intent across Work Statements by
comparing normalized objectives and scope_in items. Uses exact and
near-exact matching — no broad semantic similarity in v1.

Pure functions — no DB, no LLM, deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DuplicateFinding:
    """A single duplicate WS finding."""

    rule_id: str
    ws_ids: list[str]
    parent_wp_ids: list[str]
    duplicate_type: str
    evidence: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "ws_ids": self.ws_ids,
            "parent_wp_ids": self.parent_wp_ids,
            "duplicate_type": self.duplicate_type,
            "evidence": self.evidence,
            "message": self.message,
        }


@dataclass
class DuplicateReport:
    """WS duplicate detection report."""

    ws_count: int
    findings: list[DuplicateFinding] = field(default_factory=list)

    @property
    def summary(self) -> dict[str, int]:
        return {
            "ws_checked": self.ws_count,
            "total_findings": len(self.findings),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "ws_count": self.ws_count,
            "summary": self.summary,
            "findings": [f.to_dict() for f in self.findings],
        }


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset([
    "a", "an", "the", "and", "or", "for", "with", "of", "to", "in",
    "on", "at", "by", "from", "is", "are", "was", "were", "be", "been",
    "that", "this", "it", "its", "all", "each", "any", "via", "per",
    "into", "also", "as", "not", "no", "will", "can", "has", "have",
])


def _normalize_text(text: str) -> str:
    """Normalize text for comparison: lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from normalized text (exclude stop words)."""
    words = _normalize_text(text).split()
    return {w for w in words if w not in _STOP_WORDS and len(w) > 2}


def _keyword_similarity(kw_a: set[str], kw_b: set[str]) -> float:
    """Overlap coefficient between two keyword sets. Returns 0.0–1.0.

    Uses overlap coefficient (intersection / min_set_size) instead of
    Jaccard to avoid penalizing sets with different total sizes.
    This catches cases where one WS is a subset of another's scope.
    """
    if not kw_a or not kw_b:
        return 0.0
    intersection = kw_a & kw_b
    return len(intersection) / min(len(kw_a), len(kw_b))


# ---------------------------------------------------------------------------
# Duplicate checks
# ---------------------------------------------------------------------------

# Similarity threshold for objective overlap (overlap coefficient)
_OBJECTIVE_THRESHOLD = 0.50

# Similarity threshold for scope_in overlap (overlap coefficient)
_SCOPE_THRESHOLD = 0.50


def _check_objective_duplicates(
    ws_data: list[dict[str, Any]],
) -> list[DuplicateFinding]:
    """Check for WS pairs with near-identical objectives across different WPs."""
    findings: list[DuplicateFinding] = []
    reported_pairs: set[tuple[str, str]] = set()

    for i, ws_a in enumerate(ws_data):
        for ws_b in ws_data[i + 1:]:
            # Only flag cross-WP duplicates
            if ws_a["parent_wp_id"] == ws_b["parent_wp_id"]:
                continue

            pair_key = tuple(sorted([ws_a["ws_id"], ws_b["ws_id"]]))
            if pair_key in reported_pairs:
                continue

            sim = _keyword_similarity(ws_a["obj_keywords"], ws_b["obj_keywords"])
            if sim >= _OBJECTIVE_THRESHOLD:
                reported_pairs.add(pair_key)
                findings.append(DuplicateFinding(
                    rule_id="DUP-OBJ-001",
                    ws_ids=sorted([ws_a["ws_id"], ws_b["ws_id"]]),
                    parent_wp_ids=sorted(set([ws_a["parent_wp_id"], ws_b["parent_wp_id"]])),
                    duplicate_type="objective_duplicate",
                    evidence=(
                        f"Objective similarity {sim:.0%}: "
                        f"'{ws_a['objective'][:80]}' vs '{ws_b['objective'][:80]}'"
                    ),
                    message=(
                        f"WS {ws_a['ws_id']} and WS {ws_b['ws_id']} have similar objectives "
                        f"({sim:.0%} keyword overlap) across WPs "
                        f"{ws_a['parent_wp_id']} and {ws_b['parent_wp_id']}"
                    ),
                ))

    return findings


def _check_scope_duplicates(
    ws_data: list[dict[str, Any]],
) -> list[DuplicateFinding]:
    """Check for WS pairs with overlapping scope_in items across different WPs."""
    findings: list[DuplicateFinding] = []
    reported_pairs: set[tuple[str, str]] = set()

    for i, ws_a in enumerate(ws_data):
        for ws_b in ws_data[i + 1:]:
            if ws_a["parent_wp_id"] == ws_b["parent_wp_id"]:
                continue

            pair_key = tuple(sorted([ws_a["ws_id"], ws_b["ws_id"]]))
            if pair_key in reported_pairs:
                continue

            sim = _keyword_similarity(ws_a["scope_keywords"], ws_b["scope_keywords"])
            if sim >= _SCOPE_THRESHOLD:
                reported_pairs.add(pair_key)
                findings.append(DuplicateFinding(
                    rule_id="DUP-SCOPE-001",
                    ws_ids=sorted([ws_a["ws_id"], ws_b["ws_id"]]),
                    parent_wp_ids=sorted(set([ws_a["parent_wp_id"], ws_b["parent_wp_id"]])),
                    duplicate_type="scope_overlap",
                    evidence=f"Scope similarity {sim:.0%} between {ws_a['ws_id']} and {ws_b['ws_id']}",
                    message=(
                        f"WS {ws_a['ws_id']} and WS {ws_b['ws_id']} have overlapping scope "
                        f"({sim:.0%} keyword overlap) across WPs "
                        f"{ws_a['parent_wp_id']} and {ws_b['parent_wp_id']}"
                    ),
                ))

    return findings


# ---------------------------------------------------------------------------
# Main evaluator
# ---------------------------------------------------------------------------

def evaluate_ws_duplicates(
    ws_artifacts: list[dict[str, Any]],
) -> DuplicateReport:
    """Evaluate WS artifacts for duplicate implementation intent.

    Args:
        ws_artifacts: List of WS document dicts, each with 'content' key
                      containing ws_id, parent_wp_id, objective, scope_in.

    Returns:
        DuplicateReport with findings. Empty = no duplicates detected.
    """
    if len(ws_artifacts) < 2:
        return DuplicateReport(ws_count=len(ws_artifacts))

    # Pre-process all WSs
    ws_data: list[dict[str, Any]] = []
    for ws in ws_artifacts:
        content = ws.get("content") or {}
        ws_id = content.get("ws_id", "unknown")
        parent_wp_id = content.get("parent_wp_id", "unknown")
        objective = content.get("objective", "")

        scope_in = content.get("scope_in") or []
        scope_text = " ".join(str(item) for item in scope_in) if isinstance(scope_in, list) else str(scope_in)

        ws_data.append({
            "ws_id": ws_id,
            "parent_wp_id": parent_wp_id,
            "objective": objective,
            "obj_keywords": _extract_keywords(objective),
            "scope_keywords": _extract_keywords(scope_text),
        })

    findings: list[DuplicateFinding] = []
    findings.extend(_check_objective_duplicates(ws_data))
    findings.extend(_check_scope_duplicates(ws_data))

    return DuplicateReport(
        ws_count=len(ws_artifacts),
        findings=findings,
    )
