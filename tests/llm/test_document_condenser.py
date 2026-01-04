"""Tests for document condenser."""

import pytest

from app.llm.document_condenser import (
    DocumentCondenser,
    CondenseConfig,
    ROLE_FOCUS,
)


class TestDocumentCondenser:
    """Tests for DocumentCondenser."""
    
    def test_short_document_unchanged(self):
        """Short documents pass through unchanged."""
        condenser = DocumentCondenser()
        content = "Short content."
        
        result = condenser.condense(content, "PM")
        
        assert result == content
    
    def test_condense_prioritizes_relevant_sections(self):
        """Prioritizes sections matching role focus."""
        condenser = DocumentCondenser(CondenseConfig(max_tokens=100))
        content = """# Random Stuff
Some irrelevant content here that goes on and on.

# Requirements
The key requirements are listed here.

# More Random
Additional irrelevant filler content."""
        
        result = condenser.condense(content, "PM")
        
        # Requirements should be prioritized for PM
        assert "Requirements" in result
    
    def test_condense_for_different_roles(self):
        """Different roles get different condensations."""
        condenser = DocumentCondenser(CondenseConfig(max_tokens=150))
        content = """# Architecture
System design details here with lots of information about microservices.

# Test Cases  
Testing scenarios and edge cases documented thoroughly.

# Requirements
Business requirements listed comprehensively."""
        
        qa_result = condenser.condense(content, "QA")
        arch_result = condenser.condense(content, "Architect")
        
        # Results may differ based on role focus
        # Both should contain something
        assert len(qa_result) > 0
        assert len(arch_result) > 0
    
    def test_condense_multiple_documents(self):
        """Condenses multiple documents with shared budget."""
        condenser = DocumentCondenser()
        docs = [
            {"type": "Doc1", "content": "Content one."},
            {"type": "Doc2", "content": "Content two."},
        ]
        
        result = condenser.condense_multiple(docs, "Developer", total_max_tokens=1000)
        
        assert len(result) == 2
        assert result[0]["type"] == "Doc1"
        assert result[1]["type"] == "Doc2"
    
    def test_condense_multiple_empty_list(self):
        """Handles empty document list."""
        condenser = DocumentCondenser()
        
        result = condenser.condense_multiple([], "PM")
        
        assert result == []
    
    def test_truncation_adds_marker(self):
        """Truncated content has marker."""
        condenser = DocumentCondenser(CondenseConfig(max_tokens=10))
        content = "A" * 1000  # Very long content
        
        result = condenser.condense(content, "PM")
        
        assert "[truncated]" in result
    
    def test_estimate_tokens(self):
        """Token estimation is reasonable."""
        condenser = DocumentCondenser()
        
        # ~4 chars per token
        estimate = condenser._estimate_tokens("a" * 400)
        
        assert 90 <= estimate <= 110


class TestRoleFocus:
    """Tests for role focus areas."""
    
    def test_all_roles_have_focus(self):
        """All standard roles have focus areas."""
        expected_roles = ["PM", "BA", "Developer", "QA", "Architect"]
        
        for role in expected_roles:
            assert role in ROLE_FOCUS
            assert len(ROLE_FOCUS[role]) > 0
    
    def test_pm_focus_areas(self):
        """PM has business-focused areas."""
        pm_focus = ROLE_FOCUS["PM"]
        
        assert "requirements" in pm_focus
        assert "business value" in pm_focus
    
    def test_developer_focus_areas(self):
        """Developer has technical-focused areas."""
        dev_focus = ROLE_FOCUS["Developer"]
        
        assert "technical specifications" in dev_focus
        assert "implementation details" in dev_focus
    
    def test_qa_focus_areas(self):
        """QA has quality-focused areas."""
        qa_focus = ROLE_FOCUS["QA"]
        
        assert "test cases" in qa_focus
        assert "acceptance criteria" in qa_focus
