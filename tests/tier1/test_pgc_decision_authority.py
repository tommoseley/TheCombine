"""Tests for PGC decision-parameter authority capture (WS-EVAL-003).

Verifies that PGC context files contain decision-parameter guidance
so algorithmic parameters are captured as durable authority.
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestPDPgcContext:
    """Criterion 1: PD pgc_context contains decision parameter guidance."""

    def _read_pd_context(self):
        path = PROJECT_ROOT / (
            "combine-config/document_types/project_discovery/"
            "releases/1.4.0/prompts/pgc_context.prompt.txt"
        )
        return path.read_text()

    def test_contains_algorithm_guidance(self):
        content = self._read_pd_context()
        assert "algorithm" in content.lower() or "scoring logic" in content.lower()

    def test_contains_threshold_guidance(self):
        content = self._read_pd_context()
        assert "threshold" in content.lower()

    def test_contains_concrete_values_instruction(self):
        """Must instruct to ask for concrete values, not 'configurable'."""
        content = self._read_pd_context()
        assert "concrete" in content.lower() or "not \"configurable\"" in content.lower() or "not 'configurable'" in content.lower()

    def test_references_binding_authority(self):
        """Criterion 3: context mentions binding authority."""
        content = self._read_pd_context()
        assert "authority" in content.lower()


class TestTAPgcContext:
    """Criterion 2: TA pgc_context contains decision parameter guidance."""

    def _read_ta_context(self):
        path = PROJECT_ROOT / (
            "combine-config/prompts/pgc/technical_architecture.v1/"
            "releases/1.0.0/pgc.prompt.txt"
        )
        return path.read_text()

    def test_contains_algorithm_parameters_section(self):
        content = self._read_ta_context()
        assert "decision logic" in content.lower() or "algorithm parameters" in content.lower()

    def test_contains_pin_instruction(self):
        """Must instruct to pin parameters, not leave configurable."""
        content = self._read_ta_context()
        assert "configurable" in content.lower()

    def test_references_binding_authority(self):
        """Criterion 3: context mentions binding authority."""
        content = self._read_ta_context()
        assert "authority" in content.lower()

    def test_contains_scoring_guidance(self):
        content = self._read_ta_context()
        assert "scoring" in content.lower()
