# tests/test_canon/test_validator.py

"""Tests for version validation and comparison."""

import pytest

from workforce.canon.loader import SemanticVersion
from workforce.canon.validator import VersionValidator, VersionComparison


def test_compare_versions_same():
    """Test comparing identical versions."""
    validator = VersionValidator()
    v1 = SemanticVersion(1, 0)
    v2 = SemanticVersion(1, 0)
    
    result = validator.compare_versions(v1, v2)
    assert result == VersionComparison.SAME


def test_compare_versions_upgrade_major():
    """Test upgrade detection (major version)."""
    validator = VersionValidator()
    v1 = SemanticVersion(1, 5)
    v2 = SemanticVersion(2, 0)
    
    result = validator.compare_versions(v1, v2)
    assert result == VersionComparison.UPGRADE


def test_compare_versions_upgrade_minor():
    """Test upgrade detection (minor version)."""
    validator = VersionValidator()
    v1 = SemanticVersion(1, 0)
    v2 = SemanticVersion(1, 1)
    
    result = validator.compare_versions(v1, v2)
    assert result == VersionComparison.UPGRADE


def test_compare_versions_downgrade_major():
    """Test downgrade detection (major version)."""
    validator = VersionValidator()
    v1 = SemanticVersion(2, 0)
    v2 = SemanticVersion(1, 5)
    
    result = validator.compare_versions(v1, v2)
    assert result == VersionComparison.DOWNGRADE


def test_compare_versions_downgrade_minor():
    """Test downgrade detection (minor version)."""
    validator = VersionValidator()
    v1 = SemanticVersion(1, 5)
    v2 = SemanticVersion(1, 3)
    
    result = validator.compare_versions(v1, v2)
    assert result == VersionComparison.DOWNGRADE


def test_validate_llm_version_correct():
    """Test LLM version validation with correct version."""
    validator = VersionValidator()
    llm_response = "I acknowledge PIPELINE_FLOW_VERSION=1.0 as the canon."
    expected = SemanticVersion(1, 0)
    
    result = validator.validate_llm_version(llm_response, expected)
    assert result is True


def test_validate_llm_version_incorrect():
    """Test LLM version validation with incorrect version."""
    validator = VersionValidator()
    llm_response = "I acknowledge PIPELINE_FLOW_VERSION=2.0 as the canon."
    expected = SemanticVersion(1, 0)
    
    result = validator.validate_llm_version(llm_response, expected)
    assert result is False


def test_validate_llm_version_missing():
    """Test LLM version validation when version not reported."""
    validator = VersionValidator()
    llm_response = "I will help you with that task."
    expected = SemanticVersion(1, 0)
    
    result = validator.validate_llm_version(llm_response, expected)
    assert result is False