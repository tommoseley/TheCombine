"""Tests for ConstraintDriftValidator.

Per ADR-042 and WS-ADR-042-001 Phase 5.
"""

import pytest
from app.domain.workflow.validation.constraint_drift_validator import ConstraintDriftValidator
from app.domain.workflow.validation import DriftViolation, DriftValidationResult


class TestConstraintDriftValidator:
    """Tests for ConstraintDriftValidator."""

    @pytest.fixture
    def validator(self):
        return ConstraintDriftValidator()

    @pytest.fixture
    def web_platform_invariant(self):
        """Binding invariant for web platform selection."""
        return {
            "id": "TARGET_PLATFORM",
            "text": "What platform should the app target?",
            "priority": "must",
            "answer_type": "single_choice",
            "constraint_kind": "selection",
            "choices": [
                {"id": "web", "label": "Web browser"},
                {"id": "mobile", "label": "Mobile application"},
            ],
            "user_answer": "web",
            "user_answer_label": "Web browser",
            "resolved": True,
            "binding": True,
            "binding_source": "priority",
            "binding_reason": "must-priority question with resolved answer",
        }

    @pytest.fixture
    def no_offline_exclusion(self):
        """Binding invariant for offline mode exclusion."""
        return {
            "id": "OFFLINE_MODE",
            "text": "Should the app support offline mode?",
            "priority": "must",
            "answer_type": "yes_no",
            "constraint_kind": "exclusion",
            "user_answer": False,
            "user_answer_label": "No",
            "resolved": True,
            "binding": True,
            "binding_source": "exclusion",
            "binding_reason": "explicit exclusion constraint",
        }


class TestNoInvariants(TestConstraintDriftValidator):
    """Tests with no invariants."""

    def test_empty_invariants_passes(self, validator):
        """Validation passes when no invariants to check."""
        artifact = {"known_constraints": [], "summary": "A document"}
        result = validator.validate(artifact, [])

        assert result.passed is True
        assert len(result.violations) == 0


class TestQAPGC001Contradiction(TestConstraintDriftValidator):
    """Tests for QA-PGC-001: Contradiction detection.

    Note: Exclusion detection currently checks for the answer label, not the topic.
    This is a known limitation - proper topic extraction would require NLP.
    Tests are written to match current behavior.
    """

    def test_wrong_selection_stated_fails(self, validator, web_platform_invariant):
        """Stating a different option than selected should fail QA-PGC-001."""
        # Explicitly state the wrong platform
        artifact = {
            "summary": "Platform is mobile for this project",
            "known_constraints": [{"text": "Using mobile application"}],
        }

        result = validator.validate(artifact, [web_platform_invariant])

        # Should fail because "platform is mobile" when user selected web
        assert result.passed is False
        errors = [v for v in result.violations if v.check_id == "QA-PGC-001"]
        assert len(errors) >= 1
        assert errors[0].severity == "ERROR"

    def test_correct_selection_stated_passes(self, validator, web_platform_invariant):
        """Stating the selected option should pass."""
        artifact = {
            "summary": "Web browser application",
            "known_constraints": [{"text": "Web browser is the target platform"}],
        }

        result = validator.validate(artifact, [web_platform_invariant])

        # May have warnings, but no errors
        assert result.passed is True


class TestQAPGC002ReopenedDecision(TestConstraintDriftValidator):
    """Tests for QA-PGC-002: Reopened decision detection.

    Detection uses regex patterns to find "decision required", "needs to be decided",
    "options include", etc. near topic words from the question.
    """

    def test_decision_required_language_fails(self, validator, web_platform_invariant):
        """Using 'decision required' near topic should fail QA-PGC-002."""
        artifact = {
            "summary": "The platform decision required before development",
            "known_constraints": [{"text": "web browser"}],
        }

        result = validator.validate(artifact, [web_platform_invariant])

        assert result.passed is False
        errors = [v for v in result.violations if v.check_id == "QA-PGC-002"]
        assert len(errors) >= 1
        assert errors[0].severity == "ERROR"

    def test_stating_decision_as_constraint_passes(self, validator, web_platform_invariant):
        """Stating the decided value as constraint should pass."""
        artifact = {
            "summary": "Web browser based application",
            "known_constraints": [
                {"text": "Target platform is web browser"}
            ],
        }

        result = validator.validate(artifact, [web_platform_invariant])

        # Should pass (no errors)
        assert result.passed is True


