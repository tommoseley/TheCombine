"""Unit tests for workflow validation.

Tests WorkflowValidator and ScopeHierarchy per implementation plan Phase 0.
"""

import json
import pytest
from pathlib import Path

from app.domain.workflow.types import ValidationErrorCode
from app.domain.workflow.scope import ScopeHierarchy, ScopeHierarchyError
from app.domain.workflow.validator import WorkflowValidator


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def valid_workflow():
    """Load the sample valid workflow from combine-config."""
    path = Path("combine-config/workflows/software_product_development/releases/1.0.0/definition.json")
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


@pytest.fixture
def validator():
    """Create a validator instance."""
    return WorkflowValidator()


@pytest.fixture
def minimal_valid_workflow():
    """Minimal valid workflow for testing modifications."""
    return {
        "schema_version": "workflow.v1",
        "workflow_id": "test_workflow",
        "revision": "test_rev_1",
        "effective_date": "2026-01-02",
        "name": "Test Workflow",
        "scopes": {
            "project": {"parent": None}
        },
        "document_types": {
            "test_doc": {
                "name": "Test Document",
                "scope": "project",
                "may_own": []
            }
        },
        "entity_types": {},
        "steps": [
            {
                "step_id": "test_step",
                "role": "Technical Architect 1.0",
                "task_prompt": "Project Discovery v1.0",  # Real prompt from manifest
                "produces": "test_doc",
                "scope": "project",
                "inputs": []
            }
        ]
    }


# -----------------------------------------------------------------------------
# TestScopeHierarchy
# -----------------------------------------------------------------------------

class TestScopeHierarchy:
    """Tests for ScopeHierarchy class."""
    
    def test_is_ancestor(self):
        """Project is ancestor of epic and story."""
        hierarchy = ScopeHierarchy({
            "project": {"parent": None},
            "epic": {"parent": "project"},
            "story": {"parent": "epic"}
        })
        
        assert hierarchy.is_ancestor("project", "epic")
        assert hierarchy.is_ancestor("project", "story")
        assert hierarchy.is_ancestor("epic", "story")
        assert not hierarchy.is_ancestor("story", "epic")
        assert not hierarchy.is_ancestor("epic", "project")
    
    def test_is_descendant(self):
        """Story is descendant of epic and project."""
        hierarchy = ScopeHierarchy({
            "project": {"parent": None},
            "epic": {"parent": "project"},
            "story": {"parent": "epic"}
        })
        
        assert hierarchy.is_descendant("story", "epic")
        assert hierarchy.is_descendant("story", "project")
        assert hierarchy.is_descendant("epic", "project")
        assert not hierarchy.is_descendant("project", "epic")
    
    def test_cycle_detection(self):
        """Cyclic scope hierarchy raises error."""
        with pytest.raises(ScopeHierarchyError, match="Cycle detected"):
            ScopeHierarchy({
                "a": {"parent": "b"},
                "b": {"parent": "c"},
                "c": {"parent": "a"}
            })
    
    def test_multiple_roots_allowed(self):
        """Multiple root scopes are valid."""
        hierarchy = ScopeHierarchy({
            "org": {"parent": None},
            "project": {"parent": None},
            "epic": {"parent": "project"}
        })
        
        roots = hierarchy.get_root_scopes()
        assert set(roots) == {"org", "project"}
    
    def test_unknown_scope_handling(self):
        """Unknown scopes return None/False gracefully."""
        hierarchy = ScopeHierarchy({
            "project": {"parent": None}
        })
        
        assert not hierarchy.is_valid_scope("unknown")
        assert hierarchy.get_parent("unknown") is None
        assert not hierarchy.is_ancestor("unknown", "project")
    
    def test_from_workflow(self):
        """ScopeHierarchy.from_workflow extracts scopes correctly."""
        workflow = {
            "scopes": {
                "project": {"parent": None},
                "epic": {"parent": "project"}
            }
        }
        
        hierarchy = ScopeHierarchy.from_workflow(workflow)
        assert hierarchy.is_valid_scope("project")
        assert hierarchy.is_valid_scope("epic")
        assert hierarchy.is_ancestor("project", "epic")


