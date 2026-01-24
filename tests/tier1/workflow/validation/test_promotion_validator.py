"""Tests for PromotionValidator.

Per WS-PGC-VALIDATION-001 Phase 1.
"""

import pytest

from app.domain.workflow.validation import (
    PromotionValidator,
    PromotionValidationInput,
)
from app.domain.workflow.validation.rules import (
    extract_keywords,
    jaccard_similarity,
    keyword_overlap_ratio,
)


class TestKeywordExtraction:
    """Tests for keyword extraction utility."""

    def test_extracts_meaningful_words(self):
        """Should extract nouns and verbs, not stopwords."""
        keywords = extract_keywords("The user must authenticate before accessing the system")
        assert "user" in keywords
        assert "authenticate" in keywords
        assert "accessing" in keywords
        assert "system" in keywords
        # Stopwords excluded
        assert "the" not in keywords
        assert "must" not in keywords
        assert "before" not in keywords

    def test_case_insensitive(self):
        """Keywords should be lowercase."""
        keywords = extract_keywords("User Authentication System")
        assert "user" in keywords
        assert "authentication" in keywords
        assert "User" not in keywords

    def test_empty_string_returns_empty_set(self):
        """Empty input returns empty set."""
        assert extract_keywords("") == set()
        assert extract_keywords(None) == set()

    def test_filters_short_words(self):
        """Words with 2 or fewer chars are filtered."""
        keywords = extract_keywords("I am a user of the app")
        assert "user" in keywords
        assert "app" in keywords
        assert "am" not in keywords
        assert "of" not in keywords


class TestJaccardSimilarity:
    """Tests for Jaccard similarity calculation."""

    def test_identical_sets(self):
        """Identical sets have similarity 1.0."""
        s = {"user", "auth", "system"}
        assert jaccard_similarity(s, s) == 1.0

    def test_disjoint_sets(self):
        """Disjoint sets have similarity 0.0."""
        s1 = {"user", "auth"}
        s2 = {"payment", "invoice"}
        assert jaccard_similarity(s1, s2) == 0.0

    def test_partial_overlap(self):
        """Partial overlap gives expected ratio."""
        s1 = {"user", "auth", "system"}
        s2 = {"user", "system", "database"}
        # intersection: {user, system} = 2
        # union: {user, auth, system, database} = 4
        assert jaccard_similarity(s1, s2) == 0.5

    def test_empty_sets(self):
        """Empty sets have similarity 0.0."""
        assert jaccard_similarity(set(), set()) == 0.0
        assert jaccard_similarity({"a"}, set()) == 0.0


class TestKeywordOverlapRatio:
    """Tests for keyword overlap ratio calculation."""

    def test_full_overlap(self):
        """All target keywords in source = 1.0."""
        source = {"user", "auth", "system", "database"}
        target = {"user", "system"}
        assert keyword_overlap_ratio(source, target) == 1.0

    def test_no_overlap(self):
        """No overlap = 0.0."""
        source = {"payment", "invoice"}
        target = {"user", "auth"}
        assert keyword_overlap_ratio(source, target) == 0.0

    def test_partial_overlap(self):
        """Partial overlap gives fraction of target found."""
        source = {"user", "auth"}
        target = {"user", "auth", "system", "database"}
        # 2 of 4 target keywords found
        assert keyword_overlap_ratio(source, target) == 0.5

    def test_empty_target(self):
        """Empty target returns 0.0."""
        assert keyword_overlap_ratio({"a", "b"}, set()) == 0.0