class TestQAPGC003SilentOmission(TestConstraintDriftValidator):
    """Tests for QA-PGC-003: Silent omission detection."""

    def test_omitting_bound_constraint_warns(self, validator, web_platform_invariant):
        """Silently omitting bound constraint should warn."""
        artifact = {
            "summary": "Application development project",
            "known_constraints": [],
            # No mention of "web" or "web browser" anywhere
        }

        result = validator.validate(artifact, [web_platform_invariant])

        warnings = [v for v in result.violations if v.check_id == "QA-PGC-003"]
        assert len(warnings) >= 1
        assert warnings[0].severity == "WARNING"

    def test_mentioning_bound_value_passes(self, validator, web_platform_invariant):
        """Mentioning the bound value should pass QA-PGC-003."""
        artifact = {
            "summary": "Web browser application with modern UI",
            "known_constraints": [],
        }

        result = validator.validate(artifact, [web_platform_invariant])

        # QA-PGC-003 should not fire since "web browser" is mentioned
        omission_warnings = [v for v in result.violations if v.check_id == "QA-PGC-003"]
        assert len(omission_warnings) == 0


class TestQAPGC004Traceability(TestConstraintDriftValidator):
    """Tests for QA-PGC-004: Traceability detection."""

    def test_missing_known_constraints_section_warns(self, validator, web_platform_invariant):
        """Missing known_constraints section should warn."""
        artifact = {
            "summary": "Web browser project",
            # No known_constraints key at all
        }

        result = validator.validate(artifact, [web_platform_invariant])

        traceability_warnings = [v for v in result.violations if v.check_id == "QA-PGC-004"]
        assert len(traceability_warnings) >= 1
        assert traceability_warnings[0].severity == "WARNING"

    def test_constraint_in_known_constraints_passes(self, validator, web_platform_invariant):
        """Having constraint in known_constraints should pass QA-PGC-004."""
        artifact = {
            "summary": "Web browser application",
            "known_constraints": [
                {"id": "KC-001", "text": "Web browser is the target platform"}
            ],
        }

        result = validator.validate(artifact, [web_platform_invariant])

        traceability_warnings = [v for v in result.violations if v.check_id == "QA-PGC-004"]
        assert len(traceability_warnings) == 0


class TestIntegrationScenarios(TestConstraintDriftValidator):
    """Integration tests matching WS-ADR-042-001 scenarios."""

    def test_scenario_1_platform_reopened(self, validator, web_platform_invariant):
        """Scenario 1: Reopening platform decision should fail QA-PGC-002."""
        artifact = {
            "summary": "The target platform needs to be decided before development",
            "early_decision_points": [
                {
                    "topic": "Platform Selection",
                    "description": "Decision required for platform",
                }
            ],
            "known_constraints": [{"text": "web browser"}],
        }

        result = validator.validate(artifact, [web_platform_invariant])

        # Should fail due to reopening platform decision
        assert result.passed is False
        errors = [v for v in result.violations if v.check_id == "QA-PGC-002"]
        assert len(errors) >= 1

    def test_scenario_4_happy_path(self, validator, web_platform_invariant):
        """Scenario 4: Happy path with constraint locked and discussed."""
        artifact = {
            "summary": "Web browser application targeting modern browsers",
            "known_constraints": [
                {
                    "id": "KC-PLATFORM",
                    "text": "Target platform: web browser",
                    "source": "user clarification",
                }
            ],
            "assumptions": [
                {"text": "SPA vs MPA is a downstream decision within web platform"}
            ],
        }

        result = validator.validate(artifact, [web_platform_invariant])

        # Should pass completely
        assert result.passed is True
        # May have no violations at all
        errors = [v for v in result.violations if v.severity == "ERROR"]
        assert len(errors) == 0


