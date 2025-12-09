# tests/test_canon/test_integration.py

"""Integration tests for canon version management."""

import pytest
from pathlib import Path

from workforce.canon_version_manager import CanonVersionManager
from workforce.canon.loader import SemanticVersion


def test_load_canon_integration(temp_canon_file, monkeypatch):
    """Test complete canon loading flow."""
    monkeypatch.setenv("COMBINE_CANON_PATH", str(temp_canon_file))
    
    manager = CanonVersionManager()
    manager.load_canon()
    
    # Verify version store updated
    assert manager.version_store.get_current_version() == SemanticVersion(1, 0)
    
    # Verify buffer manager has active buffer
    buffer = manager.buffer_manager.get_current_buffer()
    assert buffer.version == SemanticVersion(1, 0)


def test_reload_canon_with_buffer_swap(tmp_path, monkeypatch):
    """Test canon reload with buffer swap."""
    canon_file = tmp_path / "canon.md"
    canon_file.write_text("""PIPELINE_FLOW_VERSION=1.0
# Pipeline Flow
## Overview
## Phase Sequence
## Phase Definitions
### PM Phase
### Architect Phase
### BA Phase
### Developer Phase
### QA Phase
### Commit Phase
## Error Handling
## Behavioral Rules
## Canonical Summary Diagram
## Canon Enforcement
""")
    
    monkeypatch.setenv("COMBINE_CANON_PATH", str(canon_file))
    
    # Initial load
    manager = CanonVersionManager()
    manager.load_canon()
    
    # Update file
    canon_file.write_text("""PIPELINE_FLOW_VERSION=2.0
# Pipeline Flow
## Overview
## Phase Sequence
## Phase Definitions
### PM Phase
### Architect Phase
### BA Phase
### Developer Phase
### QA Phase
### Commit Phase
## Error Handling
## Behavioral Rules
## Canonical Summary Diagram
## Canon Enforcement
""")
    
    # Reload
    manager.reload_canon_with_buffer_swap()
    
    # Verify new version
    assert manager.version_store.get_current_version() == SemanticVersion(2, 0)
    buffer = manager.buffer_manager.get_current_buffer()
    assert buffer.version == SemanticVersion(2, 0)


def test_version_changed_detection(tmp_path, monkeypatch):
    """Test version change detection."""
    canon_file = tmp_path / "canon.md"
    canon_file.write_text("""PIPELINE_FLOW_VERSION=1.0
# Test
## Overview
## Phase Sequence
## Phase Definitions
### PM Phase
### Architect Phase
### BA Phase
### Developer Phase
### QA Phase
### Commit Phase
## Error Handling
## Behavioral Rules
## Canonical Summary Diagram
## Canon Enforcement
""")
    
    monkeypatch.setenv("COMBINE_CANON_PATH", str(canon_file))
    
    manager = CanonVersionManager()
    manager.load_canon()
    
    # No change initially
    assert manager.version_changed() is False
    
    # Update file
    canon_file.write_text("""PIPELINE_FLOW_VERSION=1.1
# Test
## Overview
## Phase Sequence
## Phase Definitions
### PM Phase
### Architect Phase
### BA Phase
### Developer Phase
### QA Phase
### Commit Phase
## Error Handling
## Behavioral Rules
## Canonical Summary Diagram
## Canon Enforcement
""")
    
    # Should detect change
    assert manager.version_changed() is True


def test_pipeline_isolation_during_reload(tmp_path, monkeypatch):
    """Test pipeline isolation during canon reload."""
    canon_file = tmp_path / "canon.md"
    canon_file.write_text("""PIPELINE_FLOW_VERSION=1.0
# Test
## Overview
## Phase Sequence
## Phase Definitions
### PM Phase
### Architect Phase
### BA Phase
### Developer Phase
### QA Phase
### Commit Phase
## Error Handling
## Behavioral Rules
## Canonical Summary Diagram
## Canon Enforcement
""")
    
    monkeypatch.setenv("COMBINE_CANON_PATH", str(canon_file))
    
    manager = CanonVersionManager()
    manager.load_canon()
    
    # Register pipeline with v1.0
    pipeline_buffer = manager.buffer_manager.register_pipeline_reference("p1")
    assert pipeline_buffer.version == SemanticVersion(1, 0)
    
    # Update and reload
    canon_file.write_text("""PIPELINE_FLOW_VERSION=2.0
# Test
## Overview
## Phase Sequence
## Phase Definitions
### PM Phase
### Architect Phase
### BA Phase
### Developer Phase
### QA Phase
### Commit Phase
## Error Handling
## Behavioral Rules
## Canonical Summary Diagram
## Canon Enforcement
""")
    
    manager.reload_canon_with_buffer_swap()
    
    # Pipeline still has v1.0
    assert pipeline_buffer.version == SemanticVersion(1, 0)
    
    # New pipeline gets v2.0
    new_buffer = manager.buffer_manager.register_pipeline_reference("p2")
    assert new_buffer.version == SemanticVersion(2, 0)


def test_reload_skips_if_version_unchanged(temp_canon_file, monkeypatch):
    """Test reload skips if version hasn't changed."""
    monkeypatch.setenv("COMBINE_CANON_PATH", str(temp_canon_file))
    
    manager = CanonVersionManager()
    manager.load_canon()
    
    initial_buffer = manager.buffer_manager.get_current_buffer()
    
    # Reload with same version
    manager.reload_canon_with_buffer_swap()
    
    # Buffer should be same instance
    current_buffer = manager.buffer_manager.get_current_buffer()
    assert current_buffer is initial_buffer