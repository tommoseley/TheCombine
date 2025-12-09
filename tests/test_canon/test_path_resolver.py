# tests/test_canon/test_path_resolver.py

"""Tests for canon file path resolution."""

import pytest
import os
from pathlib import Path

from workforce.canon.path_resolver import resolve_canon_path
from workforce.utils.errors import CanonFileNotFoundError


def test_resolve_with_override_valid_file(tmp_path, monkeypatch):
    """Test path resolution with valid COMBINE_CANON_PATH."""
    canon_file = tmp_path / "custom_canon.md"
    canon_file.write_text("PIPELINE_FLOW_VERSION=1.0\n# Test", encoding='utf-8')
    
    monkeypatch.setenv("COMBINE_CANON_PATH", str(canon_file))
    
    resolved = resolve_canon_path()
    assert resolved == canon_file.resolve()


def test_resolve_with_override_missing_file(tmp_path, monkeypatch):
    """Test path resolution fails when override file doesn't exist."""
    nonexistent = tmp_path / "missing.md"
    monkeypatch.setenv("COMBINE_CANON_PATH", str(nonexistent))
    
    with pytest.raises(CanonFileNotFoundError) as exc_info:
        resolve_canon_path()
    
    assert "not found at override path" in str(exc_info.value)


def test_resolve_with_override_directory(tmp_path, monkeypatch):
    """Test path resolution fails when override points to directory."""
    directory = tmp_path / "canon_dir"
    directory.mkdir()
    monkeypatch.setenv("COMBINE_CANON_PATH", str(directory))
    
    with pytest.raises(CanonFileNotFoundError) as exc_info:
        resolve_canon_path()
    
    assert "directory" in str(exc_info.value).lower()


def test_resolve_canonical_location(tmp_path, monkeypatch, isolate_config):
    """Test path resolution at canonical location."""
    # Use the workforce_root from isolate_config fixture
    workforce_root = isolate_config["workforce_root"]
    canon_dir = workforce_root / "canon"
    canon_dir.mkdir(parents=True, exist_ok=True)
    
    canon_file = canon_dir / "pipeline_flow.md"
    canon_file.write_text("PIPELINE_FLOW_VERSION=1.0\n# Test", encoding='utf-8')
    
    monkeypatch.delenv("COMBINE_CANON_PATH", raising=False)
    
    resolved = resolve_canon_path()
    assert resolved.name == "pipeline_flow.md"


def test_resolve_fails_when_canonical_missing(tmp_path, monkeypatch, isolate_config):
    """Test path resolution fails when canonical location doesn't exist."""
    monkeypatch.delenv("COMBINE_CANON_PATH", raising=False)
    
    # Remove the canon file if it exists
    workforce_root = isolate_config["workforce_root"]
    canon_file = workforce_root / "canon" / "pipeline_flow.md"
    if canon_file.exists():
        canon_file.unlink()
    
    with pytest.raises(CanonFileNotFoundError) as exc_info:
        resolve_canon_path()
    
    assert "canonical location" in str(exc_info.value).lower()


def test_resolve_empty_override_uses_canonical(tmp_path, monkeypatch, isolate_config):
    """Test that empty string override falls back to canonical."""
    workforce_root = isolate_config["workforce_root"]
    canon_dir = workforce_root / "canon"
    canon_dir.mkdir(parents=True, exist_ok=True)
    
    canon_file = canon_dir / "pipeline_flow.md"
    canon_file.write_text("PIPELINE_FLOW_VERSION=1.0\n# Test", encoding='utf-8')
    
    monkeypatch.setenv("COMBINE_CANON_PATH", "")
    
    resolved = resolve_canon_path()
    assert resolved.name == "pipeline_flow.md"


def test_resolve_cross_platform_paths(tmp_path, monkeypatch):
    """Test path resolution works with pathlib.Path."""
    canon_file = tmp_path / "canon.md"
    canon_file.write_text("PIPELINE_FLOW_VERSION=1.0\n# Test", encoding='utf-8')
    
    monkeypatch.setenv("COMBINE_CANON_PATH", str(canon_file))
    
    resolved = resolve_canon_path()
    assert isinstance(resolved, Path)
    assert resolved.exists()