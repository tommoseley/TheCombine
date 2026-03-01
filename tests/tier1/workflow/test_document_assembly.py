"""Tests for document_assembly pure functions.

Extracted from plan_executor._persist_produced_documents() per WS-CRAP-007.
Tier-1: in-memory, no DB.
"""

import os
import sys
import types

# Stub the workflow package to avoid circular import through __init__.py
if "app.domain.workflow" not in sys.modules:
    _stub = types.ModuleType("app.domain.workflow")
    _stub.__path__ = [os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "app", "domain", "workflow"
    )]
    _stub.__package__ = "app.domain.workflow"
    sys.modules["app.domain.workflow"] = _stub

from app.domain.workflow.document_assembly import (  # noqa: E402
    derive_document_title,
    embed_pgc_clarifications,
    enforce_system_meta,
    promote_pgc_invariants_to_document,
    _default_derive_domain,
    _default_build_statement,
)


# ---------------------------------------------------------------------------
# enforce_system_meta
# ---------------------------------------------------------------------------


class TestEnforceSystemMeta:
    """Tests for enforce_system_meta."""

    def test_adds_meta_if_missing(self):
        doc = {"title": "Test"}
        result, warnings = enforce_system_meta(
            doc, execution_id="exec-1", document_type="project_discovery",
            workflow_id="wf-1", system_created_at="2026-01-15T00:00:00Z",
        )
        assert "meta" in result
        assert result["meta"]["created_at"] == "2026-01-15T00:00:00Z"
        assert result["meta"]["artifact_id"] == "PROJECT_DISCOVERY-exec-1"
        assert result["meta"]["correlation_id"] == "exec-1"
        assert result["meta"]["workflow_id"] == "wf-1"
        assert warnings == []

    def test_does_not_mutate_original(self):
        doc = {"meta": {"created_at": "old"}}
        result, _ = enforce_system_meta(
            doc, execution_id="e", document_type="dt",
            workflow_id="w", system_created_at="new",
        )
        assert doc["meta"]["created_at"] == "old"
        assert result["meta"]["created_at"] == "new"

    def test_warns_on_llm_minted_created_at(self):
        doc = {"meta": {"created_at": "llm-value"}}
        result, warnings = enforce_system_meta(
            doc, execution_id="e", document_type="dt",
            workflow_id="w", system_created_at="sys-value",
        )
        assert len(warnings) == 1
        assert "created_at" in warnings[0]
        assert result["meta"]["created_at"] == "sys-value"

    def test_warns_on_llm_minted_artifact_id(self):
        doc = {"meta": {"artifact_id": "WRONG-ID"}}
        result, warnings = enforce_system_meta(
            doc, execution_id="exec-1", document_type="project_discovery",
            workflow_id="w", system_created_at="2026-01-15T00:00:00Z",
        )
        assert len(warnings) == 1
        assert "artifact_id" in warnings[0]
        assert result["meta"]["artifact_id"] == "PROJECT_DISCOVERY-exec-1"

    def test_no_warning_when_llm_matches_system(self):
        doc = {
            "meta": {
                "created_at": "2026-01-15T00:00:00Z",
                "artifact_id": "DT-e1",
            }
        }
        _, warnings = enforce_system_meta(
            doc, execution_id="e1", document_type="dt",
            workflow_id="w", system_created_at="2026-01-15T00:00:00Z",
        )
        assert warnings == []

    def test_default_created_at_when_not_provided(self):
        doc = {}
        result, _ = enforce_system_meta(
            doc, execution_id="e", document_type="dt", workflow_id="w",
        )
        # Should have a timestamp ending in Z
        assert result["meta"]["created_at"].endswith("Z")


# ---------------------------------------------------------------------------
# derive_document_title
# ---------------------------------------------------------------------------


