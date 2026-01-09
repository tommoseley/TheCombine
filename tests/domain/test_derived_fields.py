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


class TestDeriveIntegrationSurface:
    """Tests for derive_integration_surface() frozen rule."""
    
    def test_empty_integrations_returns_none(self):
        """INVARIANT: No integrations → none"""
        from app.domain.services.render_model_builder import derive_integration_surface
        assert derive_integration_surface({}) == "none"
        assert derive_integration_surface({"external_integrations": []}) == "none"
    
    def test_has_integrations_returns_external(self):
        """INVARIANT: Any integrations → external"""
        from app.domain.services.render_model_builder import derive_integration_surface
        obj = {"external_integrations": ["Stripe API", "SendGrid"]}
        assert derive_integration_surface(obj) == "external"
    
    def test_handles_container_form(self):
        """INVARIANT: Container form {"items": [...]} handled"""
        from app.domain.services.render_model_builder import derive_integration_surface
        obj = {"external_integrations": {"items": ["Stripe API"]}}
        assert derive_integration_surface(obj) == "external"
    
    def test_container_empty_items_returns_none(self):
        """INVARIANT: Container with empty items → none"""
        from app.domain.services.render_model_builder import derive_integration_surface
        obj = {"external_integrations": {"items": []}}
        assert derive_integration_surface(obj) == "none"


class TestDeriveComplexityLevel:
    """Tests for derive_complexity_level() frozen rule."""
    
    def test_empty_object_returns_low(self):
        """INVARIANT: Empty object → low"""
        from app.domain.services.render_model_builder import derive_complexity_level
        assert derive_complexity_level({}) == "low"
    
    def test_total_0_to_3_returns_low(self):
        """INVARIANT: 0-3 total → low"""
        from app.domain.services.render_model_builder import derive_complexity_level
        obj = {
            "systems_touched": ["A", "B"],
            "key_interfaces": ["API1"],
        }  # total = 3
        assert derive_complexity_level(obj) == "low"
    
    def test_total_4_to_7_returns_medium(self):
        """INVARIANT: 4-7 total → medium"""
        from app.domain.services.render_model_builder import derive_complexity_level
        obj = {
            "systems_touched": ["A", "B"],
            "key_interfaces": ["API1", "API2"],
            "dependencies": ["D1"],
            "external_integrations": ["E1"],
        }  # total = 6
        assert derive_complexity_level(obj) == "medium"
    
    def test_total_8_plus_returns_high(self):
        """INVARIANT: 8+ total → high"""
        from app.domain.services.render_model_builder import derive_complexity_level
        obj = {
            "systems_touched": ["A", "B", "C"],
            "key_interfaces": ["API1", "API2", "API3"],
            "dependencies": ["D1", "D2"],
            "external_integrations": ["E1"],
        }  # total = 9
        assert derive_complexity_level(obj) == "high"
    
    def test_handles_container_form_dependencies(self):
        """INVARIANT: Container form for dependencies handled"""
        from app.domain.services.render_model_builder import derive_complexity_level
        obj = {
            "systems_touched": ["A", "B"],
            "dependencies": {"items": ["D1", "D2", "D3", "D4", "D5", "D6"]},
        }  # total = 8
        assert derive_complexity_level(obj) == "high"
    
    def test_boundary_3_is_low(self):
        """INVARIANT: Exactly 3 → low"""
        from app.domain.services.render_model_builder import derive_complexity_level
        obj = {"systems_touched": ["A", "B", "C"]}
        assert derive_complexity_level(obj) == "low"
    
    def test_boundary_4_is_medium(self):
        """INVARIANT: Exactly 4 → medium"""
        from app.domain.services.render_model_builder import derive_complexity_level
        obj = {"systems_touched": ["A", "B", "C", "D"]}
        assert derive_complexity_level(obj) == "medium"
    
    def test_boundary_7_is_medium(self):
        """INVARIANT: Exactly 7 → medium"""
        from app.domain.services.render_model_builder import derive_complexity_level
        obj = {"systems_touched": ["A", "B", "C", "D", "E", "F", "G"]}
        assert derive_complexity_level(obj) == "medium"
    
    def test_boundary_8_is_high(self):
        """INVARIANT: Exactly 8 → high"""
        from app.domain.services.render_model_builder import derive_complexity_level
        obj = {"systems_touched": ["A", "B", "C", "D", "E", "F", "G", "H"]}
        assert derive_complexity_level(obj) == "high"
