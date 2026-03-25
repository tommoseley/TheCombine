"""Ontology leakage evaluator per ADR-059.

Detects cross-layer vocabulary leakage in project artifacts by comparing
artifact content against a declared project ontology.

Pure functions — no DB, no LLM, deterministic string matching.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OntologyFinding:
    """A single ontology leakage finding."""

    rule_id: str
    artifact_id: str
    field_path: str
    offending_term: str
    expected_layer: str
    actual_layer: str
    context: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "artifact_id": self.artifact_id,
            "field_path": self.field_path,
            "offending_term": self.offending_term,
            "expected_layer": self.expected_layer,
            "actual_layer": self.actual_layer,
            "context": self.context,
            "message": self.message,
        }


@dataclass
class OntologyReport:
    """Evaluation report for ontology consistency."""

    project_id: str
    ontology_version: str
    artifact_count: int
    findings: list[OntologyFinding] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None

    @property
    def summary(self) -> dict[str, int]:
        return {
            "total_findings": len(self.findings),
            "artifacts_checked": self.artifact_count,
        }

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "project_id": self.project_id,
            "ontology_version": self.ontology_version,
            "artifact_count": self.artifact_count,
            "skipped": self.skipped,
            "summary": self.summary,
            "findings": [f.to_dict() for f in self.findings],
        }
        if self.skip_reason:
            result["skip_reason"] = self.skip_reason
        return result


def load_ontology(ontology_config: dict[str, Any]) -> dict[str, Any] | None:
    """Extract and validate ontology from a parsed YAML config.

    Args:
        ontology_config: Parsed YAML dict (top-level must contain 'ontology' key).

    Returns:
        The ontology dict, or None if invalid/missing.
    """
    return ontology_config.get("ontology")


def _build_vocab_index(
    ontology: dict[str, Any],
) -> dict[str, str]:
    """Build a term → layer_name index from the ontology layers.

    Returns:
        Dict mapping each vocabulary term (case-preserved) to its owning layer name.
    """
    index: dict[str, str] = {}
    layers = ontology.get("layers") or {}
    for layer_name, layer_def in layers.items():
        for term in layer_def.get("vocabulary", []):
            index[term] = layer_name
    return index


def _determine_artifact_layer(
    doc_type: str,
    artifact_layers: dict[str, list[str]],
) -> str | None:
    """Determine which semantic layer an artifact belongs to.

    Args:
        doc_type: The document type id (e.g., 'work_package', 'work_statement').
        artifact_layers: The artifact_layers mapping from ontology config.

    Returns:
        Layer name, 'mixed' if explicitly mixed, or None if not mapped.
    """
    for layer_name, doc_types in artifact_layers.items():
        if doc_type in doc_types:
            return layer_name
    return None


# Fields to scan for vocabulary in artifact content
_SCANNABLE_FIELDS = [
    "objective",
    "scope_in",
    "scope_out",
    "procedure",
    "verification_criteria",
    "prohibited_actions",
    "title",
    "rationale",
    "scope",
]


def _extract_text(value: Any) -> str:
    """Flatten a value to searchable text."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_extract_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_extract_text(v) for v in value.values())
    return str(value) if value is not None else ""


def _scan_content_for_terms(
    content: dict[str, Any],
    terms: list[str],
) -> list[tuple[str, str, str]]:
    """Scan artifact content for vocabulary terms.

    Returns:
        List of (field_path, term_found, context_snippet) tuples.
    """
    hits: list[tuple[str, str, str]] = []
    for field_name in _SCANNABLE_FIELDS:
        value = content.get(field_name)
        if value is None:
            continue
        text = _extract_text(value)
        for term in terms:
            # Word-boundary match, case-insensitive for execution terms,
            # exact case for decision terms (which tend to be uppercase)
            pattern = r'\b' + re.escape(term) + r'\b'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Extract context snippet around the match
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                snippet = text[start:end].strip()
                hits.append((field_name, term, snippet))
    return hits


def evaluate_ontology(
    ontology_config: dict[str, Any],
    artifacts: list[dict[str, Any]],
) -> OntologyReport:
    """Evaluate artifacts against a project ontology for cross-layer leakage.

    Args:
        ontology_config: Parsed ontology YAML (must contain 'ontology' key).
        artifacts: List of dicts, each with at least 'doc_type_id' and 'content'.

    Returns:
        OntologyReport with findings. Empty findings = clean.
    """
    ontology = load_ontology(ontology_config)
    if ontology is None:
        return OntologyReport(
            project_id="unknown",
            ontology_version="unknown",
            artifact_count=0,
            skipped=True,
            skip_reason="No ontology declared — evaluator skipped",
        )

    project_id = ontology.get("project_id", "unknown")
    version = ontology.get("version", "unknown")
    vocab_index = _build_vocab_index(ontology)
    artifact_layers = ontology.get("artifact_layers") or {}

    findings: list[OntologyFinding] = []

    for artifact in artifacts:
        doc_type = artifact.get("doc_type_id", "unknown")
        content = artifact.get("content") or {}
        artifact_id = (
            content.get("ws_id")
            or content.get("wp_id")
            or content.get("display_id")
            or artifact.get("id", "unknown")
        )

        # Determine which layer this artifact belongs to
        artifact_layer = _determine_artifact_layer(doc_type, artifact_layers)

        # Mixed or unmapped artifacts: skip (no leakage to detect)
        if artifact_layer is None or artifact_layer == "mixed":
            continue

        # Find terms from OTHER layers that appear in this artifact
        foreign_terms: list[str] = []
        foreign_layer_map: dict[str, str] = {}
        for term, owning_layer in vocab_index.items():
            if owning_layer != artifact_layer:
                foreign_terms.append(term)
                foreign_layer_map[term] = owning_layer

        if not foreign_terms:
            continue

        hits = _scan_content_for_terms(content, foreign_terms)
        for field_path, term, snippet in hits:
            findings.append(OntologyFinding(
                rule_id="ONT-LEAK-001",
                artifact_id=artifact_id,
                field_path=field_path,
                offending_term=term,
                expected_layer=artifact_layer,
                actual_layer=foreign_layer_map[term],
                context=snippet,
                message=(
                    f"Term '{term}' from {foreign_layer_map[term]} layer "
                    f"found in {artifact_layer}-layer artifact {artifact_id} "
                    f"(field: {field_path})"
                ),
            ))

    return OntologyReport(
        project_id=project_id,
        ontology_version=version,
        artifact_count=len(artifacts),
        findings=findings,
    )
