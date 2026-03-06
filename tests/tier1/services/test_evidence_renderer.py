"""Tier-1 tests for the evidence renderer (WS-RENDER-004).

Tests the evidence header generation that produces YAML frontmatter
with provenance and verification data for rendered documents.
No DB, no HTTP, no side effects.
"""

import hashlib
import json

import pytest

from app.domain.services.evidence_renderer import (
    render_evidence_header,
    compute_source_hash,
    render_evidence_index,
)


# ---------------------------------------------------------------------------
# Evidence header tests
# ---------------------------------------------------------------------------

class TestEvidenceHeader:

    def test_includes_project_id(self):
        header = render_evidence_header(
            project_id="HWCA-001",
            display_id="PD-001",
            doc_type_id="project_discovery",
            content={"summary": "Test"},
        )
        assert "project_id: HWCA-001" in header

    def test_includes_display_id(self):
        header = render_evidence_header(
            project_id="HWCA-001",
            display_id="PD-001",
            doc_type_id="project_discovery",
            content={"summary": "Test"},
        )
        assert "display_id: PD-001" in header

    def test_includes_doc_type_id(self):
        header = render_evidence_header(
            project_id="HWCA-001",
            display_id="PD-001",
            doc_type_id="project_discovery",
            content={"summary": "Test"},
        )
        assert "doc_type_id: project_discovery" in header

    def test_includes_document_version(self):
        header = render_evidence_header(
            project_id="HWCA-001",
            display_id="PD-001",
            doc_type_id="project_discovery",
            content={"summary": "Test"},
            document_version=7,
        )
        assert "document_version: 7" in header

    def test_includes_source_hash(self):
        content = {"summary": "Test"}
        header = render_evidence_header(
            project_id="HWCA-001",
            display_id="PD-001",
            doc_type_id="project_discovery",
            content=content,
        )
        assert "source_hash: sha256:" in header

    def test_includes_renderer_version(self):
        header = render_evidence_header(
            project_id="HWCA-001",
            display_id="PD-001",
            doc_type_id="project_discovery",
            content={"summary": "Test"},
        )
        assert "renderer_version: render-md@1.0.0" in header

    def test_omits_lineage_when_none(self):
        header = render_evidence_header(
            project_id="HWCA-001",
            display_id="PD-001",
            doc_type_id="project_discovery",
            content={"summary": "Test"},
        )
        assert "lineage:" not in header

    def test_includes_lineage_when_provided(self):
        header = render_evidence_header(
            project_id="HWCA-001",
            display_id="PD-001",
            doc_type_id="project_discovery",
            content={"summary": "Test"},
            lineage={"parent_display_id": "IP-001"},
        )
        assert "lineage:" in header
        assert "parent_display_id: IP-001" in header

    def test_includes_ia_verification_status(self):
        header = render_evidence_header(
            project_id="HWCA-001",
            display_id="PD-001",
            doc_type_id="project_discovery",
            content={"summary": "Test"},
            ia_status="PASS",
        )
        assert "ia_verification:" in header
        assert "status: PASS" in header

    def test_wraps_in_yaml_frontmatter_delimiters(self):
        header = render_evidence_header(
            project_id="HWCA-001",
            display_id="PD-001",
            doc_type_id="project_discovery",
            content={"summary": "Test"},
        )
        assert header.startswith("---\n")
        assert header.rstrip().endswith("---")


# ---------------------------------------------------------------------------
# Source hash tests
# ---------------------------------------------------------------------------

class TestSourceHash:

    def test_deterministic(self):
        content = {"summary": "Test", "goals": ["A", "B"]}
        h1 = compute_source_hash(content)
        h2 = compute_source_hash(content)
        assert h1 == h2

    def test_starts_with_sha256_prefix(self):
        h = compute_source_hash({"key": "value"})
        assert h.startswith("sha256:")

    def test_different_content_different_hash(self):
        h1 = compute_source_hash({"a": 1})
        h2 = compute_source_hash({"a": 2})
        assert h1 != h2


# ---------------------------------------------------------------------------
# Evidence index tests
# ---------------------------------------------------------------------------

class TestEvidenceIndex:

    def test_includes_all_documents(self):
        docs = [
            {"display_id": "CI-001", "title": "Intake", "version": 1, "ia_status": "PASS", "source_hash": "sha256:abc"},
            {"display_id": "PD-001", "title": "Discovery", "version": 3, "ia_status": "PASS", "source_hash": "sha256:def"},
        ]
        index = render_evidence_index(docs)
        assert "CI-001" in index
        assert "PD-001" in index

    def test_index_is_gfm_table(self):
        docs = [
            {"display_id": "PD-001", "title": "Discovery", "version": 1, "ia_status": "PASS", "source_hash": "sha256:abc"},
        ]
        index = render_evidence_index(docs)
        assert "| Display ID |" in index
        assert "| --- |" in index
        assert "| PD-001 |" in index

    def test_columns_include_required_fields(self):
        docs = [
            {"display_id": "PD-001", "title": "Discovery", "version": 2, "ia_status": "PASS", "source_hash": "sha256:abc123"},
        ]
        index = render_evidence_index(docs)
        assert "Title" in index
        assert "Version" in index
        assert "IA Status" in index
        assert "Source Hash" in index
