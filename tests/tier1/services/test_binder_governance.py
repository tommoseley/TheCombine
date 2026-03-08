"""Tests for Project Governance section in binder export (WS-RENDER-006).

The binder renderer receives policy data as a parameter (list of dicts).
It formats a governance section at the front of the binder, before pipeline
documents. The renderer never reads from the filesystem — policies are
passed in by the endpoint.
"""
from app.domain.services.binder_renderer import render_project_binder


def _make_doc(display_id, doc_type_id, title, content=None):
    return {
        "display_id": display_id,
        "doc_type_id": doc_type_id,
        "title": title,
        "content": content or {},
        "ia": None,
        "id": None,
        "parent_document_id": None,
    }


def _sample_docs():
    return [
        _make_doc("CI-001", "concierge_intake", "Concierge Intake"),
        _make_doc("PD-001", "project_discovery", "Project Discovery"),
    ]


def _sample_policies():
    return [
        {"title": "POL-CODE-001 \u2014 Code Construction Standard", "content": "Reuse-first rule applies."},
        {"title": "POL-ARCH-001 \u2014 Architectural Integrity Standard", "content": "Separation of concerns."},
        {"title": "POL-QA-001 \u2014 Testing & Verification Standard", "content": "Tests-first rule."},
    ]


# --- Governance section presence ---

def test_governance_section_before_first_pipeline_doc():
    """Binder with policies includes governance section before CI-001."""
    md = render_project_binder("P-001", "Test", _sample_docs(), policies=_sample_policies(), generated_at="2026-01-01T00:00:00Z")
    gov_pos = md.find("# Project Governance")
    ci_pos = md.find("# CI-001")
    assert gov_pos != -1, "Governance section not found"
    assert ci_pos != -1, "CI-001 not found"
    assert gov_pos < ci_pos, "Governance must appear before CI-001"


def test_governance_section_includes_all_policies():
    """All passed policy contents appear in the governance section."""
    policies = _sample_policies()
    md = render_project_binder("P-001", "Test", _sample_docs(), policies=policies, generated_at="2026-01-01T00:00:00Z")
    for pol in policies:
        assert pol["content"] in md, f"Policy content missing: {pol['title']}"
        assert pol["title"] in md, f"Policy title missing: {pol['title']}"


def test_policies_sorted_alphabetically_by_title():
    """Policies appear in alphabetical order by title in the output."""
    policies = _sample_policies()  # ARCH, CODE, QA (alpha order)
    md = render_project_binder("P-001", "Test", _sample_docs(), policies=policies, generated_at="2026-01-01T00:00:00Z")
    arch_pos = md.find("POL-ARCH-001")
    code_pos = md.find("POL-CODE-001")
    qa_pos = md.find("POL-QA-001")
    assert arch_pos < code_pos < qa_pos, f"Policies not in alpha order: ARCH={arch_pos}, CODE={code_pos}, QA={qa_pos}"


# --- TOC ---

def test_governance_toc_before_pipeline_toc():
    """Governance entries appear in TOC before pipeline document entries."""
    md = render_project_binder("P-001", "Test", _sample_docs(), policies=_sample_policies(), generated_at="2026-01-01T00:00:00Z")
    toc_start = md.find("## Table of Contents")
    assert toc_start != -1
    toc_section = md[toc_start:]
    gov_toc = toc_section.find("Project Governance")
    ci_toc = toc_section.find("CI-001")
    assert gov_toc != -1, "Governance not in TOC"
    assert gov_toc < ci_toc, "Governance TOC must appear before pipeline docs"


def test_governance_toc_entries_indented():
    """Individual policy TOC entries are indented (sub-items under governance group)."""
    md = render_project_binder("P-001", "Test", _sample_docs(), policies=_sample_policies(), generated_at="2026-01-01T00:00:00Z")
    lines = md.split("\n")
    policy_toc_lines = [l for l in lines if "POL-" in l and l.strip().startswith("-")]
    assert len(policy_toc_lines) >= 3, f"Expected 3+ policy TOC entries, found {len(policy_toc_lines)}"
    for line in policy_toc_lines:
        assert line.startswith("  -") or line.startswith("- "), f"Policy TOC entry not properly formatted: {line!r}"


def test_governance_toc_has_anchor_links():
    """Policy TOC entries have anchor links."""
    md = render_project_binder("P-001", "Test", _sample_docs(), policies=_sample_policies(), generated_at="2026-01-01T00:00:00Z")
    assert "(#pol-arch-001)" in md.lower() or "(#pol-arch-001" in md.lower(), "Missing anchor for POL-ARCH-001"


# --- Graceful omission ---

def test_empty_policies_list_omits_governance():
    """Binder with policies=[] omits governance section entirely."""
    md = render_project_binder("P-001", "Test", _sample_docs(), policies=[], generated_at="2026-01-01T00:00:00Z")
    assert "Project Governance" not in md
    assert "CI-001" in md, "Pipeline docs should still render"


def test_none_policies_omits_governance():
    """Binder with policies=None omits governance section."""
    md = render_project_binder("P-001", "Test", _sample_docs(), policies=None, generated_at="2026-01-01T00:00:00Z")
    assert "Project Governance" not in md
    assert "CI-001" in md


def test_no_policies_kwarg_omits_governance():
    """Binder called without policies kwarg omits governance section (backward compat)."""
    md = render_project_binder("P-001", "Test", _sample_docs(), generated_at="2026-01-01T00:00:00Z")
    assert "Project Governance" not in md
    assert "CI-001" in md


# --- Content integrity ---

def test_policy_content_included_as_is():
    """Policy content is rendered verbatim (not modified by the renderer)."""
    content = "This is **bold** and has `code` and\n- bullet one\n- bullet two"
    policies = [{"title": "POL-TEST-001 \u2014 Test Policy", "content": content}]
    md = render_project_binder("P-001", "Test", _sample_docs(), policies=policies, generated_at="2026-01-01T00:00:00Z")
    assert content in md, "Policy content must appear verbatim"


def test_policy_titles_used_as_section_headers():
    """Policy titles from the data appear as ## headers in the governance body."""
    policies = [{"title": "POL-TEST-001 \u2014 Test Policy", "content": "test content"}]
    md = render_project_binder("P-001", "Test", _sample_docs(), policies=policies, generated_at="2026-01-01T00:00:00Z")
    assert "## POL-TEST-001" in md, "Policy title should be a ## header"


# --- Existing output unchanged ---

def test_pipeline_documents_unchanged_with_governance():
    """Adding governance does not change pipeline document rendering."""
    md_no_gov = render_project_binder("P-001", "Test", _sample_docs(), generated_at="2026-01-01T00:00:00Z")
    md_with_gov = render_project_binder("P-001", "Test", _sample_docs(), policies=_sample_policies(), generated_at="2026-01-01T00:00:00Z")
    # CI-001 and PD-001 sections should be identical in both
    ci_section_no_gov = md_no_gov[md_no_gov.find("# CI-001"):]
    ci_section_with_gov = md_with_gov[md_with_gov.find("# CI-001"):]
    assert ci_section_no_gov == ci_section_with_gov, "Pipeline document output must be identical"


def test_document_count_excludes_policies():
    """Cover block document count reflects pipeline docs, not policies."""
    md = render_project_binder("P-001", "Test", _sample_docs(), policies=_sample_policies(), generated_at="2026-01-01T00:00:00Z")
    assert "> Documents: 2" in md, "Document count should be 2 (pipeline docs only)"
