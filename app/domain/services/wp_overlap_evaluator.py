"""WP boundary overlap evaluator.

Detects work package boundary overlaps where multiple WPs claim ownership
of the same component, responsibility, or deliverable. Advisory only.

Pure functions — no DB, no LLM, deterministic.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OverlapFinding:
    """A single WP boundary overlap finding."""

    rule_id: str
    wp_ids: list[str]
    overlap_type: str
    evidence: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "wp_ids": self.wp_ids,
            "overlap_type": self.overlap_type,
            "evidence": self.evidence,
            "message": self.message,
        }


@dataclass
class OverlapReport:
    """WP boundary overlap evaluation report."""

    wp_count: int
    findings: list[OverlapFinding] = field(default_factory=list)

    @property
    def summary(self) -> dict[str, int]:
        return {
            "wps_checked": self.wp_count,
            "total_findings": len(self.findings),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "wp_count": self.wp_count,
            "summary": self.summary,
            "findings": [f.to_dict() for f in self.findings],
        }


# ---------------------------------------------------------------------------
# Component name extraction
# ---------------------------------------------------------------------------

# Common suffixes that indicate a named component/module/service
_COMPONENT_SUFFIXES = re.compile(
    r'\b(\w+(?:\s+\w+)?)\s+'
    r'(?:engine|service|module|manager|validator|handler|client|logger|calculator|sizer|collector|executor|storage)\b',
    re.IGNORECASE,
)

# Normalize whitespace and case for comparison
def _normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', text.strip().lower())


def _extract_component_names(text: str) -> list[str]:
    """Extract named components from text (e.g., 'Decision Engine', 'Safety Validator').

    Returns both the full match and the 2-word core (word + suffix) to catch
    partial overlaps like 'Indicator Engine' across different phrasings.
    """
    suffixes = r'(?:engine|service|module|manager|validator|handler|client|logger|calculator|sizer|collector|executor|storage)'
    full_matches = re.findall(
        r'\b(\w+(?:\s+\w+)?\s+' + suffixes + r')\b',
        text,
        re.IGNORECASE,
    )
    # Also extract just the 2-word form: <word> <suffix>
    short_matches = re.findall(
        r'\b(\w+\s+' + suffixes + r')\b',
        text,
        re.IGNORECASE,
    )
    all_matches = set(_normalize(m) for m in full_matches)
    all_matches.update(_normalize(m) for m in short_matches)
    return sorted(all_matches)


def _extract_text_from_wp(wp_content: dict[str, Any]) -> str:
    """Extract all searchable text from a WP content dict."""
    parts: list[str] = []
    for key in ("title", "objective", "rationale", "scope"):
        val = wp_content.get(key)
        if isinstance(val, str):
            parts.append(val)
        elif isinstance(val, list):
            parts.extend(str(item) for item in val)

    # Also include scope_in items
    scope_in = wp_content.get("scope_in")
    if isinstance(scope_in, list):
        parts.extend(str(item) for item in scope_in)

    return " ".join(parts)


def _extract_text_from_ws(ws_content: dict[str, Any]) -> str:
    """Extract searchable text from a WS content dict."""
    parts: list[str] = []
    for key in ("title", "objective"):
        val = ws_content.get(key)
        if isinstance(val, str):
            parts.append(val)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Overlap checks
# ---------------------------------------------------------------------------

def _check_component_name_overlap(
    wp_texts: dict[str, str],
) -> list[OverlapFinding]:
    """Check if multiple WPs claim the same named component."""
    # component_name -> list of wp_ids that reference it
    component_owners: dict[str, list[str]] = defaultdict(list)

    for wp_id, text in wp_texts.items():
        components = _extract_component_names(text)
        seen = set()
        for comp in components:
            if comp not in seen:
                component_owners[comp].append(wp_id)
                seen.add(comp)

    findings: list[OverlapFinding] = []
    for comp_name, wp_ids in sorted(component_owners.items()):
        if len(wp_ids) > 1:
            findings.append(OverlapFinding(
                rule_id="WP-OVERLAP-001",
                wp_ids=sorted(wp_ids),
                overlap_type="component_name",
                evidence=f"Component '{comp_name}' claimed by: {', '.join(sorted(wp_ids))}",
                message=(
                    f"Component '{comp_name}' appears in {len(wp_ids)} WPs: "
                    f"{', '.join(sorted(wp_ids))}. Consider clarifying ownership."
                ),
            ))

    return findings


def _check_ws_title_similarity(
    wp_ws_map: dict[str, list[str]],
) -> list[OverlapFinding]:
    """Check if WS titles under different WPs are suspiciously similar.

    Detects when the same normalized title phrase appears in WSs
    under different WPs.
    """
    # normalized title fragment -> list of (wp_id, ws_title)
    title_index: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for wp_id, ws_titles in wp_ws_map.items():
        for title in ws_titles:
            normalized = _normalize(title)
            # Extract key phrases (3+ word subsequences)
            words = normalized.split()
            if len(words) >= 3:
                # Use the full normalized title as the key
                title_index[normalized].append((wp_id, title))

    findings: list[OverlapFinding] = []
    for norm_title, entries in sorted(title_index.items()):
        wp_ids = list({wp_id for wp_id, _ in entries})
        if len(wp_ids) > 1:
            titles = [title for _, title in entries]
            findings.append(OverlapFinding(
                rule_id="WP-OVERLAP-002",
                wp_ids=sorted(wp_ids),
                overlap_type="ws_title_duplicate",
                evidence=f"Similar WS titles across WPs: {titles}",
                message=(
                    f"WS title '{entries[0][1]}' appears under {len(wp_ids)} WPs: "
                    f"{', '.join(sorted(wp_ids))}. This may indicate ownership overlap."
                ),
            ))

    return findings


def _check_scope_keyword_overlap(
    wp_scopes: dict[str, list[str]],
) -> list[OverlapFinding]:
    """Check if scope_in items across WPs share high-signal responsibility phrases.

    Looks for repeated 3+ word phrases in scope_in items across different WPs.
    """
    # Extract 3+ word phrases from scope items
    phrase_index: dict[str, list[str]] = defaultdict(list)

    for wp_id, scope_items in wp_scopes.items():
        seen_phrases: set[str] = set()
        for item in scope_items:
            normalized = _normalize(item)
            words = normalized.split()
            # Extract all 3-word sliding windows as key phrases
            for i in range(len(words) - 2):
                phrase = " ".join(words[i:i + 3])
                # Filter out generic/stop phrases
                if _is_generic_phrase(phrase):
                    continue
                if phrase not in seen_phrases:
                    phrase_index[phrase].append(wp_id)
                    seen_phrases.add(phrase)

    findings: list[OverlapFinding] = []
    # Only report phrases that appear in 2+ WPs and are specific enough
    reported_pairs: set[tuple[str, ...]] = set()
    for phrase, wp_ids in sorted(phrase_index.items()):
        unique_wps = sorted(set(wp_ids))
        if len(unique_wps) < 2:
            continue
        pair_key = tuple(unique_wps)
        if pair_key in reported_pairs:
            continue
        reported_pairs.add(pair_key)
        findings.append(OverlapFinding(
            rule_id="WP-OVERLAP-003",
            wp_ids=unique_wps,
            overlap_type="scope_phrase_overlap",
            evidence=f"Shared scope phrase '{phrase}' in: {', '.join(unique_wps)}",
            message=(
                f"Scope phrase '{phrase}' appears in {len(unique_wps)} WPs: "
                f"{', '.join(unique_wps)}. Review for responsibility overlap."
            ),
        ))

    return findings


_GENERIC_WORDS = frozenset([
    "the", "and", "for", "with", "all", "from", "that", "this",
    "are", "was", "will", "can", "has", "have", "been", "not",
    "each", "any", "its", "via", "per", "into", "also",
])


def _is_generic_phrase(phrase: str) -> bool:
    """Return True if a phrase is too generic to be meaningful overlap signal."""
    words = phrase.split()
    # If all words are generic, skip
    non_generic = [w for w in words if w not in _GENERIC_WORDS and len(w) > 2]
    return len(non_generic) < 2


# ---------------------------------------------------------------------------
# Main evaluator
# ---------------------------------------------------------------------------

def evaluate_wp_overlap(
    wp_artifacts: list[dict[str, Any]],
    ws_artifacts: list[dict[str, Any]] | None = None,
) -> OverlapReport:
    """Evaluate WP artifacts for boundary overlap.

    Args:
        wp_artifacts: List of WP document dicts. Each must have 'content' with
                      wp_id, title, scope/scope_in, objective, etc.
        ws_artifacts: Optional list of WS document dicts for WS-title overlap check.
                      Each must have 'content' with parent_wp_id and title.

    Returns:
        OverlapReport with findings. Empty findings = clean boundaries.
    """
    if len(wp_artifacts) < 2:
        return OverlapReport(wp_count=len(wp_artifacts))

    # Build WP text index (WP scope + title + objective + WS titles)
    wp_texts: dict[str, str] = {}
    wp_scopes: dict[str, list[str]] = {}
    wp_ws_map: dict[str, list[str]] = defaultdict(list)

    for wp in wp_artifacts:
        content = wp.get("content") or {}
        wp_id = content.get("wp_id") or wp.get("display_id", "unknown")
        wp_texts[wp_id] = _extract_text_from_wp(content)

        # Collect scope_in items
        scope_in = content.get("scope_in")
        if isinstance(scope_in, list):
            wp_scopes[wp_id] = [str(item) for item in scope_in]
        elif isinstance(content.get("scope"), list):
            wp_scopes[wp_id] = [str(item) for item in content["scope"]]
        else:
            wp_scopes[wp_id] = []

        # Include WS titles from ws_index if present
        ws_index = content.get("ws_index") or []
        for ws_entry in ws_index:
            title = ws_entry.get("title", "")
            if title:
                wp_ws_map[wp_id].append(title)
                wp_texts[wp_id] += " " + title

    # Also include WS titles from ws_artifacts if provided
    if ws_artifacts:
        for ws in ws_artifacts:
            ws_content = ws.get("content") or {}
            parent = ws_content.get("parent_wp_id")
            title = ws_content.get("title", "")
            if parent and title:
                wp_ws_map[parent].append(title)
                if parent in wp_texts:
                    wp_texts[parent] += " " + title

    findings: list[OverlapFinding] = []

    # Check 1: Component name overlap
    findings.extend(_check_component_name_overlap(wp_texts))

    # Check 2: WS title similarity across WPs
    findings.extend(_check_ws_title_similarity(wp_ws_map))

    # Check 3: Scope phrase overlap
    findings.extend(_check_scope_keyword_overlap(wp_scopes))

    return OverlapReport(
        wp_count=len(wp_artifacts),
        findings=findings,
    )
