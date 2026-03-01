"""
Tests for router pure functions -- WS-CRAP-004.

Tests extracted pure functions: extract_classification, score_route,
determine_confidence.
"""

import pytest

from app.api.services.mech_handlers.router import (
    extract_classification,
    score_route,
    determine_confidence,
)


# =========================================================================
# extract_classification
# =========================================================================


class TestExtractClassification:
    """Tests for extract_classification pure function."""

    def test_default_field_extraction(self):
        intake = {
            "project_type": "greenfield",
            "artifact_type": "web_app",
            "audience": "internal",
            "classification": "standard",
            "confidence": "high",
            "other_field": "ignored",
        }
        result = extract_classification(intake, {})
        assert result == {
            "project_type": "greenfield",
            "artifact_type": "web_app",
            "audience": "internal",
            "classification": "standard",
            "confidence": "high",
        }

    def test_custom_jsonpath_extraction(self):
        intake = {"metadata": {"type": "greenfield"}, "details": {"scope": "large"}}
        config = {
            "classification_fields": [
                {"path": "$.metadata.type", "as": "project_type"},
                {"path": "$.details.scope", "as": "scope"},
            ]
        }
        result = extract_classification(intake, config)
        assert result == {"project_type": "greenfield", "scope": "large"}

    def test_jsonpath_missing_value_skipped(self):
        intake = {"metadata": {"type": "greenfield"}}
        config = {
            "classification_fields": [
                {"path": "$.metadata.type", "as": "project_type"},
                {"path": "$.metadata.missing", "as": "missing"},
            ]
        }
        result = extract_classification(intake, config)
        assert result == {"project_type": "greenfield"}

    def test_invalid_jsonpath_skipped(self):
        intake = {"type": "test"}
        config = {
            "classification_fields": [
                {"path": "$[invalid", "as": "bad"},
            ]
        }
        result = extract_classification(intake, config)
        assert result == {}

    def test_empty_intake_default_fields(self):
        result = extract_classification({}, {})
        assert result == {}

    def test_partial_default_fields(self):
        intake = {"project_type": "greenfield"}
        result = extract_classification(intake, {})
        assert result == {"project_type": "greenfield"}

    def test_missing_path_or_as_skipped(self):
        intake = {"type": "test"}
        config = {
            "classification_fields": [
                {"path": "$.type"},  # missing "as"
                {"as": "result"},  # missing "path"
            ]
        }
        result = extract_classification(intake, config)
        assert result == {}


# =========================================================================
# score_route
# =========================================================================


class TestScoreRoute:
    """Tests for score_route pure function."""

    def test_full_match_high_confidence(self):
        route = {
            "match": {"project_type": "greenfield"},
            "confidence": "high",
        }
        classification = {"project_type": "greenfield"}
        score = score_route(route, classification)
        assert score == pytest.approx(1.0)  # 1/1 * 0.9 + 0.1 = 1.0

    def test_full_match_medium_confidence(self):
        route = {
            "match": {"project_type": "greenfield"},
            "confidence": "medium",
        }
        classification = {"project_type": "greenfield"}
        score = score_route(route, classification)
        assert score == pytest.approx(0.95)  # 1/1 * 0.9 + 0.05

    def test_no_match_conditions_low_score(self):
        route = {"match": {}}
        classification = {"project_type": "greenfield"}
        score = score_route(route, classification)
        assert score == pytest.approx(0.1)

    def test_missing_match_key(self):
        route = {}
        classification = {"project_type": "greenfield"}
        score = score_route(route, classification)
        assert score == pytest.approx(0.1)

    def test_partial_match(self):
        route = {
            "match": {
                "project_type": "greenfield",
                "artifact_type": "web_app",
            },
            "confidence": "medium",
        }
        classification = {"project_type": "greenfield", "artifact_type": "api"}
        score = score_route(route, classification)
        # 1/2 match * 0.9 + 0.05 = 0.5
        assert score == pytest.approx(0.5)

    def test_no_match_at_all(self):
        route = {
            "match": {"project_type": "greenfield"},
            "confidence": "low",
        }
        classification = {"project_type": "brownfield"}
        score = score_route(route, classification)
        # 0/1 * 0.9 + 0.0 = 0.0
        assert score == pytest.approx(0.0)

    def test_list_match_values(self):
        route = {
            "match": {"project_type": ["greenfield", "brownfield"]},
            "confidence": "high",
        }
        classification = {"project_type": "brownfield"}
        score = score_route(route, classification)
        assert score == pytest.approx(1.0)

    def test_classification_missing_field(self):
        route = {
            "match": {"project_type": "greenfield"},
            "confidence": "medium",
        }
        classification = {}  # field missing
        score = score_route(route, classification)
        # 0/1 * 0.9 + 0.05 = 0.05
        assert score == pytest.approx(0.05)


# =========================================================================
# determine_confidence
# =========================================================================


class TestDetermineConfidence:
    """Tests for determine_confidence pure function."""

    def test_low_score_returns_low(self):
        winner = {"score": 0.2, "configured_confidence": "high"}
        candidates = [winner]
        assert determine_confidence(winner, candidates) == "low"

    def test_high_score_returns_configured(self):
        winner = {"score": 0.8, "configured_confidence": "high"}
        candidates = [winner]
        assert determine_confidence(winner, candidates) == "high"

    def test_close_scores_downgrades_high_to_medium(self):
        winner = {"score": 0.8, "configured_confidence": "high"}
        runner_up = {"score": 0.75}
        candidates = [winner, runner_up]
        assert determine_confidence(winner, candidates) == "medium"

    def test_close_scores_downgrades_medium_to_low(self):
        winner = {"score": 0.8, "configured_confidence": "medium"}
        runner_up = {"score": 0.75}
        candidates = [winner, runner_up]
        assert determine_confidence(winner, candidates) == "low"

    def test_clear_gap_keeps_configured(self):
        winner = {"score": 0.8, "configured_confidence": "high"}
        runner_up = {"score": 0.5}
        candidates = [winner, runner_up]
        assert determine_confidence(winner, candidates) == "high"

    def test_medium_score_downgrades_high(self):
        winner = {"score": 0.5, "configured_confidence": "high"}
        candidates = [winner]
        assert determine_confidence(winner, candidates) == "medium"

    def test_medium_score_keeps_medium(self):
        winner = {"score": 0.5, "configured_confidence": "medium"}
        candidates = [winner]
        assert determine_confidence(winner, candidates) == "medium"

    def test_medium_score_keeps_low(self):
        winner = {"score": 0.5, "configured_confidence": "low"}
        candidates = [winner]
        assert determine_confidence(winner, candidates) == "low"

    def test_single_candidate_no_gap_check(self):
        winner = {"score": 0.8, "configured_confidence": "high"}
        candidates = [winner]
        assert determine_confidence(winner, candidates) == "high"