class TestDriftValidationResult:
    """Tests for DriftValidationResult data class."""

    def test_errors_property(self):
        """errors property should return only ERROR violations."""
        result = DriftValidationResult(
            passed=False,
            violations=[
                DriftViolation("QA-PGC-001", "ERROR", "ID1", "Error msg"),
                DriftViolation("QA-PGC-003", "WARNING", "ID2", "Warning msg"),
            ],
        )

        assert len(result.errors) == 1
        assert result.errors[0].check_id == "QA-PGC-001"

    def test_warnings_property(self):
        """warnings property should return only WARNING violations."""
        result = DriftValidationResult(
            passed=False,
            violations=[
                DriftViolation("QA-PGC-001", "ERROR", "ID1", "Error msg"),
                DriftViolation("QA-PGC-003", "WARNING", "ID2", "Warning msg"),
            ],
        )

        assert len(result.warnings) == 1
        assert result.warnings[0].check_id == "QA-PGC-003"

    def test_error_summary(self):
        """error_summary should format all errors."""
        result = DriftValidationResult(
            passed=False,
            violations=[
                DriftViolation("QA-PGC-001", "ERROR", "ID1", "First error"),
                DriftViolation("QA-PGC-002", "ERROR", "ID2", "Second error"),
            ],
        )

        summary = result.error_summary
        assert "QA-PGC-001" in summary
        assert "QA-PGC-002" in summary
        assert "First error" in summary
        assert "Second error" in summary


class TestFalsePositiveRegression:
    """Regression tests for false positive issues."""

    @pytest.fixture
    def validator(self):
        return ConstraintDriftValidator()

    def test_without_word_not_extracted_as_topic(self, validator):
        """Regression: 'without' from question should not be extracted as topic.

        Bug: Question like "Should the app work without internet?" caused
        'without' to be extracted as a topic word. Artifact text containing
        'without' innocuously would trigger false QA-PGC-002 errors.

        See session 2026-01-24.
        """
        # Invariant with "without" in question text
        offline_invariant = {
            "id": "OFFLINE_CAPABILITY",
            "text": "Should the app work without internet connectivity?",
            "priority": "must",
            "answer_type": "yes_no",
            "constraint_kind": "selection",
            "user_answer": False,
            "user_answer_label": "No",
            "resolved": True,
            "binding": True,
            "binding_source": "priority",
            "binding_reason": "must-priority question with resolved answer",
        }

        # Artifact that uses "without" innocuously (not reopening any decision)
        artifact = {
            "summary": "Online-only application without offline caching. No offline capability required.",
            "known_constraints": [
                {"id": "KC-OFFLINE", "text": "No offline capability - online only"}
            ],
        }

        result = validator.validate(artifact, [offline_invariant])

        # Should NOT fail with QA-PGC-002 for "without" being "reopened"
        errors = [v for v in result.violations if v.check_id == "QA-PGC-002"]
        assert len(errors) == 0, f"False positive QA-PGC-002: {errors}"

    def test_common_words_filtered_from_topics(self, validator):
        """Common words should not be extracted as topic words."""
        # Verify internal method filters stopwords
        topics = validator._extract_topic_words(
            "Should the app work without internet connectivity?"
        )

        # These common words should NOT be in topics
        filtered_words = {"should", "the", "app", "work", "without"}
        for word in filtered_words:
            assert word not in topics, f"'{word}' should be filtered as stopword"

        # "internet" and "connectivity" should be extracted (meaningful topics)
        assert "internet" in topics or "connectivity" in topics