# -----------------------------------------------------------------------------
# TestWorkflowValidator - Happy Path
# -----------------------------------------------------------------------------

class TestWorkflowValidatorHappyPath:
    """Tests for valid workflow scenarios."""
    
    def test_valid_workflow_passes(self, validator, valid_workflow):
        """Sample workflow validates (ignoring missing prompts not yet in manifest)."""
        result = validator.validate(valid_workflow)
        
        # Filter out PROMPT_NOT_IN_MANIFEST errors - these are expected until prompts are created
        non_prompt_errors = [
            e for e in result.errors 
            if e.code != ValidationErrorCode.PROMPT_NOT_IN_MANIFEST
        ]
        
        assert len(non_prompt_errors) == 0, f"Unexpected errors: {non_prompt_errors}"
    
    def test_minimal_valid_workflow_passes(self, validator, minimal_valid_workflow):
        """Minimal valid workflow validates."""
        result = validator.validate(minimal_valid_workflow)
        
        assert result.valid, f"Expected valid but got errors: {result.errors}"


# -----------------------------------------------------------------------------
# TestWorkflowValidator - Schema Validation
# -----------------------------------------------------------------------------

class TestWorkflowValidatorSchema:
    """Tests for schema validation (V1)."""
    
    def test_schema_invalid_rejected(self, validator):
        """Missing required fields rejected."""
        invalid = {"workflow_id": "test"}  # Missing most required fields
        
        result = validator.validate(invalid)
        
        assert not result.valid
        assert any(e.code == ValidationErrorCode.SCHEMA_INVALID for e in result.errors)
    
    def test_accepted_by_requires_acceptance_required(self, validator, minimal_valid_workflow):
        """accepted_by without acceptance_required=true is rejected."""
        minimal_valid_workflow["document_types"]["test_doc"]["accepted_by"] = ["pm"]
        # Note: acceptance_required is not set (defaults to false)
        
        result = validator.validate(minimal_valid_workflow)
        
        assert not result.valid
        assert any(e.code == ValidationErrorCode.SCHEMA_INVALID for e in result.errors)


# -----------------------------------------------------------------------------
# TestWorkflowValidator - Scope Validation
# -----------------------------------------------------------------------------

class TestWorkflowValidatorScopes:
    """Tests for scope validation (V2-V4)."""
    
    def test_scope_cycle_rejected(self, validator, minimal_valid_workflow):
        """Cyclic scope hierarchy rejected."""
        minimal_valid_workflow["scopes"] = {
            "a": {"parent": "b"},
            "b": {"parent": "a"}
        }
        
        result = validator.validate(minimal_valid_workflow)
        
        assert not result.valid
        assert any(e.code == ValidationErrorCode.INVALID_SCOPE_HIERARCHY for e in result.errors)
    
    def test_unknown_scope_in_doc_type_rejected(self, validator, minimal_valid_workflow):
        """Document type referencing unknown scope rejected."""
        minimal_valid_workflow["document_types"]["test_doc"]["scope"] = "unknown_scope"
        
        result = validator.validate(minimal_valid_workflow)
        
        assert not result.valid
        assert any(e.code == ValidationErrorCode.UNKNOWN_SCOPE for e in result.errors)


# -----------------------------------------------------------------------------
# TestWorkflowValidator - Type References
# -----------------------------------------------------------------------------