class TestDeriveDocumentTitle:
    """Tests for derive_document_title."""

    def test_title_from_content(self):
        doc = {"title": "My Project Discovery"}
        assert derive_document_title(doc, "project_discovery") == "My Project Discovery"

    def test_title_from_project_name_field(self):
        doc = {"project_name": "Acme Corp"}
        assert derive_document_title(doc, "project_discovery") == "Acme Corp"

    def test_title_prefers_title_over_project_name(self):
        doc = {"title": "Title", "project_name": "Project"}
        assert derive_document_title(doc, "dt") == "Title"

    def test_fallback_to_db_names(self):
        doc = {}
        assert derive_document_title(
            doc, "project_discovery",
            project_name="Acme", doc_type_display_name="Project Discovery",
        ) == "Acme: Project Discovery"

    def test_fallback_project_name_only(self):
        doc = {}
        assert derive_document_title(doc, "dt", project_name="Acme") == "Acme"

    def test_fallback_doc_type_name_only(self):
        doc = {}
        assert derive_document_title(
            doc, "dt", doc_type_display_name="Discovery",
        ) == "Discovery"

    def test_fallback_to_titlecased_document_type(self):
        doc = {}
        assert derive_document_title(doc, "project_discovery") == "Project Discovery"

    def test_empty_title_falls_through(self):
        doc = {"title": ""}
        assert derive_document_title(doc, "project_discovery") == "Project Discovery"


# ---------------------------------------------------------------------------
# promote_pgc_invariants_to_document
# ---------------------------------------------------------------------------


class TestPromotePgcInvariantsToDocument:
    """Tests for promote_pgc_invariants_to_document."""

    def test_empty_invariants_returns_empty(self):
        doc = {}
        result = promote_pgc_invariants_to_document(doc, [])
        assert result == []
        assert "pgc_invariants" not in doc

    def test_single_invariant_promoted(self):
        doc = {"known_constraints": []}
        invariants = [
            {
                "id": "TARGET_PLATFORM",
                "user_answer_label": "Web application",
                "user_answer": "web",
                "binding_source": "priority",
                "text": "What is the target platform?",
            }
        ]
        result = promote_pgc_invariants_to_document(doc, invariants)
        assert len(result) == 1
        assert result[0]["invariant_id"] == "INV-TARGET_PLATFORM"
        assert result[0]["binding"] is True
        assert result[0]["origin"] == "pgc"
        assert result[0]["user_answer_label"] == "Web application"
        assert doc["pgc_invariants"] == result

    def test_cross_reference_with_known_constraints(self):
        doc = {
            "known_constraints": [
                {"text": "The application must run as a web application"},
            ]
        }
        invariants = [
            {
                "id": "PLATFORM",
                "user_answer_label": "web application",
                "binding_source": "priority",
            }
        ]
        result = promote_pgc_invariants_to_document(doc, invariants)
        assert result[0]["source_constraint_id"] == "CNS-1"

    def test_no_cross_reference_when_no_match(self):
        doc = {"known_constraints": [{"text": "Completely unrelated"}]}
        invariants = [
            {
                "id": "PLATFORM",
                "user_answer_label": "Web app",
                "binding_source": "priority",
            }
        ]
        result = promote_pgc_invariants_to_document(doc, invariants)
        assert result[0]["source_constraint_id"] is None

    def test_custom_derive_domain_fn(self):
        doc = {}
        invariants = [{"id": "X", "user_answer_label": "Y", "binding_source": "p"}]
        result = promote_pgc_invariants_to_document(
            doc, invariants, derive_domain_fn=lambda cid: "custom_domain"
        )
        assert result[0]["domain"] == "custom_domain"

    def test_custom_build_statement_fn(self):
        doc = {}
        invariants = [{"id": "X", "user_answer_label": "Y", "binding_source": "p"}]
        result = promote_pgc_invariants_to_document(
            doc, invariants,
            build_statement_fn=lambda cid, qt, al, bs: f"CUSTOM: {al}",
        )
        assert result[0]["statement"] == "CUSTOM: Y"

    def test_default_domain_derivation(self):
        doc = {}
        invariants = [
            {"id": "TARGET_PLATFORM", "user_answer_label": "Web", "binding_source": "p"},
        ]
        result = promote_pgc_invariants_to_document(doc, invariants)
        assert result[0]["domain"] == "platform"

    def test_multiple_invariants(self):
        doc = {}
        invariants = [
            {"id": "A", "user_answer_label": "X", "binding_source": "p"},
            {"id": "B", "user_answer_label": "Y", "binding_source": "p"},
        ]
        result = promote_pgc_invariants_to_document(doc, invariants)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# embed_pgc_clarifications
# ---------------------------------------------------------------------------


