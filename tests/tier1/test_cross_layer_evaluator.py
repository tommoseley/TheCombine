"""Tier-1 tests for cross-layer contradiction evaluator (ADR-061).

Pure unit tests — no DB, no LLM.
Tests TA surface extraction, contradiction detection, and report structure.
"""

from app.domain.services.cross_layer_evaluator import (
    ContradictionFinding,
    evaluate_cross_layer,
    extract_ta_surfaces,
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
# Component mismatches (CLDR-003)
# ---------------------------------------------------------------------------

class TestComponentMismatches:
    def test_ws_references_declared_component(self):
        """WS references a component that IS in TA — no finding."""
        ta = _ta(components=[_ta_component("Daily Indicator Engine")])
        ws = _ws("WS-005", objective="Integrate Daily Indicator Engine")
        report = evaluate_cross_layer(ta, [ws])
        comp_findings = [f for f in report.findings if f.rule_id == "CLDR-003"]
        assert len(comp_findings) == 0

    def test_ws_references_undeclared_component(self):
        """WS references a component NOT in TA — finding."""
        ta = _ta(components=[_ta_component("Daily Indicator Engine")])
        ws = _ws("WS-023", objective="Implement Email Notification Service")
        report = evaluate_cross_layer(ta, [ws])
        comp_findings = [f for f in report.findings if f.rule_id == "CLDR-003"]
        assert len(comp_findings) >= 1
        assert any("notification_service" in f.ws_claim.lower() or
                    "email" in f.ws_claim.lower()
                    for f in comp_findings)


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
# APAM-like scenario
# ---------------------------------------------------------------------------

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