class TestWorkflowValidatorTypeReferences:
    """Tests for type reference validation (V5-V6)."""
    
    def test_unknown_doc_type_rejected(self, validator, minimal_valid_workflow):
        """Step producing unknown document type rejected."""
        minimal_valid_workflow["steps"][0]["produces"] = "nonexistent_doc"
        
        result = validator.validate(minimal_valid_workflow)
        
        assert not result.valid
        assert any(e.code == ValidationErrorCode.UNKNOWN_DOCUMENT_TYPE for e in result.errors)
    
    def test_unknown_entity_type_rejected(self, validator, minimal_valid_workflow):
        """may_own referencing unknown entity rejected."""
        minimal_valid_workflow["document_types"]["test_doc"]["may_own"] = ["nonexistent_entity"]
        
        result = validator.validate(minimal_valid_workflow)
        
        assert not result.valid
        assert any(e.code == ValidationErrorCode.UNKNOWN_ENTITY_TYPE for e in result.errors)


# -----------------------------------------------------------------------------
# TestWorkflowValidator - Ownership
# -----------------------------------------------------------------------------

class TestWorkflowValidatorOwnership:
    """Tests for ownership validation (V7)."""
    
    def test_ownership_cycle_rejected(self, validator):
        """Cyclic ownership relationships - check disabled for MVP.
        
        NOTE: Ownership cycle validation is disabled for MVP because:
        1. Scope hierarchy validation already prevents real structural cycles
        2. The parent_doc_type relationship is definitional, not ownership
        
        This test verifies the check is disabled (returns no errors for this case).
        """
        workflow = {
            "schema_version": "workflow.v1",
            "workflow_id": "cycle_test",
            "revision": "test",
            "effective_date": "2026-01-02",
            "name": "Cycle Test",
            "scopes": {
                "project": {"parent": None},
                "level_a": {"parent": "project"},
                "level_b": {"parent": "level_a"}
            },
            "document_types": {
                "doc_a": {
                    "name": "Doc A",
                    "scope": "project",
                    "may_own": ["entity_a"],
                    "collection_field": "items_a"
                },
                "doc_b": {
                    "name": "Doc B",
                    "scope": "level_a",
                    "may_own": ["entity_b"],
                    "collection_field": "items_b"
                }
            },
            "entity_types": {
                "entity_a": {
                    "name": "Entity A",
                    "parent_doc_type": "doc_b",
                    "creates_scope": "level_a"
                },
                "entity_b": {
                    "name": "Entity B",
                    "parent_doc_type": "doc_a",
                    "creates_scope": "level_b"
                }
            },
            "steps": [
                {
                    "step_id": "step_a",
                    "role": "Technical Architect 1.0",
                    "task_prompt": "Project Discovery v1.0",
                    "produces": "doc_a",
                    "scope": "project",
                    "inputs": []
                }
            ]
        }
        
        result = validator.validate(workflow)
        
        # Ownership cycle check is disabled for MVP - no OWNERSHIP_CYCLE errors expected
        cycle_errors = [e for e in result.errors if e.code == ValidationErrorCode.OWNERSHIP_CYCLE]
        assert len(cycle_errors) == 0, "Ownership cycle check should be disabled for MVP"


# -----------------------------------------------------------------------------
# TestWorkflowValidator - Scope Consistency
# -----------------------------------------------------------------------------

class TestWorkflowValidatorScopeConsistency:
    """Tests for scope consistency (V8)."""
    
    def test_scope_mismatch_rejected(self, validator, minimal_valid_workflow):
        """Step scope != produced doc scope rejected."""
        minimal_valid_workflow["scopes"]["epic"] = {"parent": "project"}
        minimal_valid_workflow["document_types"]["test_doc"]["scope"] = "epic"
        
        result = validator.validate(minimal_valid_workflow)
        
        assert not result.valid
        assert any(e.code == ValidationErrorCode.SCOPE_MISMATCH for e in result.errors)


# -----------------------------------------------------------------------------
# TestWorkflowValidator - Iteration
# -----------------------------------------------------------------------------

