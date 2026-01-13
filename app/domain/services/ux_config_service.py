"""
UX Configuration Service for The Combine.

Phase 9 (WS-DOCUMENT-SYSTEM-CLEANUP): Data-driven UX implementation.

Provides resolution of UX configuration elements with fallback defaults.
All UX elements are tunable without code changes.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# =============================================================================
# DEFAULT CONFIGURATIONS
# =============================================================================

DEFAULT_STATUS_BADGES: Dict[str, Dict[str, Any]] = {
    "missing": {"icon": "file-plus", "color": "gray"},
    "generating": {"icon": "loader-2", "color": "blue", "animate": "spin"},
    "partial": {"icon": "file-clock", "color": "yellow"},
    "complete": {"icon": "file-check", "color": "green"},
    "stale": {"icon": "alert-triangle", "color": "amber"},
}

DEFAULT_PRIMARY_ACTION: Dict[str, Any] = {
    "label": "Generate",
    "icon": None,  # Will use document type icon
    "variant": "primary",
    "tooltip": None,
}

DEFAULT_DISPLAY_VARIANTS = ["default", "compact", "expanded", "card", "table", "minimal"]


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class StatusBadge:
    """Resolved status badge configuration."""
    icon: str
    color: str
    animate: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"icon": self.icon, "color": self.color}
        if self.animate:
            result["animate"] = self.animate
        return result


@dataclass
class PrimaryAction:
    """Resolved primary action (CTA) configuration."""
    label: str
    icon: Optional[str] = None
    variant: str = "primary"
    tooltip: Optional[str] = None
    confirmation: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"label": self.label, "variant": self.variant}
        if self.icon:
            result["icon"] = self.icon
        if self.tooltip:
            result["tooltip"] = self.tooltip
        if self.confirmation:
            result["confirmation"] = self.confirmation
        return result


# =============================================================================
# UX CONFIGURATION SERVICE
# =============================================================================

class UXConfigService:
    """
    Resolves UX configuration with fallback defaults.
    
    Resolution order:
    1. Document-specific override (if provided)
    2. Document type configuration (from DB)
    3. System defaults (hardcoded fallbacks)
    
    Usage:
        service = UXConfigService()
        badge = service.get_status_badge("complete", doc_type_config)
        cta = service.get_primary_action(doc_type_config, doc_name="Project Discovery")
    """
    
    def get_status_badge(
        self,
        lifecycle_state: str,
        doc_type_config: Optional[Dict[str, Any]] = None,
        override: Optional[Dict[str, Any]] = None
    ) -> StatusBadge:
        """
        Get status badge for a lifecycle state.
        
        Args:
            lifecycle_state: One of 'missing', 'generating', 'partial', 'complete', 'stale'
            doc_type_config: Document type configuration (may contain status_badges)
            override: Direct override (highest priority)
        
        Returns:
            StatusBadge with resolved icon, color, and optional animation
        """
        # Priority 1: Direct override
        if override:
            return StatusBadge(
                icon=override.get("icon", "circle"),
                color=override.get("color", "gray"),
                animate=override.get("animate"),
            )
        
        # Priority 2: Document type config
        if doc_type_config and doc_type_config.get("status_badges"):
            badges = doc_type_config["status_badges"]
            if lifecycle_state in badges:
                badge_config = badges[lifecycle_state]
                return StatusBadge(
                    icon=badge_config.get("icon", "circle"),
                    color=badge_config.get("color", "gray"),
                    animate=badge_config.get("animate"),
                )
        
        # Priority 3: System defaults
        default = DEFAULT_STATUS_BADGES.get(lifecycle_state, {"icon": "circle", "color": "gray"})
        return StatusBadge(
            icon=default.get("icon", "circle"),
            color=default.get("color", "gray"),
            animate=default.get("animate"),
        )
    
    def get_primary_action(
        self,
        doc_type_config: Optional[Dict[str, Any]] = None,
        doc_name: Optional[str] = None,
        override: Optional[Dict[str, Any]] = None
    ) -> PrimaryAction:
        """
        Get primary action (CTA) configuration.
        
        Args:
            doc_type_config: Document type configuration (may contain primary_action)
            doc_name: Document name for default label (e.g., "Generate Project Discovery")
            override: Direct override (highest priority)
        
        Returns:
            PrimaryAction with resolved label, icon, variant, etc.
        """
        # Priority 1: Direct override
        if override:
            return PrimaryAction(
                label=override.get("label", "Generate"),
                icon=override.get("icon"),
                variant=override.get("variant", "primary"),
                tooltip=override.get("tooltip"),
                confirmation=override.get("confirmation"),
            )
        
        # Priority 2: Document type config
        if doc_type_config and doc_type_config.get("primary_action"):
            action = doc_type_config["primary_action"]
            return PrimaryAction(
                label=action.get("label", f"Generate {doc_name}" if doc_name else "Generate"),
                icon=action.get("icon") or doc_type_config.get("icon"),
                variant=action.get("variant", "primary"),
                tooltip=action.get("tooltip"),
                confirmation=action.get("confirmation"),
            )
        
        # Priority 3: System defaults with doc_name
        default_label = f"Generate {doc_name}" if doc_name else "Generate"
        default_icon = doc_type_config.get("icon") if doc_type_config else None
        
        return PrimaryAction(
            label=default_label,
            icon=default_icon,
            variant="primary",
        )
    
    def get_display_variant(
        self,
        section_config: Optional[Dict[str, Any]] = None,
        default: str = "default"
    ) -> str:
        """
        Get display variant for a section.
        
        Args:
            section_config: Section configuration (may contain display_variant)
            default: Default variant if not specified
        
        Returns:
            Display variant string (default, compact, expanded, card, table, minimal)
        """
        if section_config and section_config.get("display_variant"):
            variant = section_config["display_variant"]
            if variant in DEFAULT_DISPLAY_VARIANTS:
                return variant
            logger.warning(f"Unknown display variant '{variant}', using '{default}'")
        return default
    
    def get_variant_css_class(self, variant: str) -> str:
        """
        Get CSS class for a display variant.
        
        Args:
            variant: Display variant string
        
        Returns:
            CSS class name (e.g., 'fragment-compact')
        """
        if variant in DEFAULT_DISPLAY_VARIANTS:
            return f"fragment-{variant}"
        return "fragment-default"
    
    def resolve_all_badges(
        self,
        doc_type_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, StatusBadge]:
        """
        Resolve all status badges for a document type.
        
        Args:
            doc_type_config: Document type configuration
        
        Returns:
            Dict mapping lifecycle state to StatusBadge
        """
        states = ["missing", "generating", "partial", "complete", "stale"]
        return {
            state: self.get_status_badge(state, doc_type_config)
            for state in states
        }


# Singleton instance for convenience
ux_config_service = UXConfigService()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_status_badge(
    lifecycle_state: str,
    doc_type_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Convenience function to get status badge as dict."""
    return ux_config_service.get_status_badge(lifecycle_state, doc_type_config).to_dict()


def get_primary_action(
    doc_type_config: Optional[Dict[str, Any]] = None,
    doc_name: Optional[str] = None
) -> Dict[str, Any]:
    """Convenience function to get primary action as dict."""
    return ux_config_service.get_primary_action(doc_type_config, doc_name).to_dict()


def get_variant_css_class(variant: str) -> str:
    """Convenience function to get CSS class for variant."""
    return ux_config_service.get_variant_css_class(variant)