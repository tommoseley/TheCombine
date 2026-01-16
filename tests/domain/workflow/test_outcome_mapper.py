"""Tests for OutcomeMapper (ADR-039)."""

import pytest

from app.domain.workflow.outcome_mapper import OutcomeMapper, OutcomeMapperError
from app.domain.workflow.plan_models import OutcomeMapping


class TestOutcomeMapper:
    """Tests for OutcomeMapper."""

    @pytest.fixture
    def mappings(self):
        """Standard concierge intake mappings."""
        return [
            OutcomeMapping(gate_outcome="qualified", terminal_outcome="stabilized"),
            OutcomeMapping(gate_outcome="not_ready", terminal_outcome="blocked"),
            OutcomeMapping(gate_outcome="out_of_scope", terminal_outcome="abandoned"),
            OutcomeMapping(gate_outcome="redirect", terminal_outcome="abandoned"),
        ]

    @pytest.fixture
    def mapper(self, mappings):
        """Create OutcomeMapper with standard mappings."""
        return OutcomeMapper(mappings)

    def test_map_qualified(self, mapper):
        """qualified maps to stabilized."""
        assert mapper.map("qualified") == "stabilized"

    def test_map_not_ready(self, mapper):
        """not_ready maps to blocked."""
        assert mapper.map("not_ready") == "blocked"

    def test_map_out_of_scope(self, mapper):
        """out_of_scope maps to abandoned."""
        assert mapper.map("out_of_scope") == "abandoned"

    def test_map_redirect(self, mapper):
        """redirect maps to abandoned."""
        assert mapper.map("redirect") == "abandoned"

    def test_map_unknown_raises(self, mapper):
        """Unknown gate outcome raises OutcomeMapperError."""
        with pytest.raises(OutcomeMapperError) as exc_info:
            mapper.map("unknown")

        assert "unknown" in str(exc_info.value).lower()
        assert "qualified" in str(exc_info.value)  # Shows valid options

    def test_map_optional_returns_none(self, mapper):
        """map_optional returns None for unknown outcome."""
        assert mapper.map_optional("unknown") is None

    def test_map_optional_returns_value(self, mapper):
        """map_optional returns value for known outcome."""
        assert mapper.map_optional("qualified") == "stabilized"

    def test_is_valid_gate_outcome(self, mapper):
        """is_valid_gate_outcome checks validity."""
        assert mapper.is_valid_gate_outcome("qualified") is True
        assert mapper.is_valid_gate_outcome("not_ready") is True
        assert mapper.is_valid_gate_outcome("unknown") is False

    def test_list_gate_outcomes(self, mapper):
        """list_gate_outcomes returns all gate outcomes."""
        outcomes = mapper.list_gate_outcomes()

        assert set(outcomes) == {"qualified", "not_ready", "out_of_scope", "redirect"}

    def test_list_terminal_outcomes(self, mapper):
        """list_terminal_outcomes returns unique terminal outcomes."""
        outcomes = mapper.list_terminal_outcomes()

        # "abandoned" appears twice but should be deduplicated
        assert set(outcomes) == {"stabilized", "blocked", "abandoned"}

    def test_get_mapping_table(self, mapper):
        """get_mapping_table returns full mapping."""
        table = mapper.get_mapping_table()

        assert table["qualified"] == "stabilized"
        assert table["not_ready"] == "blocked"
        assert table["out_of_scope"] == "abandoned"
        assert table["redirect"] == "abandoned"

    def test_deterministic_mapping(self, mapper):
        """Mapping is deterministic (pure function invariant)."""
        # Call multiple times - should always return same result
        for _ in range(100):
            assert mapper.map("qualified") == "stabilized"
            assert mapper.map("not_ready") == "blocked"

    def test_empty_mappings(self):
        """Empty mappings work but all lookups fail."""
        mapper = OutcomeMapper([])

        assert mapper.list_gate_outcomes() == []
        assert mapper.map_optional("anything") is None

        with pytest.raises(OutcomeMapperError):
            mapper.map("anything")