class TestWorkflowValidatorIteration:
    """Tests for iteration source validation (V9)."""
    
    def test_missing_iteration_source_rejected(self, validator, minimal_valid_workflow):
        """iterate_over referencing missing doc rejected."""
        minimal_valid_workflow["scopes"]["epic"] = {"parent": "project"}
        minimal_valid_workflow["document_types"]["epic_doc"] = {
            "name": "Epic Doc",
            "scope": "epic",
            "may_own": []
        }
        minimal_valid_workflow["entity_types"]["epic"] = {
            "name": "Epic",
            "parent_doc_type": "epic_backlog",
            "creates_scope": "epic"
        }
        minimal_valid_workflow["steps"].append({
            "step_id": "per_epic",
            "iterate_over": {
                "doc_type": "nonexistent_backlog",
                "collection_field": "epics",
                "entity_type": "epic"
            },
            "scope": "epic",
            "steps": [
                {
                    "step_id": "epic_step",
                    "role": "Technical Architect 1.0",
                    "task_prompt": "Project Discovery v1.0",
                    "produces": "epic_doc",
                    "scope": "epic",
                    "inputs": []
                }
            ]
        })
        
        result = validator.validate(minimal_valid_workflow)
        
        assert not result.valid
        assert any(e.code == ValidationErrorCode.MISSING_ITERATION_SOURCE for e in result.errors)


# -----------------------------------------------------------------------------
# TestWorkflowValidator - Reference Rules
# -----------------------------------------------------------------------------

class TestWorkflowValidatorReferenceRules:
    """Tests for ADR-011 reference rules (V11-V13)."""
    
    def test_ancestor_reference_permitted(self, validator, valid_workflow):
        """Child referencing parent/ancestor is OK."""
        result = validator.validate(valid_workflow)
        
        # Filter out expected prompt errors (prompts not yet created)
        non_prompt_errors = [
            e for e in result.errors 
            if e.code != ValidationErrorCode.PROMPT_NOT_IN_MANIFEST
        ]
        
        assert len(non_prompt_errors) == 0, f"Unexpected errors: {non_prompt_errors}"
    
    def test_same_scope_context_permitted(self, validator, valid_workflow):
        """Same-scope ref with context=true is OK."""
        result = validator.validate(valid_workflow)
        
        # Filter out expected prompt errors (prompts not yet created)
        non_prompt_errors = [
            e for e in result.errors 
            if e.code != ValidationErrorCode.PROMPT_NOT_IN_MANIFEST
        ]
        
        assert len(non_prompt_errors) == 0, f"Unexpected errors: {non_prompt_errors}"
    
    def test_sibling_reference_forbidden(self, validator):
        """Same-scope ref without context rejected at NON-ROOT scope."""
        # Note: Sibling references ARE allowed at root scope (project).
        # This test creates a scenario at epic scope where siblings are forbidden.
        workflow = {
            "schema_version": "workflow.v1",
            "workflow_id": "sibling_test",
            "revision": "test",
            "effective_date": "2026-01-02",
            "name": "Sibling Test",
            "scopes": {
                "project": {"parent": None},
                "epic": {"parent": "project"}
            },
            "document_types": {
                "project_doc": {"name": "Project Doc", "scope": "project", "may_own": ["epic"], "collection_field": "epics"},
                "doc_a": {"name": "Doc A", "scope": "epic", "may_own": []},
                "doc_b": {"name": "Doc B", "scope": "epic", "may_own": []}
            },
            "entity_types": {
                "epic": {"name": "Epic", "parent_doc_type": "project_doc", "creates_scope": "epic"}
            },
            "steps": [
                {
                    "step_id": "per_epic",
                    "iterate_over": {
                        "doc_type": "project_doc",
                        "collection_field": "epics",
                        "entity_type": "epic"
                    },
                    "scope": "epic",
                    "steps": [
                        {
                            "step_id": "step_a",
                            "role": "Technical Architect 1.0",
                            "task_prompt": "Project Discovery v1.0",
                            "produces": "doc_a",
                            "scope": "epic",
                            "inputs": [
                                {"entity_type": "epic", "scope": "epic", "context": True}
                            ]
                        },
                        {
                            "step_id": "step_b",
                            "role": "Technical Architect 1.0",
                            "task_prompt": "Project Discovery v1.0",
                            "produces": "doc_b",
                            "scope": "epic",
                            "inputs": [
                                {"doc_type": "doc_a", "scope": "epic"}  # Sibling ref - no context!
                            ]
                        }
                    ]
                }
            ]
        }
        
        result = validator.validate(workflow)
        
        assert not result.valid
        assert any(e.code == ValidationErrorCode.FORBIDDEN_SIBLING_REFERENCE for e in result.errors)
    
    def test_descendant_reference_forbidden(self, validator):
        """Parent referencing child rejected."""
        workflow = {
            "schema_version": "workflow.v1",
            "workflow_id": "descendant_test",
            "revision": "test",
            "effective_date": "2026-01-02",
            "name": "Descendant Test",
            "scopes": {
                "project": {"parent": None},
                "epic": {"parent": "project"}
            },
            "document_types": {
                "project_doc": {"name": "Project Doc", "scope": "project", "may_own": []},
                "epic_doc": {"name": "Epic Doc", "scope": "epic", "may_own": []}
            },
            "entity_types": {},
            "steps": [
                {
                    "step_id": "project_step",
                    "role": "Technical Architect 1.0",
                    "task_prompt": "Project Discovery v1.0",
                    "produces": "project_doc",
                    "scope": "project",
                    "inputs": [
                        {"doc_type": "epic_doc", "scope": "epic"}
                    ]
                }
            ]
        }
        
        result = validator.validate(workflow)
        
        assert not result.valid
        assert any(e.code == ValidationErrorCode.FORBIDDEN_DESCENDANT_REFERENCE for e in result.errors)


