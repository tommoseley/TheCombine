"""Tier-1 tests for cross-layer contradiction evaluator (ADR-061).

Pure unit tests — no DB, no LLM.
Tests TA surface extraction, contradiction detection, report structure,
and TA owns validation (WS-EVAL-003).
"""

from app.domain.services.cross_layer_evaluator import (
    ContradictionFinding,
    evaluate_cross_layer,
    extract_ta_surfaces,
    validate_ta_owns,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _ta(data_models=None, components=None):
    """Build a minimal TA artifact."""
    content = {}
    if data_models is not None:
        content["data_models"] = data_models
    if components is not None:
        content["components"] = components
    return {"doc_type_id": "technical_architecture", "content": content}


def _ta_model(name, fields):
    """Build a TA data model dict."""
    return {
        "name": name,
        "fields": [{"name": f} for f in fields],
    }


def _ta_component(name, tech_stack=""):
    """Build a TA component dict."""
    return {"name": name, "tech_stack": tech_stack}


def _ws(ws_id, objective="", scope_in=None, procedure=None, prohibited_actions=None):
    """Build a minimal WS artifact."""
    content = {"ws_id": ws_id, "objective": objective}
    if scope_in:
        content["scope_in"] = scope_in
    if procedure:
        content["procedure"] = procedure
    if prohibited_actions:
        content["prohibited_actions"] = prohibited_actions
    return {"doc_type_id": "work_statement", "content": content}


# ---------------------------------------------------------------------------
# extract_ta_surfaces
# ---------------------------------------------------------------------------

class TestExtractTASurfaces:
    def test_extracts_data_model_fields(self):
        ta = _ta(data_models=[
            _ta_model("TechnicalIndicators", ["sma_20", "sma_50", "rsi_14"]),
        ])
        surfaces = extract_ta_surfaces(ta["content"])
        assert "technicalindicators" in surfaces["data_model_fields"]
        assert "sma_20" in surfaces["data_model_fields"]["technicalindicators"]

    def test_extracts_component_names(self):
        ta = _ta(components=[
            _ta_component("Daily Indicator Engine"),
            _ta_component("Order Execution Engine"),
        ])
        surfaces = extract_ta_surfaces(ta["content"])
        assert "daily_indicator_engine" in surfaces["component_names"]
        assert "order_execution_engine" in surfaces["component_names"]

    def test_extracts_technologies(self):
        ta = _ta(components=[
            _ta_component("Data Store", "SQLite 3.x"),
            _ta_component("Calculator", "Python 3.x with pandas, numpy"),
        ])
        surfaces = extract_ta_surfaces(ta["content"])
        assert "sqlite 3.x" in surfaces["technologies"]

    def test_empty_ta(self):
        surfaces = extract_ta_surfaces({})
        assert surfaces["data_model_fields"] == {}
        assert surfaces["component_names"] == set()
        assert surfaces["technologies"] == set()


# ---------------------------------------------------------------------------
# No TA
# ---------------------------------------------------------------------------

class TestNoTA:
    def test_no_ta_returns_empty_report(self):
        report = evaluate_cross_layer(None, [_ws("WS-001")])
        assert report.ta_found is False
        assert report.findings == []
        assert report.artifacts_checked == 0


# ---------------------------------------------------------------------------
# Schema field mismatches (CLDR-001)
# ---------------------------------------------------------------------------

class TestSchemaFieldMismatches:
    def test_ws_references_field_in_ta(self):
        """WS references sma_20 which IS in TA — no finding."""
        ta = _ta(data_models=[
            _ta_model("TechnicalIndicators", ["sma_20", "sma_50", "rsi_14"]),
        ])
        ws = _ws("WS-005", scope_in=["SMA 20 calculation", "RSI 14 computation"])
        report = evaluate_cross_layer(ta, [ws])
        schema_findings = [f for f in report.findings if f.rule_id == "CLDR-001"]
        assert len(schema_findings) == 0

    def test_ws_references_field_not_in_ta(self):
        """WS references MACD which is NOT in TA — finding."""
        ta = _ta(data_models=[
            _ta_model("TechnicalIndicators", ["sma_20", "sma_50", "rsi_14"]),
        ])
        ws = _ws("WS-005", scope_in=["MACD calculation", "Bollinger Bands"])
        report = evaluate_cross_layer(ta, [ws])
        schema_findings = [f for f in report.findings if f.rule_id == "CLDR-001"]
        assert len(schema_findings) >= 1
        terms = {f.ws_claim for f in schema_findings}
        assert any("macd" in t.lower() for t in terms)

    def test_multiple_missing_fields(self):
        """WS references both MACD and Bollinger — both flagged."""
        ta = _ta(data_models=[
            _ta_model("TechnicalIndicators", ["sma_20", "rsi_14"]),
        ])
        ws = _ws("WS-005", scope_in=[
            "MACD signal line calculation",
            "Bollinger Bands computation",
        ])
        report = evaluate_cross_layer(ta, [ws])
        schema_findings = [f for f in report.findings if f.rule_id == "CLDR-001"]
        assert len(schema_findings) >= 2

    def test_no_data_models_skips_check(self):
        """TA without data models — no schema findings."""
        ta = _ta(components=[_ta_component("Engine")])
        ws = _ws("WS-005", scope_in=["MACD calculation"])
        report = evaluate_cross_layer(ta, [ws])
        schema_findings = [f for f in report.findings if f.rule_id == "CLDR-001"]
        assert len(schema_findings) == 0


# ---------------------------------------------------------------------------
# Persistence contradictions (CLDR-002)
# ---------------------------------------------------------------------------

class TestPersistenceContradictions:
    def test_ws_csv_only_when_ta_has_sqlite_no_prohibition(self):
        """WS uses CSV but doesn't prohibit DB — no finding (could use both)."""
        ta = _ta(components=[_ta_component("Store", "SQLite 3.x")])
        ws = _ws("WS-017", objective="CSV logging for trades")
        report = evaluate_cross_layer(ta, [ws])
        persis_findings = [f for f in report.findings if f.rule_id == "CLDR-002"]
        assert len(persis_findings) == 0

    def test_ws_prohibits_database_when_ta_has_sqlite(self):
        """WS prohibits database when TA declares SQLite — finding."""
        ta = _ta(components=[_ta_component("Store", "SQLite 3.x")])
        ws = _ws("WS-017",
                 objective="CSV logging for trades",
                 prohibited_actions=["Do not log trades to database instead of CSV"])
        report = evaluate_cross_layer(ta, [ws])
        persis_findings = [f for f in report.findings if f.rule_id == "CLDR-002"]
        assert len(persis_findings) == 1
        assert "prohibits database" in persis_findings[0].message.lower()


# ---------------------------------------------------------------------------
# Component mismatches (CLDR-003) — vocabulary-based (WS-EVAL-004)
# ---------------------------------------------------------------------------

class TestComponentMismatches:
    def test_no_findings_without_regex_extraction(self):
        """CLDR-003 no longer extracts component names from prose.
        Without a components_touched field on WS, no findings are produced."""
        ta = _ta(components=[_ta_component("Daily Indicator Engine")])
        ws = _ws("WS-023", objective="Implement Email Notification Service")
        report = evaluate_cross_layer(ta, [ws])
        comp_findings = [f for f in report.findings if f.rule_id == "CLDR-003"]
        assert len(comp_findings) == 0

    def test_no_false_positives_from_prose(self):
        """Procedure verbs and generic prose never produce CLDR-003 findings."""
        ta = _ta(components=[_ta_component("Real Engine")])
        ws = _ws("WS-003", scope_in=[
            "Create scoring module structure",
            "Verify all packages by importing each module",
            "Ensure clean script termination importing sys module",
        ])
        report = evaluate_cross_layer(ta, [ws])
        comp_findings = [f for f in report.findings if f.rule_id == "CLDR-003"]
        assert len(comp_findings) == 0


# ---------------------------------------------------------------------------
# Report structure
# ---------------------------------------------------------------------------

class TestReportStructure:
    def test_report_summary(self):
        ta = _ta(data_models=[_ta_model("M", ["f1"])])
        report = evaluate_cross_layer(ta, [_ws("WS-001"), _ws("WS-002")])
        s = report.summary
        assert s["artifacts_checked"] == 2
        assert isinstance(s["total_findings"], int)

    def test_report_to_dict(self):
        ta = _ta(data_models=[_ta_model("M", ["f1"])])
        report = evaluate_cross_layer(ta, [_ws("WS-001")])
        d = report.to_dict()
        assert "ta_found" in d
        assert "artifacts_checked" in d
        assert "summary" in d
        assert "findings" in d

    def test_finding_shape(self):
        ta = _ta(data_models=[
            _ta_model("TechnicalIndicators", ["sma_20"]),
        ])
        ws = _ws("WS-005", scope_in=["MACD calculation"])
        report = evaluate_cross_layer(ta, [ws])
        assert len(report.findings) >= 1
        f = report.findings[0]
        assert isinstance(f, ContradictionFinding)
        d = f.to_dict()
        for key in ("rule_id", "artifact_id", "field_path",
                     "contradiction_type", "ta_authority", "ws_claim", "message"):
            assert key in d


# ---------------------------------------------------------------------------
# TA owns validation (WS-EVAL-003)
# ---------------------------------------------------------------------------

class TestTAOwnsValidation:
    """WS-EVAL-003: mechanical validation that TA components have non-empty owns."""

    def test_all_components_have_owns(self):
        """All components have valid owns — no findings."""
        content = {"components": [
            {"name": "API Gateway", "owns": ["src/api/"]},
            {"name": "Data Store", "owns": ["src/storage/", "src/models/"]},
        ]}
        report = validate_ta_owns(content)
        assert report.components_checked == 2
        assert report.all_valid
        assert len(report.findings) == 0

    def test_missing_owns_field(self):
        """Component without owns field — missing_owns finding."""
        content = {"components": [
            {"name": "API Gateway"},
        ]}
        report = validate_ta_owns(content)
        assert report.components_checked == 1
        assert not report.all_valid
        assert len(report.findings) == 1
        assert report.findings[0].issue_type == "missing_owns"
        assert report.findings[0].component_name == "API Gateway"
        assert report.findings[0].severity == "advisory"

    def test_empty_owns_array(self):
        """Component with empty owns array — empty_owns finding."""
        content = {"components": [
            {"name": "API Gateway", "owns": []},
        ]}
        report = validate_ta_owns(content)
        assert report.findings[0].issue_type == "empty_owns"

    def test_null_owns(self):
        """Component with owns: null — treated as missing."""
        content = {"components": [
            {"name": "API Gateway", "owns": None},
        ]}
        report = validate_ta_owns(content)
        assert report.findings[0].issue_type == "missing_owns"

    def test_whitespace_only_owns(self):
        """Component with owns containing only blank strings — empty_owns."""
        content = {"components": [
            {"name": "API Gateway", "owns": ["  ", ""]},
        ]}
        report = validate_ta_owns(content)
        assert report.findings[0].issue_type == "empty_owns"
        assert "blank" in report.findings[0].message

    def test_mixed_valid_and_invalid(self):
        """Some components valid, some missing — only invalid flagged."""
        content = {"components": [
            {"name": "API Gateway", "owns": ["src/api/"]},
            {"name": "Data Store"},
            {"name": "Cache Layer", "owns": []},
        ]}
        report = validate_ta_owns(content)
        assert report.components_checked == 3
        assert len(report.findings) == 2
        names = {f.component_name for f in report.findings}
        assert names == {"Data Store", "Cache Layer"}

    def test_empty_components_list(self):
        """No components — report is valid with 0 checked."""
        report = validate_ta_owns({"components": []})
        assert report.components_checked == 0
        assert report.all_valid

    def test_no_components_key(self):
        """TA content without components key — 0 checked."""
        report = validate_ta_owns({})
        assert report.components_checked == 0
        assert report.all_valid

    def test_report_to_dict(self):
        """Report serialization includes all fields."""
        content = {"components": [{"name": "X"}]}
        report = validate_ta_owns(content)
        d = report.to_dict()
        assert "components_checked" in d
        assert "findings_count" in d
        assert "all_valid" in d
        assert "findings" in d
        assert d["findings_count"] == 1


# ---------------------------------------------------------------------------
# APAM-like scenario
# ---------------------------------------------------------------------------

class TestTAOwnsInBinderContext:
    """WS-EVAL-005A: validate_ta_owns produces correct findings for binder rendering."""

    def test_real_ta_with_owns(self):
        """TA with components that all have owns — clean report."""
        content = {"components": [
            {"name": "Main Execution Handler", "owns": ["src/main.py"]},
            {"name": "Output Handler", "owns": ["src/output.py"]},
        ]}
        report = validate_ta_owns(content)
        assert report.all_valid
        assert report.components_checked == 2

    def test_real_ta_missing_owns(self):
        """TA with components missing owns — findings for binder."""
        content = {"components": [
            {"name": "Main Execution Handler"},
            {"name": "Output Handler"},
        ]}
        report = validate_ta_owns(content)
        assert not report.all_valid
        assert len(report.findings) == 2
        # Each finding has the fields needed for binder rendering
        for f in report.findings:
            d = f.to_dict()
            assert "component_name" in d
            assert "issue_type" in d
            assert "severity" in d
            assert d["severity"] == "advisory"

    def test_no_ta_in_binder(self):
        """No components key — 0 checked, all_valid (no findings section shown)."""
        report = validate_ta_owns({})
        assert report.all_valid
        assert report.components_checked == 0


class TestAPAMScenario:
    def test_apam_macd_bollinger_mismatch(self):
        """Reproduce the APAM-005 critique: WS-005 references MACD/Bollinger not in TA."""
        ta = _ta(
            data_models=[
                _ta_model("TechnicalIndicators", [
                    "sma_20", "sma_50", "rsi_14", "momentum_score", "volatility",
                ]),
            ],
            components=[
                _ta_component("Daily Indicator Engine", "Python 3.x with pandas"),
                _ta_component("SQLite Data Store", "SQLite 3.x"),
            ],
        )
        ws = _ws("WS-005", scope_in=[
            "MACD signal line calculation with standard parameters",
            "Bollinger Bands calculation with 20-day period",
            "RSI 14-day calculation",
            "SMA 20 and SMA 50 calculations",
        ])
        report = evaluate_cross_layer(ta, [ws])
        schema_findings = [f for f in report.findings if f.rule_id == "CLDR-001"]
        # Should find MACD and Bollinger but not RSI or SMA
        flagged_terms = {f.ws_claim.lower() for f in schema_findings}
        assert any("macd" in t for t in flagged_terms)
        assert any("bollinger" in t for t in flagged_terms)
        # RSI and SMA should NOT be flagged (they're in TA)
        assert not any("rsi_14" in t for t in flagged_terms)
        assert not any("sma_20" in t for t in flagged_terms)

    def test_chwa005_no_false_positives(self):
        """CHWA-005 binder: 'termination_importing_sys_module' must not be flagged."""
        ta = _ta(components=[
            _ta_component("Main Execution Handler"),
            _ta_component("Output Handler"),
        ])
        ws = _ws("WS-003", scope_in=[
            "Ensure clean script termination",
        ], prohibited_actions=[
            "Adding explicit sys.exit() calls unless required for error handling",
            "Importing sys module unless specifically needed",
        ])
        report = evaluate_cross_layer(ta, [ws])
        comp_findings = [f for f in report.findings if f.rule_id == "CLDR-003"]
        assert len(comp_findings) == 0
