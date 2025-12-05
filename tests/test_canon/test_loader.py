# tests/test_canon/test_loader.py

"""Tests for canon file loading and parsing."""

import pytest
from pathlib import Path

from workforce.canon.loader import CanonLoader, SemanticVersion
from workforce.utils.errors import (
    CanonFileNotFoundError,
    CanonParseError,
    CanonValidationError
)


def test_load_valid_canon(temp_canon_file):
    """Test loading valid canon file."""
    loader = CanonLoader()
    canon = loader.load_canon(temp_canon_file)
    
    assert canon.version == SemanticVersion(1, 0)
    assert "PIPELINE_FLOW_VERSION=1.0" in canon.content
    assert canon.file_path == temp_canon_file


def test_parse_version_first_line():
    """Test version extraction from first line."""
    loader = CanonLoader()
    content = "PIPELINE_FLOW_VERSION=2.5\n# Content"
    
    version = loader._parse_version(content)
    assert version == SemanticVersion(2, 5)


def test_parse_version_with_leading_empty_lines():
    """Test version extraction with leading empty lines."""
    loader = CanonLoader()
    content = "\n\n\nPIPELINE_FLOW_VERSION=1.3\n# Content"
    
    version = loader._parse_version(content)
    assert version == SemanticVersion(1, 3)


def test_parse_version_missing():
    """Test error when version line is not on first non-empty line."""
    loader = CanonLoader()
    content = "# Pipeline Flow\nPIPELINE_FLOW_VERSION=1.0"
    
    with pytest.raises(CanonParseError) as exc_info:
        loader._parse_version(content)
    
    assert "Invalid version format" in str(exc_info.value)


def test_parse_version_invalid_format():
    """Test error when version format is invalid."""
    loader = CanonLoader()
    content = "PIPELINE_FLOW_VERSION=invalid\n# Content"
    
    with pytest.raises(CanonParseError) as exc_info:
        loader._parse_version(content)
    
    assert "Invalid version format" in str(exc_info.value)


def test_parse_version_missing_entirely():
    """Test error when no content at all."""
    loader = CanonLoader()
    content = ""
    
    with pytest.raises(CanonParseError) as exc_info:
        loader._parse_version(content)
    
    assert "No version line found" in str(exc_info.value)


def test_load_nonexistent_file():
    """Test error when file doesn't exist."""
    loader = CanonLoader()
    
    with pytest.raises(CanonFileNotFoundError):
        loader.load_canon(Path("/nonexistent/file.md"))


def test_load_file_too_large(tmp_path):
    """Test error when file exceeds size limit."""
    loader = CanonLoader()
    large_file = tmp_path / "large.md"
    
    # Create file larger than 1MB
    large_file.write_text("X" * (1024 * 1024 + 1))
    
    with pytest.raises(CanonValidationError) as exc_info:
        loader.load_canon(large_file)
    
    assert "too large" in str(exc_info.value)


def test_validate_structure_all_sections_present(temp_canon_file):
    """Test structure validation passes with all sections."""
    loader = CanonLoader()
    canon = loader.load_canon(temp_canon_file)
    
    # Should not raise
    loader._validate_structure(canon.content)


def test_validate_structure_missing_section():
    """Test structure validation fails with missing section."""
    loader = CanonLoader()
    content = """PIPELINE_FLOW_VERSION=1.0
# Pipeline Flow

## Overview
## Phase Sequence
## PM Phase
## Architect Phase
## BA Phase
## Developer Phase
## Commit Phase
"""
    
    with pytest.raises(CanonValidationError) as exc_info:
        loader._validate_structure(content)
    
    assert "Missing required sections" in str(exc_info.value)
    assert "QA Phase" in str(exc_info.value)


def test_validate_structure_case_insensitive():
    """Test structure validation is case-insensitive."""
    loader = CanonLoader()
    content = """PIPELINE_FLOW_VERSION=1.0

## OVERVIEW
## Phase Sequence
## phase definitions
### pm phase
### ARCHITECT PHASE
### Ba Phase
### developer PHASE
### Qa Phase
### COMMIT phase
## error handling & recovery
## behavioral rules (binding)
## canonical summary diagram
## canon enforcement
"""
    
    # Should not raise
    loader._validate_structure(content)