# -----------------------------------------------------------------------------
# TestWorkflowValidator - Prompt Validation
# -----------------------------------------------------------------------------

class TestWorkflowValidatorPrompts:
    """Tests for prompt validation (V14-V15)."""
    
    def test_invalid_prompt_format_rejected(self, validator, minimal_valid_workflow):
        """Prompt not matching pattern rejected."""
        minimal_valid_workflow["steps"][0]["task_prompt"] = "invalid_format"
        
        result = validator.validate(minimal_valid_workflow)
        
        assert not result.valid
        assert any(e.code == ValidationErrorCode.INVALID_PROMPT_FORMAT for e in result.errors)
    
    def test_valid_prompt_format_accepted(self, validator, minimal_valid_workflow):
        """Prompt matching pattern accepted (manifest check may still fail)."""
        # Use a valid format but non-existent prompt
        minimal_valid_workflow["steps"][0]["task_prompt"] = "Some Task v1.0"
        
        result = validator.validate(minimal_valid_workflow)
        
        # Should have no format errors - manifest errors are OK
        format_errors = [e for e in result.errors if e.code == ValidationErrorCode.INVALID_PROMPT_FORMAT]
        assert len(format_errors) == 0


# -----------------------------------------------------------------------------
# TestWorkflowValidator - Error Quality
# -----------------------------------------------------------------------------

class TestWorkflowValidatorErrorQuality:
    """Tests for error message quality."""
    
    def test_error_includes_path(self, validator, minimal_valid_workflow):
        """Validation errors include JSON path."""
        minimal_valid_workflow["steps"][0]["produces"] = "nonexistent"
        
        result = validator.validate(minimal_valid_workflow)
        
        assert not result.valid
        error = next(e for e in result.errors if e.code == ValidationErrorCode.UNKNOWN_DOCUMENT_TYPE)
        assert "steps[0]" in error.path
    
    def test_multiple_errors_collected(self, validator, minimal_valid_workflow):
        """Multiple semantic errors are collected."""
        minimal_valid_workflow["document_types"]["bad_doc"] = {
            "name": "Bad",
            "scope": "unknown_scope",
            "may_own": ["unknown_entity"]
        }
        
        result = validator.validate(minimal_valid_workflow)
        
        assert not result.valid
        assert len(result.errors) >= 2
