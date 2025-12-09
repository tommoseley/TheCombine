# tests/test_canon/test_prompt_builder.py

"""Tests for system prompt building."""

import pytest
from pathlib import Path
from datetime import datetime

from workforce.canon.loader import SemanticVersion, CanonDocument
from workforce.canon.prompt_builder import PromptBuilder


def test_build_orchestrator_prompt():
    """Test building Orchestrator system prompt."""
    builder = PromptBuilder()
    canon_doc = CanonDocument(
        version=SemanticVersion(1, 0),
        content="PIPELINE_FLOW_VERSION=1.0\n# Test Canon",
        loaded_at=datetime.now(),
        file_path=Path("/test/canon.md")
    )
    
    prompt = builder.build_orchestrator_prompt(canon_doc)
    
    assert "ORCHESTRATOR SYSTEM PROMPT" in prompt
    assert "PIPELINE_FLOW_VERSION=1.0" in prompt
    assert "# Test Canon" in prompt
    assert "[Orchestrator role-specific instructions active]" in prompt


def test_build_mentor_prompt():
    """Test building Mentor system prompt."""
    builder = PromptBuilder()
    canon_doc = CanonDocument(
        version=SemanticVersion(1, 0),
        content="PIPELINE_FLOW_VERSION=1.0\n# Test Canon",
        loaded_at=datetime.now(),
        file_path=Path("/test/canon.md")
    )
    
    prompt = builder.build_mentor_prompt(canon_doc, "PM Mentor")
    
    assert "PM MENTOR SYSTEM PROMPT" in prompt
    assert "PIPELINE_FLOW_VERSION=1.0" in prompt
    assert "# Test Canon" in prompt
    assert "[PM Mentor role-specific instructions active]" in prompt


def test_prompt_includes_full_canon_content():
    """Test that prompt includes complete canon content."""
    builder = PromptBuilder()
    long_content = "PIPELINE_FLOW_VERSION=2.5\n" + ("X" * 5000)
    canon_doc = CanonDocument(
        version=SemanticVersion(2, 5),
        content=long_content,
        loaded_at=datetime.now(),
        file_path=Path("/test/canon.md")
    )
    
    prompt = builder.build_orchestrator_prompt(canon_doc)
    
    assert long_content in prompt


def test_prompt_version_matches_canon():
    """Test that prompt version matches canon document version."""
    builder = PromptBuilder()
    canon_doc = CanonDocument(
        version=SemanticVersion(3, 7),
        content="PIPELINE_FLOW_VERSION=3.7\n# Test",
        loaded_at=datetime.now(),
        file_path=Path("/test/canon.md")
    )
    
    prompt = builder.build_orchestrator_prompt(canon_doc)
    
    assert "PIPELINE_FLOW_VERSION=3.7" in prompt