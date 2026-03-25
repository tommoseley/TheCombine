"""Tier-1 tests for WP boundary overlap evaluator.

Pure unit tests — no DB, no LLM.
Tests component name overlap, WS title duplication, and scope phrase overlap.
"""

from app.domain.services.wp_overlap_evaluator import (
    OverlapFinding,
    evaluate_wp_overlap,
    _extract_component_names,
    _normalize,
    _is_generic_phrase,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _wp(wp_id, title, scope_in=None, objective=None, ws_index=None):
    """Build a minimal WP artifact dict."""
    content = {
        "wp_id": wp_id,
        "title": title,
    }
    if scope_in:
        content["scope_in"] = scope_in
    if objective:
        content["objective"] = objective
    if ws_index:
        content["ws_index"] = ws_index
    return {"doc_type_id": "work_package", "content": content}


def _ws(ws_id, parent_wp_id, title):
    """Build a minimal WS artifact dict."""
    return {
        "doc_type_id": "work_statement",
        "content": {
            "ws_id": ws_id,
            "parent_wp_id": parent_wp_id,
            "title": title,
        },
    }


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------

class TestNormalize:
    def test_lowercase(self):
        assert _normalize("Hello World") == "hello world"

    def test_collapse_whitespace(self):
        assert _normalize("hello   world") == "hello world"


class TestExtractComponentNames:
    def test_finds_engine(self):
        names = _extract_component_names("Technical Indicator Calculation Engine")
        assert any("calculation engine" in n for n in names)

    def test_finds_validator(self):
        names = _extract_component_names("Safety Validator implementation")
        assert any("safety validator" in n for n in names)

    def test_finds_manager(self):
        names = _extract_component_names("Configuration Manager setup")
        assert any("configuration manager" in n for n in names)

    def test_no_match(self):
        names = _extract_component_names("Simple Python script")
        assert len(names) == 0


class TestIsGenericPhrase:
    def test_generic(self):
        assert _is_generic_phrase("the and for") is True

    def test_not_generic(self):
        assert _is_generic_phrase("technical indicator calculation") is False

    def test_mostly_generic(self):
        # Only 1 non-generic word ("indicator") — still generic
        assert _is_generic_phrase("the indicator for") is True

    def test_two_meaningful_words(self):
        assert _is_generic_phrase("indicator calculation for") is False


# ---------------------------------------------------------------------------
# evaluate_wp_overlap — trivial cases
# ---------------------------------------------------------------------------

class TestTrivialCases:
    def test_empty_list(self):
        report = evaluate_wp_overlap([])
        assert report.wp_count == 0
        assert report.findings == []

    def test_single_wp(self):
        report = evaluate_wp_overlap([_wp("WP-001", "Setup")])
        assert report.wp_count == 1
        assert report.findings == []


# ---------------------------------------------------------------------------
# Component name overlap (WP-OVERLAP-001)
# ---------------------------------------------------------------------------

class TestComponentNameOverlap:
    def test_no_overlap(self):
        """Two WPs with different components — clean."""
        report = evaluate_wp_overlap([
            _wp("WP-001", "Decision Engine Implementation"),
            _wp("WP-002", "Order Executor Setup"),
        ])
        component_findings = [f for f in report.findings if f.rule_id == "WP-OVERLAP-001"]
        assert len(component_findings) == 0

    def test_shared_component(self):
        """Two WPs both claiming 'Indicator Engine' — finding."""
        report = evaluate_wp_overlap([
            _wp("WP-001", "Daily Data with Indicator Engine"),
            _wp("WP-002", "Technical Indicator Engine Implementation"),
        ])
        component_findings = [f for f in report.findings if f.rule_id == "WP-OVERLAP-001"]
        assert len(component_findings) >= 1
        f = component_findings[0]
        assert "WP-001" in f.wp_ids
        assert "WP-002" in f.wp_ids
        assert f.overlap_type == "component_name"

    def test_component_in_scope(self):
        """Component name overlap detected in scope_in."""
        report = evaluate_wp_overlap([
            _wp("WP-001", "Data Collection", scope_in=["Indicator Calculator implementation"]),
            _wp("WP-002", "Analysis", scope_in=["Indicator Calculator integration"]),
        ])
        component_findings = [f for f in report.findings if f.rule_id == "WP-OVERLAP-001"]
        assert len(component_findings) >= 1

    def test_component_in_ws_index(self):
        """Component name from WS titles in ws_index detected."""
        report = evaluate_wp_overlap([
            _wp("WP-001", "Data Collection", ws_index=[
                {"ws_id": "WS-001", "title": "Technical Indicator Calculation Engine"},
            ]),
            _wp("WP-002", "Analysis Engine", ws_index=[
                {"ws_id": "WS-008", "title": "Technical Indicator Calculation Engine"},
            ]),
        ])
        component_findings = [f for f in report.findings if f.rule_id == "WP-OVERLAP-001"]
        assert len(component_findings) >= 1


# ---------------------------------------------------------------------------
# WS title duplication (WP-OVERLAP-002)
# ---------------------------------------------------------------------------

class TestWSTitleDuplication:
    def test_no_duplicate_titles(self):
        """WSs under different WPs with different titles — clean."""
        report = evaluate_wp_overlap(
            [
                _wp("WP-001", "Data"),
                _wp("WP-002", "Execution"),
            ],
            ws_artifacts=[
                _ws("WS-001", "WP-001", "Market Data Fetcher"),
                _ws("WS-002", "WP-002", "Order Submission Logic"),
            ],
        )
        title_findings = [f for f in report.findings if f.rule_id == "WP-OVERLAP-002"]
        assert len(title_findings) == 0

    def test_duplicate_ws_title_across_wps(self):
        """Same WS title under different WPs — finding."""
        report = evaluate_wp_overlap(
            [
                _wp("WP-001", "Data"),
                _wp("WP-002", "Analysis"),
            ],
            ws_artifacts=[
                _ws("WS-001", "WP-001", "Technical Indicator Calculation Engine"),
                _ws("WS-008", "WP-002", "Technical Indicator Calculation Engine"),
            ],
        )
        title_findings = [f for f in report.findings if f.rule_id == "WP-OVERLAP-002"]
        assert len(title_findings) >= 1
        f = title_findings[0]
        assert "WP-001" in f.wp_ids
        assert "WP-002" in f.wp_ids


# ---------------------------------------------------------------------------
# Scope phrase overlap (WP-OVERLAP-003)
# ---------------------------------------------------------------------------

class TestScopePhraseOverlap:
    def test_no_scope_overlap(self):
        """Different scope items — clean."""
        report = evaluate_wp_overlap([
            _wp("WP-001", "Data", scope_in=["Alpaca API integration"]),
            _wp("WP-002", "Execution", scope_in=["Order submission logic"]),
        ])
        scope_findings = [f for f in report.findings if f.rule_id == "WP-OVERLAP-003"]
        assert len(scope_findings) == 0

    def test_shared_scope_phrase(self):
        """Same specific phrase in scope_in across WPs — finding."""
        report = evaluate_wp_overlap([
            _wp("WP-001", "Data", scope_in=[
                "Technical indicator calculations for RSI and SMA",
            ]),
            _wp("WP-002", "Analysis", scope_in=[
                "Technical indicator calculations and scoring",
            ]),
        ])
        scope_findings = [f for f in report.findings if f.rule_id == "WP-OVERLAP-003"]
        assert len(scope_findings) >= 1


# ---------------------------------------------------------------------------
# Report structure
# ---------------------------------------------------------------------------

class TestReportStructure:
    def test_report_summary(self):
        report = evaluate_wp_overlap([
            _wp("WP-001", "Decision Engine Work"),
            _wp("WP-002", "Decision Engine Testing"),
        ])
        s = report.summary
        assert s["wps_checked"] == 2
        assert isinstance(s["total_findings"], int)

    def test_report_to_dict(self):
        report = evaluate_wp_overlap([
            _wp("WP-001", "A"),
            _wp("WP-002", "B"),
        ])
        d = report.to_dict()
        assert "wp_count" in d
        assert "summary" in d
        assert "findings" in d
        assert isinstance(d["findings"], list)

    def test_finding_shape(self):
        report = evaluate_wp_overlap([
            _wp("WP-001", "Decision Engine"),
            _wp("WP-002", "Decision Engine"),
        ])
        assert len(report.findings) >= 1
        f = report.findings[0]
        assert isinstance(f, OverlapFinding)
        d = f.to_dict()
        assert "rule_id" in d
        assert "wp_ids" in d
        assert "overlap_type" in d
        assert "evidence" in d
        assert "message" in d


# ---------------------------------------------------------------------------
# Real-world scenario (APAM-like)
# ---------------------------------------------------------------------------

class TestAPAMScenario:
    def test_apam_indicator_overlap(self):
        """Reproduce the WP-004/WP-005 overlap from APAM binder."""
        report = evaluate_wp_overlap([
            _wp("WP-002", "Monthly Decision Generation", ws_index=[
                {"ws_id": "WS-008", "title": "Implement Technical Indicator Analysis Engine"},
            ]),
            _wp("WP-004", "Daily Market Data Collection", ws_index=[
                {"ws_id": "WS-022", "title": "Technical Indicator Calculation Engine"},
            ]),
            _wp("WP-005", "Technical Indicator Calculation Engine", ws_index=[
                {"ws_id": "WS-020", "title": "Moving Average Calculation Implementation"},
            ]),
        ])
        # Should detect overlap between WP-004 and WP-005 at minimum
        overlap_wps = set()
        for f in report.findings:
            for wp_id in f.wp_ids:
                overlap_wps.add(wp_id)
        assert "WP-004" in overlap_wps or "WP-005" in overlap_wps
