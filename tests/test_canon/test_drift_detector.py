# tests/test_canon/test_drift_detector.py

"""Tests for canon version drift detection."""

import pytest
from pathlib import Path

from workforce.canon.loader import SemanticVersion
from workforce.canon.drift_detector import DriftDetector


def test_check_for_drift_no_change(temp_canon_file, monkeypatch):
    """Test drift detection when version unchanged."""
    monkeypatch.setenv("COMBINE_CANON_PATH", str(temp_canon_file))
    
    detector = DriftDetector()
    current_version = SemanticVersion(1, 0)
    
    result = detector.check_for_drift(current_version)
    assert result is None


def test_check_for_drift_version_changed(tmp_path, monkeypatch):
    """Test drift detection when version changed."""
    canon_file = tmp_path / "canon.md"
    canon_file.write_text("PIPELINE_FLOW_VERSION=2.0\n# Updated")
    
    monkeypatch.setenv("COMBINE_CANON_PATH", str(canon_file))
    
    detector = DriftDetector()
    current_version = SemanticVersion(1, 0)
    
    result = detector.check_for_drift(current_version)
    assert result == SemanticVersion(2, 0)


def test_check_for_drift_file_missing(tmp_path, monkeypatch):
    """Test drift detection when file is missing."""
    nonexistent = tmp_path / "missing.md"
    monkeypatch.setenv("COMBINE_CANON_PATH", str(nonexistent))
    
    detector = DriftDetector()
    current_version = SemanticVersion(1, 0)
    
    result = detector.check_for_drift(current_version)
    assert result is None


def test_check_for_drift_invalid_version(tmp_path, monkeypatch):
    """Test drift detection with invalid version in file."""
    canon_file = tmp_path / "canon.md"
    canon_file.write_text("INVALID_VERSION\n# Content")
    
    monkeypatch.setenv("COMBINE_CANON_PATH", str(canon_file))
    
    detector = DriftDetector()
    current_version = SemanticVersion(1, 0)
    
    result = detector.check_for_drift(current_version)
    assert result is None


def test_check_for_drift_upgrade_detected(tmp_path, monkeypatch):
    """Test drift detection for version upgrade."""
    canon_file = tmp_path / "canon.md"
    canon_file.write_text("PIPELINE_FLOW_VERSION=1.5\n# Updated")
    
    monkeypatch.setenv("COMBINE_CANON_PATH", str(canon_file))
    
    detector = DriftDetector()
    current_version = SemanticVersion(1, 0)
    
    result = detector.check_for_drift(current_version)
    assert result == SemanticVersion(1, 5)


def test_check_for_drift_downgrade_detected(tmp_path, monkeypatch):
    """Test drift detection for version downgrade."""
    canon_file = tmp_path / "canon.md"
    canon_file.write_text("PIPELINE_FLOW_VERSION=1.0\n# Reverted")
    
    monkeypatch.setenv("COMBINE_CANON_PATH", str(canon_file))
    
    detector = DriftDetector()
    current_version = SemanticVersion(2, 0)
    
    result = detector.check_for_drift(current_version)
    assert result == SemanticVersion(1, 0)