"""
Tests for invariant_pinner pure functions -- WS-CRAP-004.

Tests extracted pure functions: is_duplicate_constraint,
build_pinned_constraints, pin_invariants.
"""

from app.api.services.mech_handlers.invariant_pinner import (
    is_duplicate_constraint,
    build_pinned_constraints,
    pin_invariants,
)


# =========================================================================
# is_duplicate_constraint
# =========================================================================


class TestIsDuplicateConstraint:
    """Tests for is_duplicate_constraint pure function."""

    def test_string_constraint_matching_keywords(self):
        keywords = {"authentication", "oauth", "security"}
        assert is_duplicate_constraint(
            "Use OAuth authentication for security", keywords, 2
        )

    def test_string_constraint_below_threshold(self):
        keywords = {"authentication", "oauth", "security"}
        assert not is_duplicate_constraint(
            "Use simple passwords", keywords, 2
        )

    def test_string_constraint_exact_threshold(self):
        keywords = {"authentication", "security"}
        assert is_duplicate_constraint(
            "authentication with security", keywords, 2
        )

    def test_dict_constraint_with_text_field(self):
        keywords = {"database", "postgres"}
        constraint = {"text": "Use Postgres database", "source": "user"}
        assert is_duplicate_constraint(constraint, keywords, 2)

    def test_dict_constraint_with_constraint_field(self):
        keywords = {"database", "postgres"}
        constraint = {"constraint": "Use Postgres database"}
        assert is_duplicate_constraint(constraint, keywords, 2)

    def test_dict_constraint_with_description_field(self):
        keywords = {"database", "postgres"}
        constraint = {"description": "Use Postgres database"}
        assert is_duplicate_constraint(constraint, keywords, 2)

    def test_non_string_non_dict_returns_false(self):
        keywords = {"database"}
        assert not is_duplicate_constraint(42, keywords, 1)

    def test_case_insensitive_matching(self):
        keywords = {"database", "postgres"}
        assert is_duplicate_constraint(
            "DATABASE with POSTGRES", keywords, 2
        )

    def test_empty_keywords_no_match(self):
        assert not is_duplicate_constraint("anything", set(), 1)

    def test_threshold_zero_always_matches_string(self):
        assert is_duplicate_constraint("anything", set(), 0)


# =========================================================================
# build_pinned_constraints
# =========================================================================


class TestBuildPinnedConstraints:
    """Tests for build_pinned_constraints pure function."""

    def test_basic_invariant(self):
        invariants = [
            {
                "id": "LANG_CHOICE",
                "user_answer_label": "Python preferred",
                "normalized_text": None,
            }
        ]
        pinned, keywords = build_pinned_constraints(invariants)
        assert len(pinned) == 1
        assert pinned[0]["text"] == "Python preferred"
        assert pinned[0]["source"] == "user_clarification"
        assert pinned[0]["constraint_id"] == "LANG_CHOICE"
        assert pinned[0]["binding"] is True

    def test_normalized_text_preferred(self):
        invariants = [
            {
                "id": "DB_CHOICE",
                "user_answer_label": "PostgreSQL",
                "normalized_text": "Use PostgreSQL for all data storage",
            }
        ]
        pinned, keywords = build_pinned_constraints(invariants)
        assert pinned[0]["text"] == "Use PostgreSQL for all data storage"

    def test_keywords_from_label_and_normalized(self):
        invariants = [
            {
                "id": "DB_CHOICE",
                "user_answer_label": "PostgreSQL only",
                "normalized_text": "Use PostgreSQL database",
            }
        ]
        _, keywords = build_pinned_constraints(invariants)
        # Words > 3 chars from label and normalized
        assert "postgresql" in keywords
        assert "only" in keywords
        assert "database" in keywords

    def test_keywords_from_constraint_id(self):
        invariants = [
            {
                "id": "DATABASE_CHOICE",
                "user_answer_label": "yes",
            }
        ]
        _, keywords = build_pinned_constraints(invariants)
        # Parts of "DATABASE_CHOICE" > 2 chars
        assert "database" in keywords
        assert "choice" in keywords

    def test_skip_empty_answer_label(self):
        invariants = [
            {"id": "SKIP", "user_answer_label": ""},
            {"id": "SKIP2"},
        ]
        pinned, keywords = build_pinned_constraints(invariants)
        assert len(pinned) == 0

    def test_user_answer_fallback(self):
        invariants = [
            {"id": "TEST", "user_answer": "fallback value"},
        ]
        pinned, _ = build_pinned_constraints(invariants)
        assert len(pinned) == 1
        assert pinned[0]["text"] == "fallback value"

    def test_empty_invariants(self):
        pinned, keywords = build_pinned_constraints([])
        assert pinned == []
        assert keywords == set()

    def test_short_words_excluded_from_keywords(self):
        invariants = [
            {"id": "X", "user_answer_label": "do it now"},
        ]
        _, keywords = build_pinned_constraints(invariants)
        # "do", "it", "now" are all <= 3 chars
        assert "do" not in keywords
        assert "it" not in keywords
        assert "now" not in keywords

    def test_missing_id_defaults_to_unknown(self):
        invariants = [
            {"user_answer_label": "some answer"},
        ]
        pinned, _ = build_pinned_constraints(invariants)
        assert pinned[0]["constraint_id"] == "UNKNOWN"


