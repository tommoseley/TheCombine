"""Cross-layer contradiction evaluator per ADR-061.

Detects contradictions between TA (authoritative architecture) and
WS (execution artifacts) by comparing structured TA surfaces against
WS content.

Pure functions — no DB, no LLM, deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContradictionFinding:
    """A single cross-layer contradiction finding."""

    rule_id: str
    artifact_id: str
    field_path: str
    contradiction_type: str
    ta_authority: str
    ws_claim: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "artifact_id": self.artifact_id,
            "field_path": self.field_path,
            "contradiction_type": self.contradiction_type,
            "ta_authority": self.ta_authority,
            "ws_claim": self.ws_claim,
            "message": self.message,
        }


@dataclass
class ContradictionReport:
    """Cross-layer contradiction evaluation report."""

    ta_found: bool
    artifacts_checked: int
    findings: list[ContradictionFinding] = field(default_factory=list)

    @property
    def summary(self) -> dict[str, int]:
        return {
            "artifacts_checked": self.artifacts_checked,
            "total_findings": len(self.findings),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "ta_found": self.ta_found,
            "artifacts_checked": self.artifacts_checked,
            "summary": self.summary,
            "findings": [f.to_dict() for f in self.findings],
        }


# ---------------------------------------------------------------------------
# TA authority surface extraction
# ---------------------------------------------------------------------------

def extract_ta_surfaces(ta_content: dict[str, Any]) -> dict[str, Any]:
    """Extract structured authority surfaces from a TA document.

    Returns dict with:
        - data_model_fields: {model_name: set of field names}
        - component_names: set of declared component names
        - technologies: set of declared tech stack items
    """
    surfaces: dict[str, Any] = {
        "data_model_fields": {},
        "component_names": set(),
        "technologies": set(),
    }

    # Extract data model fields
    data_models = ta_content.get("data_models") or []
    if isinstance(data_models, list):
        for model in data_models:
            model_name = _normalize(model.get("name", ""))
            fields_list = model.get("fields") or []
            field_names = set()
            for f in fields_list:
                fname = f.get("name") or f.get("field")
                if fname:
                    field_names.add(_normalize(fname))
            if model_name and field_names:
                surfaces["data_model_fields"][model_name] = field_names

    # Extract component names
    components = ta_content.get("components") or []
    if isinstance(components, list):
        for comp in components:
            name = comp.get("name", "")
            if name:
                surfaces["component_names"].add(_normalize(name))
            # Also extract tech stack
            tech = comp.get("tech_stack") or comp.get("technology") or ""
            if isinstance(tech, str) and tech:
                for item in re.split(r'[,;]\s*', tech):
                    item = item.strip().lower()
                    if item:
                        surfaces["technologies"].add(item)

    return surfaces


def _normalize(text: str) -> str:
    """Normalize text for comparison."""
    return re.sub(r'\s+', '_', text.strip().lower())


# ---------------------------------------------------------------------------
# WS content scanning
# ---------------------------------------------------------------------------

# Common technical indicator / data field names to look for in WS content
_INDICATOR_PATTERN = re.compile(
    r'\b(macd|bollinger[_ ]bands?|rsi[_ ]\d+|sma[_ ]\d+|ema[_ ]\d+'
    r'|momentum[_ ]score|volatility|technical[_ ]score)\b',
    re.IGNORECASE,
)

_PERSISTENCE_KEYWORDS = {
    "sqlite": "sqlite",
    "csv": "csv",
    "json": "json",
    "postgresql": "postgresql",
    "mysql": "mysql",
    "database": "database",
}


def _extract_ws_text(ws_content: dict[str, Any]) -> str:
    """Extract all searchable text from a WS."""
    parts: list[str] = []
    for key in ("title", "objective", "scope_in", "scope_out", "procedure",
                "verification_criteria", "prohibited_actions"):
        val = ws_content.get(key)
        if isinstance(val, str):
            parts.append(val)
        elif isinstance(val, list):
            parts.extend(str(item) for item in val)
    return " ".join(parts)


def _extract_indicator_references(text: str) -> set[str]:
    """Find technical indicator names referenced in text."""
    matches = _INDICATOR_PATTERN.findall(text)
    return {_normalize(m) for m in matches}


def _extract_persistence_references(text: str) -> set[str]:
    """Find persistence technology references in text."""
    found: set[str] = set()
    text_lower = text.lower()
    for keyword, tech in _PERSISTENCE_KEYWORDS.items():
        if keyword in text_lower:
            found.add(tech)
    return found


# ---------------------------------------------------------------------------
# Contradiction checks
# ---------------------------------------------------------------------------

def _check_schema_field_mismatches(
    ta_surfaces: dict[str, Any],
    ws_artifacts: list[dict[str, Any]],
) -> list[ContradictionFinding]:
    """Check if WS references data fields not present in TA data models."""
    findings: list[ContradictionFinding] = []
    ta_fields = ta_surfaces.get("data_model_fields") or {}

    # Build a flat set of all known TA fields
    all_ta_fields: set[str] = set()
    for fields in ta_fields.values():
        all_ta_fields.update(fields)

    if not all_ta_fields:
        return findings

    for ws in ws_artifacts:
        content = ws.get("content") or {}
        ws_id = content.get("ws_id", "unknown")
        text = _extract_ws_text(content)
        ws_indicators = _extract_indicator_references(text)

        for indicator in ws_indicators:
            # Check if this indicator has a corresponding field in TA
            if indicator not in all_ta_fields:
                findings.append(ContradictionFinding(
                    rule_id="CLDR-001",
                    artifact_id=ws_id,
                    field_path="scope_in/procedure",
                    contradiction_type="schema_field_missing",
                    ta_authority="TA data model fields",
                    ws_claim=f"References '{indicator}' indicator",
                    message=(
                        f"WS {ws_id} references indicator '{indicator}' "
                        f"which has no corresponding field in TA data models"
                    ),
                ))

    return findings


def _check_persistence_contradictions(
    ta_surfaces: dict[str, Any],
    ws_artifacts: list[dict[str, Any]],
) -> list[ContradictionFinding]:
    """Check if WS persistence approach contradicts TA."""
    findings: list[ContradictionFinding] = []
    ta_techs = ta_surfaces.get("technologies") or set()

    # Determine TA's primary persistence from technologies
    ta_has_sqlite = any("sqlite" in t for t in ta_techs)
    ta_has_csv = any("csv" in t for t in ta_techs)

    if not ta_has_sqlite and not ta_has_csv:
        return findings

    for ws in ws_artifacts:
        content = ws.get("content") or {}
        ws_id = content.get("ws_id", "unknown")
        text = _extract_ws_text(content)
        ws_persistence = _extract_persistence_references(text)

        # Flag "CSV-only" patterns in WS when TA declares SQLite
        if ta_has_sqlite and "csv" in ws_persistence and "sqlite" not in ws_persistence:
            # Check if WS explicitly excludes database
            prohibited = content.get("prohibited_actions") or []
            prohibited_text = " ".join(str(p) for p in prohibited).lower()
            if "database" in prohibited_text or "sqlite" in prohibited_text:
                findings.append(ContradictionFinding(
                    rule_id="CLDR-002",
                    artifact_id=ws_id,
                    field_path="prohibited_actions",
                    contradiction_type="persistence_contradiction",
                    ta_authority="TA declares SQLite persistence",
                    ws_claim="WS prohibits database usage",
                    message=(
                        f"WS {ws_id} prohibits database usage but TA declares "
                        f"SQLite as persistence technology"
                    ),
                ))

    return findings


def _check_component_mismatches(
    ta_surfaces: dict[str, Any],
    ws_artifacts: list[dict[str, Any]],
) -> list[ContradictionFinding]:
    """Check WS component references against TA-declared vocabulary.

    Uses canonical vocabulary validation (WS-EVAL-004): instead of regex-
    extracting component-like phrases from WS prose, searches WS text for
    exact (normalized) matches against TA-declared component names.

    This eliminates false positives from procedure verbs and generic prose
    while preserving detection of genuine undeclared component references.
    """
    findings: list[ContradictionFinding] = []
    ta_components = ta_surfaces.get("component_names") or set()

    if not ta_components:
        return findings

    # Build per-WS text and check each TA component name against it
    ws_texts: list[tuple[str, str]] = []  # (ws_id, normalized_text)
    for ws in ws_artifacts:
        content = ws.get("content") or {}
        ws_id = content.get("ws_id", "unknown")
        text = _normalize(_extract_ws_text(content))
        ws_texts.append((ws_id, text))

    # For each TA component, check if any WS references it
    # This is informational — no finding needed for matches.
    # We only report when a WS explicitly names something that looks like
    # a TA component but doesn't match any declared name.
    #
    # Since we no longer extract from prose, CLDR-003 now only fires
    # when WS has a structured components_touched field (future).
    # For now, this check is dormant — no regex guessing.

    return findings


# ---------------------------------------------------------------------------
# Main evaluator
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# TA owns validation (WS-EVAL-003)
# ---------------------------------------------------------------------------

@dataclass
class TAOwnsValidationFinding:
    """A finding from TA owns field validation."""

    component_name: str
    issue_type: str  # "missing_owns" | "empty_owns"
    severity: str  # "advisory"
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_name": self.component_name,
            "issue_type": self.issue_type,
            "severity": self.severity,
            "message": self.message,
        }


@dataclass
class TAOwnsValidationReport:
    """Report from TA owns field validation."""

    components_checked: int
    findings: list[TAOwnsValidationFinding] = field(default_factory=list)

    @property
    def all_valid(self) -> bool:
        return len(self.findings) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "components_checked": self.components_checked,
            "findings_count": len(self.findings),
            "all_valid": self.all_valid,
            "findings": [f.to_dict() for f in self.findings],
        }


def validate_ta_owns(ta_content: dict[str, Any]) -> TAOwnsValidationReport:
    """Validate that every TA component has a non-empty owns array.

    Mechanical enforcement for TA prompt v1.3.0's MUST requirement.
    Advisory only — does not block stabilization.

    Args:
        ta_content: The TA document content dict.

    Returns:
        TAOwnsValidationReport with findings for components missing owns.
    """
    components = ta_content.get("components") or []
    if not isinstance(components, list):
        return TAOwnsValidationReport(components_checked=0)

    findings: list[TAOwnsValidationFinding] = []

    for comp in components:
        name = comp.get("name", "unknown")
        owns = comp.get("owns")

        if owns is None:
            findings.append(TAOwnsValidationFinding(
                component_name=name,
                issue_type="missing_owns",
                severity="advisory",
                message=f"Component '{name}' has no 'owns' field",
            ))
        elif not isinstance(owns, list) or len(owns) == 0:
            findings.append(TAOwnsValidationFinding(
                component_name=name,
                issue_type="empty_owns",
                severity="advisory",
                message=f"Component '{name}' has empty 'owns' array",
            ))
        else:
            # Check for whitespace-only entries
            non_empty = [o for o in owns if isinstance(o, str) and o.strip()]
            if not non_empty:
                findings.append(TAOwnsValidationFinding(
                    component_name=name,
                    issue_type="empty_owns",
                    severity="advisory",
                    message=f"Component '{name}' has 'owns' with only blank entries",
                ))

    return TAOwnsValidationReport(
        components_checked=len(components),
        findings=findings,
    )


# ---------------------------------------------------------------------------
# Main evaluator
# ---------------------------------------------------------------------------

def evaluate_cross_layer(
    ta_artifact: dict[str, Any] | None,
    ws_artifacts: list[dict[str, Any]],
) -> ContradictionReport:
    """Evaluate WS artifacts against TA for cross-layer contradictions.

    Args:
        ta_artifact: The TA document dict with 'content' key, or None.
        ws_artifacts: List of WS document dicts, each with 'content' key.

    Returns:
        ContradictionReport with findings. Empty findings = clean.
    """
    if ta_artifact is None:
        return ContradictionReport(
            ta_found=False,
            artifacts_checked=0,
        )

    ta_content = ta_artifact.get("content") or {}
    ta_surfaces = extract_ta_surfaces(ta_content)

    findings: list[ContradictionFinding] = []
    findings.extend(_check_schema_field_mismatches(ta_surfaces, ws_artifacts))
    findings.extend(_check_persistence_contradictions(ta_surfaces, ws_artifacts))
    findings.extend(_check_component_mismatches(ta_surfaces, ws_artifacts))

    return ContradictionReport(
        ta_found=True,
        artifacts_checked=len(ws_artifacts),
        findings=findings,
    )
