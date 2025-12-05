# tests/test_canon/test_version_store.py

"""Tests for version storage."""

import pytest
from datetime import datetime

from workforce.canon.loader import SemanticVersion
from workforce.canon.version_store import VersionStore


def test_update_and_get_version():
    """Test storing and retrieving version."""
    store = VersionStore()
    version = SemanticVersion(1, 0)
    content = "PIPELINE_FLOW_VERSION=1.0\n# Test"
    
    store.update_version(version, content)
    
    assert store.get_current_version() == version
    assert store.get_current_content() == content


def test_is_loaded_initially_false():
    """Test version store initially has no version."""
    store = VersionStore()
    assert store.is_loaded() is False


def test_is_loaded_after_update():
    """Test version store reports loaded after update."""
    store = VersionStore()
    store.update_version(SemanticVersion(1, 0), "content")
    
    assert store.is_loaded() is True


def test_get_loaded_at_timestamp():
    """Test loaded_at timestamp is recorded."""
    store = VersionStore()
    before = datetime.now()
    
    store.update_version(SemanticVersion(1, 0), "content")
    
    after = datetime.now()
    loaded_at = store.get_loaded_at()
    
    assert loaded_at is not None
    assert before <= loaded_at <= after


def test_update_replaces_previous_version():
    """Test updating version replaces previous."""
    store = VersionStore()
    
    store.update_version(SemanticVersion(1, 0), "v1")
    store.update_version(SemanticVersion(2, 0), "v2")
    
    assert store.get_current_version() == SemanticVersion(2, 0)
    assert store.get_current_content() == "v2"