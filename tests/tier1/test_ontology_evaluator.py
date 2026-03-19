"""Tier-1 tests for ontology leakage evaluator (ADR-059).

Pure unit tests — no DB, no LLM.
Tests vocabulary cross-layer detection, skip behavior, and finding structure.
"""

from app.domain.services.ontology_evaluator import (
    OntologyFinding,
    evaluate_ontology,
    load_ontology,
    _build_vocab_index,
    _determine_artifact_layer,
    _extract_text,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _apam_ontology():
    """Minimal APAM ontology config for testing."""
    return {
        "ontology": {
            "project_id": "apam",
            "version": "1.0",
            "layers": {
                "decision": {
                    "description": "Portfolio intent",
                    "vocabulary": ["ADD_20", "REMOVE_ALL", "HOLD"],
                },
                "execution": {
                    "description": "Order mechanics",
                    "vocabulary": ["buy", "sell", "market"],
                },
            },
            "translations": [
                {"from": "decision", "to": "execution"},
            ],
            "artifact_layers": {
                "decision": ["work_package", "work_statement"],
                "execution": ["order_execution"],
                "mixed": ["technical_architecture"],
            },
        }
    }


def _decision_ws(ws_id="WS-001", objective="Implement ADD_20 logic", procedure=None):
    """A work_statement artifact in the decision layer."""
    return {
        "doc_type_id": "work_statement",
        "content": {
            "ws_id": ws_id,
            "title": "Decision WS",
            "objective": objective,
            "procedure": procedure or ["Create decision engine", "Test logic"],
        },
    }


def _execution_ws(ws_id="WS-013", objective="Submit orders", procedure=None):
    """An order_execution artifact in the execution layer."""
    return {
        "doc_type_id": "order_execution",
        "content": {
            "ws_id": ws_id,
            "title": "Execution WS",
            "objective": objective,
            "procedure": procedure or ["Submit buy order", "Track status"],
        },
    }


def _ta_artifact():
    """A technical_architecture artifact (mixed layer)."""
    return {
        "doc_type_id": "technical_architecture",
        "content": {
            "display_id": "TA-001",
            "title": "Technical Architecture",
            "objective": "Define ADD_20 to buy translation",
        },
    }


# ---------------------------------------------------------------------------
# load_ontology
# ---------------------------------------------------------------------------

class TestLoadOntology:
    def test_valid_config(self):
        ont = load_ontology(_apam_ontology())
        assert ont is not None
        assert ont["project_id"] == "apam"

    def test_missing_ontology_key(self):
        assert load_ontology({"other": "stuff"}) is None

    def test_empty_config(self):
        assert load_ontology({}) is None


# ---------------------------------------------------------------------------
# _build_vocab_index
# ---------------------------------------------------------------------------

class TestBuildVocabIndex:
    def test_builds_index(self):
        ont = _apam_ontology()["ontology"]
        index = _build_vocab_index(ont)
        assert index["ADD_20"] == "decision"
        assert index["buy"] == "execution"
        assert index["HOLD"] == "decision"

    def test_empty_layers(self):
        index = _build_vocab_index({"layers": {}})
        assert index == {}


# ---------------------------------------------------------------------------
# _determine_artifact_layer
# ---------------------------------------------------------------------------

class TestDetermineArtifactLayer:
    def test_decision_layer(self):
        layers = {"decision": ["work_statement"], "execution": ["order_execution"]}
        assert _determine_artifact_layer("work_statement", layers) == "decision"

    def test_execution_layer(self):
        layers = {"decision": ["work_statement"], "execution": ["order_execution"]}
        assert _determine_artifact_layer("order_execution", layers) == "execution"

    def test_mixed_layer(self):
        layers = {"mixed": ["technical_architecture"]}
        assert _determine_artifact_layer("technical_architecture", layers) == "mixed"

    def test_unmapped(self):
        layers = {"decision": ["work_statement"]}
        assert _determine_artifact_layer("concierge_intake", layers) is None


# ---------------------------------------------------------------------------
# _extract_text
# ---------------------------------------------------------------------------

class TestExtractText:
    def test_string(self):
        assert _extract_text("hello") == "hello"

    def test_list(self):
        assert "buy" in _extract_text(["buy", "sell"])

    def test_dict(self):
        assert "foo" in _extract_text({"a": "foo", "b": "bar"})

    def test_none(self):
        assert _extract_text(None) == ""

    def test_nested(self):
        assert "deep" in _extract_text({"a": ["deep", "value"]})


# ---------------------------------------------------------------------------
# evaluate_ontology — no ontology
# ---------------------------------------------------------------------------

class TestNoOntology:
    def test_missing_ontology_skips(self):
        report = evaluate_ontology({}, [])
        assert report.skipped is True
        assert "skipped" in report.skip_reason.lower()
        assert report.findings == []

    def test_skip_reason_in_dict(self):
        report = evaluate_ontology({}, [])
        d = report.to_dict()
        assert d["skipped"] is True
        assert "skip_reason" in d


# ---------------------------------------------------------------------------
# evaluate_ontology — clean artifacts
# ---------------------------------------------------------------------------

class TestCleanArtifacts:
    def test_decision_ws_with_decision_terms_only(self):
        """Decision WS using only decision vocabulary — no findings."""
        report = evaluate_ontology(
            _apam_ontology(),
            [_decision_ws(objective="Implement ADD_20 and HOLD logic")],
        )
        assert len(report.findings) == 0

    def test_execution_ws_with_execution_terms_only(self):
        """Execution WS using only execution vocabulary — no findings."""
        report = evaluate_ontology(
            _apam_ontology(),
            [_execution_ws(objective="Submit market buy order")],
        )
        assert len(report.findings) == 0

    def test_mixed_artifact_skipped(self):
        """TA (mixed) can use terms from any layer — no findings."""
        report = evaluate_ontology(
            _apam_ontology(),
            [_ta_artifact()],
        )
        assert len(report.findings) == 0

    def test_unmapped_artifact_skipped(self):
        """Unmapped doc type is skipped — no findings."""
        artifact = {
            "doc_type_id": "concierge_intake",
            "content": {"display_id": "CI-001", "objective": "buy stuff with ADD_20"},
        }
        report = evaluate_ontology(_apam_ontology(), [artifact])
        assert len(report.findings) == 0


# ---------------------------------------------------------------------------
# evaluate_ontology — leakage detection
# ---------------------------------------------------------------------------

class TestLeakageDetection:
    def test_execution_term_in_decision_ws(self):
        """Decision WS using 'buy' → leakage finding."""
        report = evaluate_ontology(
            _apam_ontology(),
            [_decision_ws(objective="buy shares when ADD_20 triggers")],
        )
        assert len(report.findings) == 1
        f = report.findings[0]
        assert f.rule_id == "ONT-LEAK-001"
        assert f.offending_term == "buy"
        assert f.expected_layer == "decision"
        assert f.actual_layer == "execution"

    def test_decision_term_in_execution_ws(self):
        """Execution WS using 'ADD_20' → leakage finding."""
        report = evaluate_ontology(
            _apam_ontology(),
            [_execution_ws(objective="Execute ADD_20 as market order")],
        )
        assert len(report.findings) == 1
        f = report.findings[0]
        assert f.offending_term == "ADD_20"
        assert f.expected_layer == "execution"
        assert f.actual_layer == "decision"

    def test_multiple_leaks_in_one_artifact(self):
        """Multiple foreign terms in one artifact → multiple findings."""
        report = evaluate_ontology(
            _apam_ontology(),
            [_decision_ws(
                objective="buy and sell based on ADD_20",
                procedure=["Submit market order"],
            )],
        )
        terms = {f.offending_term for f in report.findings}
        assert "buy" in terms
        assert "sell" in terms
        assert "market" in terms

    def test_leakage_in_procedure_field(self):
        """Foreign term in procedure list detected."""
        report = evaluate_ontology(
            _apam_ontology(),
            [_decision_ws(procedure=["Create buy order logic"])],
        )
        proc_findings = [f for f in report.findings if f.field_path == "procedure"]
        assert len(proc_findings) >= 1
        assert proc_findings[0].offending_term == "buy"

    def test_case_insensitive_execution_terms(self):
        """Execution terms detected case-insensitively."""
        report = evaluate_ontology(
            _apam_ontology(),
            [_decision_ws(objective="BUY shares when triggered")],
        )
        assert len(report.findings) == 1
        assert report.findings[0].offending_term == "buy"

    def test_multiple_artifacts(self):
        """Findings across multiple artifacts."""
        report = evaluate_ontology(
            _apam_ontology(),
            [
                _decision_ws("WS-001", objective="Clean decision logic with HOLD"),
                _decision_ws("WS-002", objective="buy shares directly"),
                _execution_ws("WS-013", objective="Execute ADD_20 order"),
            ],
        )
        assert report.artifact_count == 3
        artifact_ids = {f.artifact_id for f in report.findings}
        assert "WS-002" in artifact_ids
        assert "WS-013" in artifact_ids
        assert "WS-001" not in artifact_ids


# ---------------------------------------------------------------------------
# Finding and report structure
# ---------------------------------------------------------------------------

class TestFindingShape:
    def test_finding_has_all_fields(self):
        report = evaluate_ontology(
            _apam_ontology(),
            [_decision_ws(objective="buy shares")],
        )
        f = report.findings[0]
        assert isinstance(f, OntologyFinding)
        d = f.to_dict()
        assert "rule_id" in d
        assert "artifact_id" in d
        assert "field_path" in d
        assert "offending_term" in d
        assert "expected_layer" in d
        assert "actual_layer" in d
        assert "context" in d
        assert "message" in d

    def test_report_summary(self):
        report = evaluate_ontology(
            _apam_ontology(),
            [_decision_ws(objective="buy and sell")],
        )
        s = report.summary
        assert s["total_findings"] >= 1
        assert s["artifacts_checked"] == 1

    def test_report_to_dict(self):
        report = evaluate_ontology(
            _apam_ontology(),
            [_decision_ws(objective="clean HOLD logic")],
        )
        d = report.to_dict()
        assert d["project_id"] == "apam"
        assert d["ontology_version"] == "1.0"
        assert d["skipped"] is False
        assert isinstance(d["findings"], list)
        assert isinstance(d["summary"], dict)
