"""Tests for binder corrections audit section (ADR-069, WS-CORRECT-007).

Verifies:
- _render_corrections_summary produces markdown when docs have correction_authority_record_ids
- Returns None when no docs have corrections
"""

import pytest
from uuid import uuid4

from app.api.v1.routers.projects_documents import _render_corrections_summary


class TestRenderCorrectionsSummary:

    def test_returns_none_when_no_corrections(self):
        """No documents have correction_authority_record_ids."""
        binder_docs = [
            {"display_id": "TA-001", "doc_type_id": "technical_architecture", "content": {"meta": {}}},
            {"display_id": "IP-001", "doc_type_id": "implementation_plan", "content": {}},
        ]
        result = _render_corrections_summary(binder_docs)
        assert result is None

    def test_returns_none_when_empty_corrections(self):
        """Documents have correction_authority_record_ids but it's empty."""
        binder_docs = [
            {"display_id": "TA-001", "content": {"meta": {"correction_authority_record_ids": []}}},
        ]
        result = _render_corrections_summary(binder_docs)
        assert result is None

    def test_renders_section_with_corrections(self):
        """Document with correction IDs produces audit section."""
        record_id = str(uuid4())
        binder_docs = [
            {
                "display_id": "TA-001",
                "doc_type_id": "technical_architecture",
                "content": {
                    "meta": {"correction_authority_record_ids": [record_id]},
                },
            },
            {
                "display_id": "IP-001",
                "doc_type_id": "implementation_plan",
                "content": {"meta": {}},
            },
        ]
        result = _render_corrections_summary(binder_docs)
        assert result is not None
        assert "Operator Corrections Audit" in result
        assert "TA-001" in result
        assert "1 correction(s)" in result

    def test_renders_multiple_docs_with_corrections(self):
        """Multiple documents with corrections."""
        binder_docs = [
            {
                "display_id": "TA-001",
                "content": {
                    "meta": {"correction_authority_record_ids": [str(uuid4())]},
                },
            },
            {
                "display_id": "IP-001",
                "content": {
                    "meta": {"correction_authority_record_ids": [str(uuid4()), str(uuid4())]},
                },
            },
        ]
        result = _render_corrections_summary(binder_docs)
        assert "TA-001" in result
        assert "IP-001" in result
        assert "2 correction(s)" in result

    def test_handles_missing_content(self):
        """Gracefully handles docs with no content."""
        binder_docs = [
            {"display_id": "TA-001"},
            {"display_id": "IP-001", "content": None},
        ]
        result = _render_corrections_summary(binder_docs)
        assert result is None