class TestPromotionValidity:
    """Tests for Rule 1: Promotion Validity."""

    @pytest.fixture
    def validator(self):
        return PromotionValidator()

    def test_must_answer_creates_valid_constraint(self, validator):
        """Constraint from must-answer with 50%+ keyword match should not warn."""
        input_data = PromotionValidationInput(
            pgc_questions=[
                {"id": "AUTH", "text": "User authentication required?", "priority": "must"}
            ],
            pgc_answers={"AUTH": True},
            generated_document={
                "known_constraints": [
                    {"id": "CNS-1", "constraint": "User authentication is required"}
                ],
                "assumptions": [],
            },
        )
        result = validator.validate(input_data)

        # Should not have promotion warnings for this constraint
        promotion_warnings = [
            w for w in result.warnings
            if w.check_type == "promotion" and w.field_id == "CNS-1"
        ]
        assert len(promotion_warnings) == 0

    def test_should_answer_as_constraint_warns(self, validator):
        """Constraint derived from should-answer emits warning."""
        input_data = PromotionValidationInput(
            pgc_questions=[
                {"id": "TRACKING", "text": "Should include progress tracking?", "priority": "should"}
            ],
            pgc_answers={"TRACKING": True},
            generated_document={
                "known_constraints": [
                    {"id": "CNS-1", "constraint": "Must include progress tracking feature"}
                ],
                "assumptions": [],
            },
        )
        result = validator.validate(input_data)

        assert result.passed is True  # Warnings don't fail
        promotion_warnings = [w for w in result.warnings if w.check_type == "promotion"]
        assert len(promotion_warnings) == 1
        assert "should" in promotion_warnings[0].message.lower()

    def test_could_answer_as_constraint_warns(self, validator):
        """Constraint derived from could-answer emits warning."""
        input_data = PromotionValidationInput(
            pgc_questions=[
                {"id": "EXPORT", "text": "Could support data export?", "priority": "could"}
            ],
            pgc_answers={"EXPORT": "CSV format"},
            generated_document={
                "known_constraints": [
                    {"id": "CNS-1", "constraint": "Must support CSV data export"}
                ],
                "assumptions": [],
            },
        )
        result = validator.validate(input_data)

        assert result.passed is True
        promotion_warnings = [w for w in result.warnings if w.check_type == "promotion"]
        assert len(promotion_warnings) == 1
        assert "could" in promotion_warnings[0].message.lower()

    def test_intake_stated_constraint_valid(self, validator):
        """Constraint explicitly in intake is valid."""
        input_data = PromotionValidationInput(
            pgc_questions=[],
            pgc_answers={},
            generated_document={
                "known_constraints": [
                    {"id": "CNS-1", "constraint": "Mobile application for iOS and Android"}
                ],
                "assumptions": [],
            },
            intake={
                "artifact_type": "mobile application",
                "description": "Build for iOS and Android platforms",
            },
        )
        result = validator.validate(input_data)

        promotion_warnings = [
            w for w in result.warnings
            if w.check_type == "promotion" and w.field_id == "CNS-1"
        ]
        assert len(promotion_warnings) == 0

    def test_no_match_warns(self, validator):
        """Constraint with < 50% keyword match to any source warns."""
        input_data = PromotionValidationInput(
            pgc_questions=[
                {"id": "AUTH", "text": "User authentication required?", "priority": "must"}
            ],
            pgc_answers={"AUTH": True},
            generated_document={
                "known_constraints": [
                    {"id": "CNS-1", "constraint": "Database must support concurrent transactions"}
                ],
                "assumptions": [],
            },
        )
        result = validator.validate(input_data)

        promotion_warnings = [
            w for w in result.warnings
            if w.check_type == "promotion" and w.field_id == "CNS-1"
        ]
        assert len(promotion_warnings) == 1
        assert "no traceable source" in promotion_warnings[0].message.lower()


class TestInternalContradictions:
    """Tests for Rule 2: Internal Contradiction."""

    @pytest.fixture
    def validator(self):
        return PromotionValidator()

    def test_same_item_in_both_sections_errors(self, validator):
        """Same concept (> 50% Jaccard) in assumptions and constraints is error."""
        # Use nearly identical text to ensure > 50% Jaccard similarity
        # Keywords: {oauth, authentication, required} vs {oauth, authentication, available}
        # Jaccard = 2/4 = 0.5, but we need > 0.5, so use more overlap
        input_data = PromotionValidationInput(
            pgc_questions=[],
            pgc_answers={},
            generated_document={
                "known_constraints": [
                    {"id": "CNS-1", "constraint": "OAuth authentication mechanism required"}
                ],
                "assumptions": [
                    {"id": "ASM-1", "assumption": "OAuth authentication mechanism available"}
                ],
            },
        )
        result = validator.validate(input_data)

        assert result.passed is False  # Errors fail validation
        assert len(result.errors) >= 1
        contradiction_errors = [e for e in result.errors if e.check_type == "contradiction"]
        assert len(contradiction_errors) == 1

    def test_similar_but_different_items_ok(self, validator):
        """Items with < 50% Jaccard similarity should not error."""
        input_data = PromotionValidationInput(
            pgc_questions=[],
            pgc_answers={},
            generated_document={
                "known_constraints": [
                    {"id": "CNS-1", "constraint": "User authentication required"}
                ],
                "assumptions": [
                    {"id": "ASM-1", "assumption": "Database supports PostgreSQL"}
                ],
            },
        )
        result = validator.validate(input_data)

        contradiction_errors = [e for e in result.errors if e.check_type == "contradiction"]
        assert len(contradiction_errors) == 0


