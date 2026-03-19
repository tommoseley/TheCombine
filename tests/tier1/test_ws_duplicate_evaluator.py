"""Tier-1 tests for WS duplicate objective detection (ADR-062).

Pure unit tests — no DB, no LLM.
Tests objective similarity, scope overlap, and cross-WP duplicate detection.
"""

from app.domain.services.ws_duplicate_evaluator import (
    DuplicateFinding,
    evaluate_ws_duplicates,
    _extract_keywords,
    _keyword_similarity,
    _normalize_text,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _ws(ws_id, parent_wp_id, objective, scope_in=None):
    """Build a minimal WS artifact."""
    content = {
        "ws_id": ws_id,
        "parent_wp_id": parent_wp_id,
        "objective": objective,
    }
    if scope_in:
        content["scope_in"] = scope_in
    return {"doc_type_id": "work_statement", "content": content}


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------

class TestNormalizeText:
    def test_lowercase(self):
        assert _normalize_text("Hello World") == "hello world"

    def test_strips_punctuation(self):
        assert _normalize_text("hello, world!") == "hello world"

    def test_collapses_whitespace(self):
        assert _normalize_text("hello   world") == "hello world"


class TestExtractKeywords:
    def test_removes_stop_words(self):
        kw = _extract_keywords("Implement the core authentication for API")
        assert "the" not in kw
        assert "for" not in kw
        assert "implement" in kw
        assert "authentication" in kw

    def test_removes_short_words(self):
        kw = _extract_keywords("an API to do it")
        assert "an" not in kw
        assert "to" not in kw
        assert "do" not in kw

    def test_empty_string(self):
        assert _extract_keywords("") == set()


class TestKeywordSimilarity:
    def test_identical_sets(self):
        s = {"alpha", "beta", "gamma"}
        assert _keyword_similarity(s, s) == 1.0

    def test_disjoint_sets(self):
        assert _keyword_similarity({"a", "b"}, {"c", "d"}) == 0.0

    def test_partial_overlap(self):
        sim = _keyword_similarity({"a", "b", "c"}, {"b", "c", "d"})
        assert 0.6 < sim < 0.7  # 2/min(3,3) = 0.667

    def test_empty_set(self):
        assert _keyword_similarity(set(), {"a"}) == 0.0
        assert _keyword_similarity(set(), set()) == 0.0


# ---------------------------------------------------------------------------
# Trivial cases
# ---------------------------------------------------------------------------

class TestTrivialCases:
    def test_empty_list(self):
        report = evaluate_ws_duplicates([])
        assert report.ws_count == 0
        assert report.findings == []

    def test_single_ws(self):
        report = evaluate_ws_duplicates([_ws("WS-001", "WP-001", "Do something")])
        assert report.ws_count == 1
        assert report.findings == []


# ---------------------------------------------------------------------------
# Objective duplicates (DUP-OBJ-001)
# ---------------------------------------------------------------------------

class TestObjectiveDuplicates:
    def test_different_objectives_no_finding(self):
        """Completely different objectives — no duplicate."""
        report = evaluate_ws_duplicates([
            _ws("WS-001", "WP-001", "Implement SQLite database schema"),
            _ws("WS-013", "WP-003", "Configure Windows Task Scheduler"),
        ])
        obj_findings = [f for f in report.findings if f.rule_id == "DUP-OBJ-001"]
        assert len(obj_findings) == 0

    def test_similar_objectives_cross_wp(self):
        """Near-identical objectives under different WPs — finding."""
        report = evaluate_ws_duplicates([
            _ws("WS-002", "WP-001", "Implement Alpaca API client with authentication and credential management"),
            _ws("WS-013", "WP-003", "Implement Alpaca API client authentication and credential management setup"),
        ])
        obj_findings = [f for f in report.findings if f.rule_id == "DUP-OBJ-001"]
        assert len(obj_findings) >= 1
        f = obj_findings[0]
        assert "WS-002" in f.ws_ids
        assert "WS-013" in f.ws_ids

    def test_same_wp_not_flagged(self):
        """Similar objectives under the SAME WP — not flagged (intra-WP is fine)."""
        report = evaluate_ws_duplicates([
            _ws("WS-001", "WP-001", "Implement Alpaca API authentication"),
            _ws("WS-002", "WP-001", "Implement Alpaca API authentication setup"),
        ])
        obj_findings = [f for f in report.findings if f.rule_id == "DUP-OBJ-001"]
        assert len(obj_findings) == 0

    def test_finding_includes_wp_ids(self):
        """Finding includes parent WP IDs for context."""
        report = evaluate_ws_duplicates([
            _ws("WS-002", "WP-001", "Implement Alpaca API authentication and credential management"),
            _ws("WS-013", "WP-003", "Implement Alpaca API authentication credential management"),
        ])
        obj_findings = [f for f in report.findings if f.rule_id == "DUP-OBJ-001"]
        assert len(obj_findings) >= 1
        assert "WP-001" in obj_findings[0].parent_wp_ids
        assert "WP-003" in obj_findings[0].parent_wp_ids


# ---------------------------------------------------------------------------
# Scope duplicates (DUP-SCOPE-001)
# ---------------------------------------------------------------------------

class TestScopeDuplicates:
    def test_different_scope_no_finding(self):
        """Completely different scope_in — no duplicate."""
        report = evaluate_ws_duplicates([
            _ws("WS-001", "WP-001", "Data collection",
                scope_in=["Alpaca API integration", "Yahoo Finance fallback"]),
            _ws("WS-013", "WP-003", "Order execution",
                scope_in=["Limit order placement", "Order status tracking"]),
        ])
        scope_findings = [f for f in report.findings if f.rule_id == "DUP-SCOPE-001"]
        assert len(scope_findings) == 0

    def test_overlapping_scope_cross_wp(self):
        """Similar scope_in across different WPs — finding."""
        report = evaluate_ws_duplicates([
            _ws("WS-011", "WP-002", "Decision logging",
                scope_in=["Decision audit trail and CSV logging",
                           "SQLite database logging of decisions"]),
            _ws("WS-017", "WP-003", "Trade logging",
                scope_in=["Trade confirmation and CSV logging",
                           "Execution audit trail and logging"]),
        ])
        scope_findings = [f for f in report.findings if f.rule_id == "DUP-SCOPE-001"]
        assert len(scope_findings) >= 1


# ---------------------------------------------------------------------------
# Report structure
# ---------------------------------------------------------------------------

class TestReportStructure:
    def test_report_summary(self):
        report = evaluate_ws_duplicates([
            _ws("WS-001", "WP-001", "A"),
            _ws("WS-002", "WP-002", "B"),
        ])
        s = report.summary
        assert s["ws_checked"] == 2
        assert isinstance(s["total_findings"], int)

    def test_report_to_dict(self):
        report = evaluate_ws_duplicates([
            _ws("WS-001", "WP-001", "A"),
            _ws("WS-002", "WP-002", "B"),
        ])
        d = report.to_dict()
        assert "ws_count" in d
        assert "summary" in d
        assert "findings" in d

    def test_finding_shape(self):
        report = evaluate_ws_duplicates([
            _ws("WS-002", "WP-001", "Implement Alpaca API authentication and credential management"),
            _ws("WS-013", "WP-003", "Implement Alpaca API authentication credential management"),
        ])
        assert len(report.findings) >= 1
        f = report.findings[0]
        assert isinstance(f, DuplicateFinding)
        d = f.to_dict()
        for key in ("rule_id", "ws_ids", "parent_wp_ids",
                     "duplicate_type", "evidence", "message"):
            assert key in d


# ---------------------------------------------------------------------------
# APAM-like scenario
# ---------------------------------------------------------------------------

class TestAPAMScenario:
    def test_alpaca_auth_duplication(self):
        """Reproduce APAM-005 critique: WS-002 and WS-013 both implement Alpaca auth."""
        report = evaluate_ws_duplicates([
            _ws("WS-002", "WP-001",
                "Implement Alpaca Market Data API client with authentication and credential management",
                scope_in=["Alpaca API credentials management and authentication",
                           "API rate limiting and exponential backoff retry logic"]),
            _ws("WS-013", "WP-003",
                "Establish secure connection to Alpaca Trading API with credential management and authentication",
                scope_in=["Alpaca Trading API integration for paper trading",
                           "API credential management and authentication"]),
            _ws("WS-007", "WP-002",
                "Implement technical indicator scoring algorithm",
                scope_in=["SMA crossover scoring logic", "RSI scoring"]),
        ])
        # Should detect WS-002/WS-013 overlap but not WS-007
        all_ws_ids = set()
        for f in report.findings:
            all_ws_ids.update(f.ws_ids)
        assert "WS-002" in all_ws_ids
        assert "WS-013" in all_ws_ids
        assert "WS-007" not in all_ws_ids
