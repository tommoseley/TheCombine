"""
Tests for frozen derivation rules in RenderModelBuilder.

These are CONTRACT tests - if they fail, the derivation semantics have changed.
Changes require governance approval per docs/governance/DERIVED_FIELDS.md
"""

import pytest
from app.domain.services.render_model_builder import derive_risk_level


class TestDeriveRiskLevel:
    """Tests for derive_risk_level() frozen rule."""
    
    # =========================================================================
    # FROZEN INVARIANTS - Do not modify without governance approval
    # =========================================================================
    
    def test_empty_list_returns_low(self):
        """INVARIANT: Empty risks → low"""
        assert derive_risk_level([]) == "low"
    
    def test_high_likelihood_returns_high(self):
        """INVARIANT: Any high likelihood → high"""
        risks = [
            {"id": "R-001", "description": "Risk 1", "likelihood": "low"},
            {"id": "R-002", "description": "Risk 2", "likelihood": "high"},
        ]
        assert derive_risk_level(risks) == "high"
    
    def test_medium_likelihood_returns_medium(self):
        """INVARIANT: Medium (no high) → medium"""
        risks = [
            {"id": "R-001", "description": "Risk 1", "likelihood": "low"},
            {"id": "R-002", "description": "Risk 2", "likelihood": "medium"},
        ]
        assert derive_risk_level(risks) == "medium"
    
    def test_all_low_returns_low(self):
        """INVARIANT: All low → low"""
        risks = [
            {"id": "R-001", "description": "Risk 1", "likelihood": "low"},
            {"id": "R-002", "description": "Risk 2", "likelihood": "low"},
        ]
        assert derive_risk_level(risks) == "low"
    
    def test_missing_likelihood_treated_as_low(self):
        """INVARIANT: Missing likelihood field → treated as low"""
        risks = [
            {"id": "R-001", "description": "Risk 1"},  # no likelihood
            {"id": "R-002", "description": "Risk 2"},  # no likelihood
        ]
        assert derive_risk_level(risks) == "low"
    
    def test_mixed_with_missing_likelihood(self):
        """INVARIANT: Missing likelihood doesn't override explicit high"""
        risks = [
            {"id": "R-001", "description": "Risk 1"},  # no likelihood
            {"id": "R-002", "description": "Risk 2", "likelihood": "high"},
        ]
        assert derive_risk_level(risks) == "high"
    
    def test_non_dict_items_skipped(self):
        """INVARIANT: Non-dict items are skipped"""
        risks = [
            "not a dict",
            None,
            {"id": "R-001", "description": "Risk 1", "likelihood": "medium"},
        ]
        assert derive_risk_level(risks) == "medium"
    
    def test_single_high_risk(self):
        """Single high risk → high"""
        risks = [{"id": "R-001", "description": "Risk 1", "likelihood": "high"}]
        assert derive_risk_level(risks) == "high"
    
    def test_single_medium_risk(self):
        """Single medium risk → medium"""
        risks = [{"id": "R-001", "description": "Risk 1", "likelihood": "medium"}]
        assert derive_risk_level(risks) == "medium"
    
    def test_single_low_risk(self):
        """Single low risk → low"""
        risks = [{"id": "R-001", "description": "Risk 1", "likelihood": "low"}]
        assert derive_risk_level(risks) == "low"
