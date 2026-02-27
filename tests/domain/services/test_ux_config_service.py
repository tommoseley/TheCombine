"""
Tests for Phase 9: Data-driven UX (WS-DOCUMENT-SYSTEM-CLEANUP)

Tests UX configuration service, status badges, primary actions, and display variants.
"""



# =============================================================================
# TESTS: Default configurations exist
# =============================================================================

class TestDefaultConfigurations:
    """Tests that default configurations are defined."""
    
    def test_default_status_badges_has_all_states(self):
        """Verify DEFAULT_STATUS_BADGES covers all lifecycle states."""
        from app.domain.services.ux_config_service import DEFAULT_STATUS_BADGES
        
        expected_states = ["missing", "generating", "partial", "complete", "stale"]
        for state in expected_states:
            assert state in DEFAULT_STATUS_BADGES
    
    def test_default_status_badges_have_icon_and_color(self):
        """Verify each default badge has icon and color."""
        from app.domain.services.ux_config_service import DEFAULT_STATUS_BADGES
        
        for state, badge in DEFAULT_STATUS_BADGES.items():
            assert "icon" in badge, f"Missing icon for state {state}"
            assert "color" in badge, f"Missing color for state {state}"
    
    def test_generating_badge_has_animation(self):
        """Verify generating state has spin animation."""
        from app.domain.services.ux_config_service import DEFAULT_STATUS_BADGES
        
        assert DEFAULT_STATUS_BADGES["generating"].get("animate") == "spin"
    
    def test_default_primary_action_exists(self):
        """Verify DEFAULT_PRIMARY_ACTION is defined."""
        from app.domain.services.ux_config_service import DEFAULT_PRIMARY_ACTION
        
        assert "label" in DEFAULT_PRIMARY_ACTION
        assert "variant" in DEFAULT_PRIMARY_ACTION
    
    def test_default_display_variants_exist(self):
        """Verify DEFAULT_DISPLAY_VARIANTS are defined."""
        from app.domain.services.ux_config_service import DEFAULT_DISPLAY_VARIANTS
        
        assert "default" in DEFAULT_DISPLAY_VARIANTS
        assert "compact" in DEFAULT_DISPLAY_VARIANTS
        assert "expanded" in DEFAULT_DISPLAY_VARIANTS

# =============================================================================
# TESTS: StatusBadge dataclass
# =============================================================================

class TestStatusBadgeDataclass:
    """Tests for StatusBadge dataclass."""
    
    def test_status_badge_creation(self):
        """Verify StatusBadge can be created."""
        from app.domain.services.ux_config_service import StatusBadge
        
        badge = StatusBadge(icon="check", color="green")
        assert badge.icon == "check"
        assert badge.color == "green"
        assert badge.animate is None
    
    def test_status_badge_with_animation(self):
        """Verify StatusBadge can include animation."""
        from app.domain.services.ux_config_service import StatusBadge
        
        badge = StatusBadge(icon="loader-2", color="blue", animate="spin")
        assert badge.animate == "spin"
    
    def test_status_badge_to_dict(self):
        """Verify StatusBadge.to_dict() works correctly."""
        from app.domain.services.ux_config_service import StatusBadge
        
        badge = StatusBadge(icon="check", color="green", animate="pulse")
        result = badge.to_dict()
        
        assert result["icon"] == "check"
        assert result["color"] == "green"
        assert result["animate"] == "pulse"


# =============================================================================
# TESTS: PrimaryAction dataclass
# =============================================================================

class TestPrimaryActionDataclass:
    """Tests for PrimaryAction dataclass."""
    
    def test_primary_action_creation(self):
        """Verify PrimaryAction can be created."""
        from app.domain.services.ux_config_service import PrimaryAction
        
        action = PrimaryAction(label="Generate")
        assert action.label == "Generate"
        assert action.variant == "primary"
    
    def test_primary_action_to_dict(self):
        """Verify PrimaryAction.to_dict() works correctly."""
        from app.domain.services.ux_config_service import PrimaryAction
        
        action = PrimaryAction(label="Generate", icon="play", variant="primary")
        result = action.to_dict()
        
        assert result["label"] == "Generate"
        assert result["icon"] == "play"
        assert result["variant"] == "primary"


# =============================================================================
# TESTS: UXConfigService - Status Badges
# =============================================================================

class TestUXConfigServiceStatusBadges:
    """Tests for UXConfigService.get_status_badge()."""
    
    def test_get_status_badge_default(self):
        """Verify default badge is returned when no config."""
        from app.domain.services.ux_config_service import UXConfigService
        
        service = UXConfigService()
        badge = service.get_status_badge("complete")
        
        assert badge.icon == "file-check"
        assert badge.color == "green"
    
    def test_get_status_badge_from_doc_type_config(self):
        """Verify badge is read from doc_type_config."""
        from app.domain.services.ux_config_service import UXConfigService
        
        service = UXConfigService()
        config = {
            "status_badges": {
                "complete": {"icon": "check-circle", "color": "emerald"}
            }
        }
        badge = service.get_status_badge("complete", config)
        
        assert badge.icon == "check-circle"
        assert badge.color == "emerald"
    
    def test_get_status_badge_override_takes_priority(self):
        """Verify override takes priority over config."""
        from app.domain.services.ux_config_service import UXConfigService
        
        service = UXConfigService()
        config = {
            "status_badges": {
                "complete": {"icon": "check-circle", "color": "emerald"}
            }
        }
        override = {"icon": "star", "color": "gold"}
        
        badge = service.get_status_badge("complete", config, override)
        
        assert badge.icon == "star"
        assert badge.color == "gold"