# =========================================================================
# pin_invariants
# =========================================================================


class TestPinInvariants:
    """Tests for pin_invariants pure function."""

    def test_basic_pinning(self):
        doc = {"known_constraints": ["existing constraint"]}
        invariants = [
            {"id": "TEST", "user_answer_label": "pinned constraint"},
        ]
        result = pin_invariants(doc, invariants)
        assert len(result["known_constraints"]) == 2
        assert result["known_constraints"][0]["text"] == "pinned constraint"
        assert result["known_constraints"][1] == "existing constraint"

    def test_does_not_mutate_original(self):
        doc = {"known_constraints": ["original"]}
        invariants = [
            {"id": "TEST", "user_answer_label": "new"},
        ]
        result = pin_invariants(doc, invariants)
        assert doc["known_constraints"] == ["original"]
        assert result is not doc

    def test_deduplication_removes_matching_constraints(self):
        doc = {
            "known_constraints": [
                "Use PostgreSQL database for storage",
                "Deploy on AWS",
            ]
        }
        invariants = [
            {
                "id": "DB_CHOICE",
                "user_answer_label": "PostgreSQL database",
                "normalized_text": "Use PostgreSQL for data storage",
            },
        ]
        result = pin_invariants(doc, invariants, keyword_threshold=2)
        # "Use PostgreSQL database for storage" should be removed as duplicate
        # "Deploy on AWS" should remain
        constraints = result["known_constraints"]
        assert any(c.get("binding") for c in constraints)
        texts = [c if isinstance(c, str) else c.get("text", "") for c in constraints]
        assert "Deploy on AWS" in texts

    def test_deduplication_disabled(self):
        doc = {
            "known_constraints": [
                "Use PostgreSQL database for storage",
            ]
        }
        invariants = [
            {
                "id": "DB_CHOICE",
                "user_answer_label": "PostgreSQL database",
            },
        ]
        result = pin_invariants(doc, invariants, deduplicate=False)
        # Both pinned and original should remain
        assert len(result["known_constraints"]) == 2

    def test_empty_invariants(self):
        doc = {"known_constraints": ["existing"]}
        result = pin_invariants(doc, [])
        # No invariants produce pinned constraints, so just original
        assert result["known_constraints"] == ["existing"]

    def test_missing_known_constraints(self):
        doc = {"other_field": "value"}
        invariants = [
            {"id": "TEST", "user_answer_label": "pinned"},
        ]
        result = pin_invariants(doc, invariants)
        assert len(result["known_constraints"]) == 1
        assert result["known_constraints"][0]["text"] == "pinned"

    def test_non_list_known_constraints_replaced(self):
        doc = {"known_constraints": "not a list"}
        invariants = [
            {"id": "TEST", "user_answer_label": "pinned"},
        ]
        result = pin_invariants(doc, invariants)
        assert isinstance(result["known_constraints"], list)

    def test_custom_keyword_threshold(self):
        doc = {"known_constraints": ["Use database"]}
        invariants = [
            {"id": "DB", "user_answer_label": "database choice"},
        ]
        # With threshold=1, "database" alone triggers dedup
        result = pin_invariants(doc, invariants, keyword_threshold=1)
        non_pinned = [
            c for c in result["known_constraints"]
            if not isinstance(c, dict) or not c.get("binding")
        ]
        assert len(non_pinned) == 0