class TestPolicyConformance:
    """Tests for Rule 3: Policy Conformance."""

    @pytest.fixture
    def validator(self):
        return PromotionValidator()

    def test_budget_question_warns(self, validator):
        """Questions containing 'budget' emit warning."""
        input_data = PromotionValidationInput(
            pgc_questions=[],
            pgc_answers={},
            generated_document={
                "known_constraints": [],
                "assumptions": [],
                "unknowns": [
                    {"id": "UNK-1", "question": "What is the project budget?"}
                ],
            },
        )
        result = validator.validate(input_data)

        policy_warnings = [w for w in result.warnings if w.check_type == "policy"]
        assert len(policy_warnings) == 1
        assert "budget" in policy_warnings[0].evidence["prohibited_term"]

    def test_timeline_question_ok(self, validator):
        """Questions about timeline are acceptable."""
        input_data = PromotionValidationInput(
            pgc_questions=[],
            pgc_answers={},
            generated_document={
                "known_constraints": [],
                "assumptions": [],
                "unknowns": [
                    {"id": "UNK-1", "question": "What is the expected timeline?"}
                ],
            },
        )
        result = validator.validate(input_data)

        policy_warnings = [w for w in result.warnings if w.check_type == "policy"]
        assert len(policy_warnings) == 0

    def test_case_insensitive(self, validator):
        """'BUDGET' and 'Budget' both trigger warning."""
        input_data = PromotionValidationInput(
            pgc_questions=[],
            pgc_answers={},
            generated_document={
                "known_constraints": [],
                "assumptions": [],
                "unknowns": [
                    {"id": "UNK-1", "question": "BUDGET constraints?"},
                    {"id": "UNK-2", "question": "Budget limits?"},
                ],
            },
        )
        result = validator.validate(input_data)

        policy_warnings = [w for w in result.warnings if w.check_type == "policy"]
        assert len(policy_warnings) == 2

    def test_authority_question_warns(self, validator):
        """Questions about approval/authority emit warning."""
        input_data = PromotionValidationInput(
            pgc_questions=[],
            pgc_answers={},
            generated_document={
                "known_constraints": [],
                "assumptions": [],
                "stakeholder_questions": [
                    {"id": "STK-1", "question": "Who has sign-off authority?"}
                ],
            },
        )
        result = validator.validate(input_data)

        policy_warnings = [w for w in result.warnings if w.check_type == "policy"]
        assert len(policy_warnings) >= 1


class TestGrounding:
    """Tests for Rule 4: Grounding Validation."""

    @pytest.fixture
    def validator(self):
        return PromotionValidator()

    def test_stated_guardrail_valid(self, validator):
        """Guardrail matching intake keywords doesn't warn."""
        input_data = PromotionValidationInput(
            pgc_questions=[],
            pgc_answers={},
            generated_document={
                "known_constraints": [],
                "assumptions": [],
                "mvp_guardrails": [
                    {"id": "GRD-1", "guardrail": "Mobile app must work offline"}
                ],
            },
            intake={
                "description": "Mobile application with offline capability",
            },
        )
        result = validator.validate(input_data)

        grounding_warnings = [
            w for w in result.warnings
            if w.check_type == "grounding" and w.field_id == "GRD-1"
        ]
        assert len(grounding_warnings) == 0

    def test_inferred_guardrail_warns(self, validator):
        """Guardrail not traceable to input warns."""
        input_data = PromotionValidationInput(
            pgc_questions=[
                {"id": "AUTH", "text": "Authentication required?", "priority": "must"}
            ],
            pgc_answers={"AUTH": True},
            generated_document={
                "known_constraints": [],
                "assumptions": [],
                "mvp_guardrails": [
                    {"id": "GRD-1", "guardrail": "Support multi-tenancy isolation"}
                ],
            },
        )
        result = validator.validate(input_data)

        grounding_warnings = [
            w for w in result.warnings
            if w.check_type == "grounding" and w.field_id == "GRD-1"
        ]
        assert len(grounding_warnings) == 1
        assert "inferred" in grounding_warnings[0].message.lower()

    def test_must_answer_grounds_guardrail(self, validator):
        """Guardrail matching must-answer is valid."""
        input_data = PromotionValidationInput(
            pgc_questions=[
                {"id": "OFFLINE", "text": "Must support offline mode?", "priority": "must"}
            ],
            pgc_answers={"OFFLINE": True},
            generated_document={
                "known_constraints": [],
                "assumptions": [],
                "mvp_guardrails": [
                    {"id": "GRD-1", "guardrail": "Application must work in offline mode"}
                ],
            },
        )
        result = validator.validate(input_data)

        grounding_warnings = [
            w for w in result.warnings
            if w.check_type == "grounding" and w.field_id == "GRD-1"
        ]
        assert len(grounding_warnings) == 0