# =============================================================================
# TESTS: UXConfigService - Primary Actions
# =============================================================================

class TestUXConfigServicePrimaryActions:
    """Tests for UXConfigService.get_primary_action()."""
    
    def test_get_primary_action_default(self):
        """Verify default action is returned when no config."""
        from app.domain.services.ux_config_service import UXConfigService
        
        service = UXConfigService()
        action = service.get_primary_action()
        
        assert action.label == "Generate"
        assert action.variant == "primary"
    
    def test_get_primary_action_with_doc_name(self):
        """Verify doc_name is included in default label."""
        from app.domain.services.ux_config_service import UXConfigService
        
        service = UXConfigService()
        action = service.get_primary_action(doc_name="Project Discovery")
        
        assert action.label == "Generate Project Discovery"
    
    def test_get_primary_action_from_config(self):
        """Verify action is read from doc_type_config."""
        from app.domain.services.ux_config_service import UXConfigService
        
        service = UXConfigService()
        config = {
            "primary_action": {
                "label": "Begin Research",
                "icon": "compass",
                "variant": "secondary"
            }
        }
        action = service.get_primary_action(config)
        
        assert action.label == "Begin Research"
        assert action.icon == "compass"
        assert action.variant == "secondary"


# =============================================================================
# TESTS: UXConfigService - Display Variants
# =============================================================================

class TestUXConfigServiceDisplayVariants:
    """Tests for UXConfigService display variant methods."""
    
    def test_get_display_variant_default(self):
        """Verify default variant is returned when no config."""
        from app.domain.services.ux_config_service import UXConfigService
        
        service = UXConfigService()
        variant = service.get_display_variant()
        
        assert variant == "default"
    
    def test_get_display_variant_from_section(self):
        """Verify variant is read from section config."""
        from app.domain.services.ux_config_service import UXConfigService
        
        service = UXConfigService()
        section = {"display_variant": "compact"}
        variant = service.get_display_variant(section)
        
        assert variant == "compact"
    
    def test_get_variant_css_class(self):
        """Verify CSS class is generated correctly."""
        from app.domain.services.ux_config_service import UXConfigService
        
        service = UXConfigService()
        
        assert service.get_variant_css_class("compact") == "fragment-compact"
        assert service.get_variant_css_class("expanded") == "fragment-expanded"
        assert service.get_variant_css_class("default") == "fragment-default"


# =============================================================================
# TESTS: UXConfigService - Resolve All Badges
# =============================================================================

class TestUXConfigServiceResolveAllBadges:
    """Tests for UXConfigService.resolve_all_badges()."""
    
    def test_resolve_all_badges_returns_all_states(self):
        """Verify all lifecycle states are included."""
        from app.domain.services.ux_config_service import UXConfigService
        
        service = UXConfigService()
        badges = service.resolve_all_badges()
        
        expected_states = ["missing", "generating", "partial", "complete", "stale"]
        for state in expected_states:
            assert state in badges


# =============================================================================
# TESTS: Convenience Functions
# =============================================================================

class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""
    
    def test_get_status_badge_function(self):
        """Verify get_status_badge convenience function works."""
        from app.domain.services.ux_config_service import get_status_badge
        
        result = get_status_badge("complete")
        
        assert isinstance(result, dict)
        assert result["icon"] == "file-check"
        assert result["color"] == "green"
    
    def test_get_primary_action_function(self):
        """Verify get_primary_action convenience function works."""
        from app.domain.services.ux_config_service import get_primary_action
        
        result = get_primary_action(doc_name="Implementation Plan")

        assert isinstance(result, dict)
        assert "Implementation Plan" in result["label"]
    
    def test_get_variant_css_class_function(self):
        """Verify get_variant_css_class convenience function works."""
        from app.domain.services.ux_config_service import get_variant_css_class
        
        result = get_variant_css_class("compact")
        
        assert result == "fragment-compact"


# =============================================================================
# TESTS: DocumentType model has new columns
# =============================================================================

class TestDocumentTypeModelHasUXColumns:
    """Tests that DocumentType model has Phase 9 columns."""
    
    def test_document_type_has_status_badges_column(self):
        """Verify DocumentType model has status_badges column."""
        from app.api.models.document_type import DocumentType
        
        assert hasattr(DocumentType, 'status_badges')
    
    def test_document_type_has_primary_action_column(self):
        """Verify DocumentType model has primary_action column."""
        from app.api.models.document_type import DocumentType
        
        assert hasattr(DocumentType, 'primary_action')
    
    def test_document_type_has_display_config_column(self):
        """Verify DocumentType model has display_config column."""
        from app.api.models.document_type import DocumentType
        
        assert hasattr(DocumentType, 'display_config')
