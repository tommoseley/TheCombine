"""
Unit tests for ConfigurationLoader.

Tests cover config loading, validation, and QA Issue #3
(logging before raising).

Author: D-3 (Junior Developer)
Epic: PIPELINE-175B
"""

import pytest
from unittest.mock import Mock
from app.orchestrator_api.services.configuration_loader import (
    ConfigurationLoader,
    ConfigurationError,
    PhaseConfig
)


class TestConfigurationLoader:
    """Tests for ConfigurationLoader."""
    
    def test_load_active_config(self):
        """Should load and return active configuration."""
        mock_repo = Mock()
        mock_model = Mock()
        mock_model.phase_name = "pm_phase"
        mock_model.role_name = "pm"
        mock_model.artifact_type = "epic"
        mock_model.next_phase = "arch_phase"
        mock_model.is_active = True
        mock_repo.get_by_phase_name.return_value = mock_model
        
        loader = ConfigurationLoader(mock_repo)
        config = loader.load_config("pm_phase")
        
        assert isinstance(config, PhaseConfig)
        assert config.phase_name == "pm_phase"
        assert config.role_name == "pm"
        assert config.artifact_type == "epic"
        assert config.next_phase == "arch_phase"
        assert config.is_active is True
    
    def test_load_config_not_found(self):
        """Should raise ConfigurationError when config not found."""
        mock_repo = Mock()
        mock_repo.get_by_phase_name.return_value = None
        
        loader = ConfigurationLoader(mock_repo)
        
        with pytest.raises(ConfigurationError, match="not found"):
            loader.load_config("nonexistent_phase")
    
    def test_load_inactive_config(self):
        """Should raise ConfigurationError for inactive configuration."""
        mock_repo = Mock()
        mock_model = Mock()
        mock_model.is_active = False
        mock_repo.get_by_phase_name.return_value = mock_model
        
        loader = ConfigurationLoader(mock_repo)
        
        with pytest.raises(ConfigurationError, match="not active"):
            loader.load_config("inactive_phase")
    
    def test_logs_before_raising_not_found(self, caplog):
        """QA Issue #3: Should log ERROR before raising for not found."""
        import logging
        caplog.set_level(logging.ERROR)
        
        mock_repo = Mock()
        mock_repo.get_by_phase_name.return_value = None
        
        loader = ConfigurationLoader(mock_repo)
        
        with pytest.raises(ConfigurationError):
            loader.load_config("missing_phase")
        
        assert "Phase config not found: missing_phase" in caplog.text
    
    def test_logs_before_raising_not_active(self, caplog):
        """QA Issue #3: Should log ERROR before raising for not active."""
        import logging
        caplog.set_level(logging.ERROR)
        
        mock_repo = Mock()
        mock_model = Mock()
        mock_model.is_active = False
        mock_repo.get_by_phase_name.return_value = mock_model
        
        loader = ConfigurationLoader(mock_repo)
        
        with pytest.raises(ConfigurationError):
            loader.load_config("inactive_phase")
        
        assert "Phase config not active: inactive_phase" in caplog.text
    
    def test_repository_exception_handling(self):
        """Should wrap repository exceptions in ConfigurationError."""
        mock_repo = Mock()
        mock_repo.get_by_phase_name.side_effect = Exception("Database error")
        
        loader = ConfigurationLoader(mock_repo)
        
        with pytest.raises(ConfigurationError, match="Failed to load"):
            loader.load_config("pm_phase")
    
    def test_terminal_phase_config(self):
        """Should handle terminal phase with next_phase=None."""
        mock_repo = Mock()
        mock_model = Mock()
        mock_model.phase_name = "commit_phase"
        mock_model.role_name = "commit"
        mock_model.artifact_type = "commit_message"
        mock_model.next_phase = None  # Terminal phase
        mock_model.is_active = True
        mock_repo.get_by_phase_name.return_value = mock_model
        
        loader = ConfigurationLoader(mock_repo)
        config = loader.load_config("commit_phase")
        
        assert config.next_phase is None


# Total: 7 tests