class TestIntegration:
    """Integration tests for full validation flow."""

    @pytest.fixture
    def validator(self):
        return PromotionValidator()

    def test_verification_scenario_from_ws(self, validator):
        """Test scenario from WS-PGC-VALIDATION-001 verification section."""
        # Setup: PGC question with priority="should"
        pgc_questions = [
            {"id": "TRACKING", "text": "progress tracking?", "priority": "should"}
        ]
        pgc_answers = {"TRACKING": True}

        # Document incorrectly promotes to constraint
        document = {
            "known_constraints": [
                {"id": "CNS-1", "constraint": "Must include progress tracking"}
            ],
            "assumptions": [],
        }

        result = validator.validate(PromotionValidationInput(
            pgc_questions=pgc_questions,
            pgc_answers=pgc_answers,
            generated_document=document,
        ))

        assert result.passed is True  # Warnings don't fail
        assert len(result.warnings) >= 1

        promotion_warnings = [w for w in result.warnings if w.check_type == "promotion"]
        assert len(promotion_warnings) == 1
        assert "should" in promotion_warnings[0].message.lower()

    def test_empty_document_passes(self, validator):
        """Empty document with no sections should pass."""
        input_data = PromotionValidationInput(
            pgc_questions=[],
            pgc_answers={},
            generated_document={},
        )
        result = validator.validate(input_data)

        assert result.passed is True
        assert len(result.issues) == 0

    def test_multiple_issues_collected(self, validator):
        """Validator collects issues from all rules."""
        # Use text with > 50% Jaccard similarity for contradiction detection
        # CNS-2: {oauth, authentication, mechanism, required} = 4 keywords
        # ASM-1: {oauth, authentication, mechanism, configured} = 4 keywords
        # Intersection: {oauth, authentication, mechanism} = 3
        # Union: {oauth, authentication, mechanism, required, configured} = 5
        # Jaccard = 3/5 = 0.6 > 0.5 ✓
        input_data = PromotionValidationInput(
            pgc_questions=[
                {"id": "TRACKING", "text": "progress tracking?", "priority": "should"}
            ],
            pgc_answers={"TRACKING": True},
            generated_document={
                "known_constraints": [
                    {"id": "CNS-1", "constraint": "Must include progress tracking"},
                    {"id": "CNS-2", "constraint": "OAuth authentication mechanism required"},
                ],
                "assumptions": [
                    {"id": "ASM-1", "assumption": "OAuth authentication mechanism configured"},
                ],
                "unknowns": [
                    {"id": "UNK-1", "question": "What is the budget?"},
                ],
                "mvp_guardrails": [
                    {"id": "GRD-1", "guardrail": "Multi-tenancy isolation required"},
                ],
            },
        )
        result = validator.validate(input_data)

        # Should have errors (contradiction) and warnings (promotion, policy, grounding)
        assert result.passed is False  # Contradiction is an error
        assert len(result.errors) >= 1
        assert len(result.warnings) >= 1

        # Check we have each type of issue
        check_types = {i.check_type for i in result.issues}
        assert "contradiction" in check_types
        assert "policy" in check_types