class TestEmbedPgcClarifications:
    """Tests for embed_pgc_clarifications."""

    def test_empty_clarifications(self):
        doc = {}
        result = embed_pgc_clarifications(doc, [])
        assert result == []
        assert "pgc_clarifications" not in doc

    def test_only_resolved_included(self):
        doc = {}
        clarifications = [
            {"id": "Q1", "text": "What?", "resolved": True, "user_answer_label": "Answer"},
            {"id": "Q2", "text": "Why?", "resolved": False},
        ]
        result = embed_pgc_clarifications(doc, clarifications)
        assert len(result) == 1
        assert result[0]["question_id"] == "Q1"
        assert doc["pgc_clarifications"] == result

    def test_embedded_fields(self):
        doc = {}
        clarifications = [
            {
                "id": "Q1",
                "text": "What platform?",
                "why_it_matters": "Determines architecture",
                "resolved": True,
                "user_answer_label": "Web",
                "binding": True,
            }
        ]
        result = embed_pgc_clarifications(doc, clarifications)
        assert result[0]["question_id"] == "Q1"
        assert result[0]["question"] == "What platform?"
        assert result[0]["why_it_matters"] == "Determines architecture"
        assert result[0]["answer"] == "Web"
        assert result[0]["binding"] is True

    def test_falls_back_to_user_answer(self):
        doc = {}
        clarifications = [
            {"id": "Q1", "text": "Q", "resolved": True, "user_answer": 42},
        ]
        result = embed_pgc_clarifications(doc, clarifications)
        assert result[0]["answer"] == "42"

    def test_all_unresolved_skipped(self):
        doc = {}
        clarifications = [
            {"id": "Q1", "text": "Q", "resolved": False},
        ]
        result = embed_pgc_clarifications(doc, clarifications)
        assert result == []
        assert "pgc_clarifications" not in doc


# ---------------------------------------------------------------------------
# _default_derive_domain
# ---------------------------------------------------------------------------


class TestDefaultDeriveDomain:
    """Tests for _default_derive_domain."""

    def test_platform_patterns(self):
        assert _default_derive_domain("TARGET_PLATFORM") == "platform"
        assert _default_derive_domain("PLATFORM_TYPE") == "platform"
        assert _default_derive_domain("TARGET_USER") == "platform"  # TARGET matches first

    def test_user_pattern(self):
        assert _default_derive_domain("PRIMARY_USERS") == "user"

    def test_deployment_patterns(self):
        assert _default_derive_domain("DEPLOYMENT_MODEL") == "deployment"
        assert _default_derive_domain("CONTEXT_TYPE") == "deployment"

    def test_scope_pattern(self):
        assert _default_derive_domain("SCOPE_MATH") == "scope"

    def test_feature_pattern(self):
        assert _default_derive_domain("TRACKING_SYSTEM") == "feature"

    def test_compliance_pattern(self):
        assert _default_derive_domain("STANDARD_COMPLIANCE") == "compliance"
        assert _default_derive_domain("EDUCATIONAL_REQUIREMENTS") == "compliance"

    def test_integration_pattern(self):
        assert _default_derive_domain("SYSTEM_INTEGRATIONS") == "integration"
        assert _default_derive_domain("EXISTING_TOOLS") == "integration"

    def test_unknown_defaults_to_general(self):
        assert _default_derive_domain("CUSTOM_THING") == "general"


# ---------------------------------------------------------------------------
# _default_build_statement
# ---------------------------------------------------------------------------


class TestDefaultBuildStatement:
    """Tests for _default_build_statement."""

    def test_exclusion(self):
        result = _default_build_statement("FEATURE", "Q", "Mobile", "exclusion")
        assert result == "Mobile is explicitly excluded"

    def test_platform(self):
        result = _default_build_statement("TARGET_PLATFORM", "Q", "Web", "priority")
        assert result == "Application must be deployed as Web"

    def test_user(self):
        result = _default_build_statement("PRIMARY_USERS", "Q", "Teachers", "priority")
        assert result == "Primary users are Teachers"

    def test_deployment(self):
        result = _default_build_statement("DEPLOYMENT_MODEL", "Q", "Cloud", "priority")
        assert result == "Deployment context is Cloud"

    def test_scope(self):
        result = _default_build_statement("SCOPE_MATH", "Q", "Advanced", "priority")
        assert result == "Scope includes Advanced"

    def test_tracking(self):
        result = _default_build_statement("TRACKING_TYPE", "Q", "Analytics", "priority")
        assert result == "System will provide Analytics"

    def test_standard(self):
        result = _default_build_statement("STANDARD_REF", "Q", "CCSS", "priority")
        assert result == "Educational standards: CCSS"

    def test_generic_fallback(self):
        result = _default_build_statement("CUSTOM", "Q", "Value", "priority")
        assert result == "CUSTOM: Value"
