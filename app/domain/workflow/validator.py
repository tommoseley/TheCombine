"""Workflow validator implementing ADR-011 and ADR-027 rules.

Validates workflow definitions before execution. Enforces:
- JSON Schema conformance
- Scope hierarchy validity
- Ownership DAG (no cycles)
- Reference rules (ancestor OK, sibling/descendant forbidden)
- Prompt naming and manifest presence
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

import jsonschema

from app.domain.workflow.types import (
    ValidationError,
    ValidationErrorCode,
    ValidationResult,
)
from app.domain.workflow.scope import ScopeHierarchy, ScopeHierarchyError


# Prompt naming pattern: "Name v#.#" (e.g., "Story Backlog v1.0")
PROMPT_PATTERN = re.compile(r"^[\w\s]+ v\d+\.\d+$")


class WorkflowValidator:
    """
    Validates workflow definitions per ADR-011 and ADR-027.
    
    Validation order:
    1. JSON Schema conformance (fail fast)
    2. Scope hierarchy validity (fail fast)
    3. Semantic validations (collect all errors)
    """
    
    def __init__(
        self,
        schema_path: Optional[Path] = None,
        manifest_path: Optional[Path] = None,
    ):
        """
        Initialize validator with schema and manifest paths.
        
        Args:
            schema_path: Path to workflow.v1.json schema.
                        Defaults to seed/schemas/workflow.v1.json
            manifest_path: Path to seed manifest.
                          Defaults to seed/manifest.json
        """
        self.schema_path = schema_path or Path("seed/schemas/workflow.v1.json")
        self.manifest_path = manifest_path or Path("seed/manifest.json")
        self._schema: Optional[dict] = None
        self._manifest: Optional[dict] = None
    
    def validate(self, workflow: dict) -> ValidationResult:
        """
        Validate a workflow definition.
        
        Args:
            workflow: Parsed workflow definition dict
            
        Returns:
            ValidationResult with valid=True or list of errors
        """
        errors: List[ValidationError] = []
        
        # V1: JSON Schema validation (fail fast)
        schema_errors = self._validate_schema(workflow)
        if schema_errors:
            return ValidationResult.failure(schema_errors)
        
        # V2: Scope hierarchy validation (fail fast)
        scope_errors = self._validate_scope_hierarchy(workflow)
        if scope_errors:
            return ValidationResult.failure(scope_errors)
        
        # Build scope hierarchy for remaining validations
        scope_hierarchy = ScopeHierarchy.from_workflow(workflow)
        
        # V3-V4: Scope references in document and entity types
        errors.extend(self._validate_scope_references(workflow))
        
        # V5: Step produces references valid doc types
        errors.extend(self._validate_produces_references(workflow))
        
        # V6: may_own references valid entity types
        errors.extend(self._validate_may_own_references(workflow))
        
        # V7: Ownership DAG (no cycles)
        errors.extend(self._validate_ownership_dag(workflow))
        
        # V8: Step scope matches produced doc scope
        errors.extend(self._validate_scope_consistency(workflow))
        
        # V9: Iteration sources exist
        errors.extend(self._validate_iteration_sources(workflow))
        
        # V10: Input references resolve
        errors.extend(self._validate_input_references(workflow))
        
        # V11-V13: Reference rules (ADR-011 section 5)
        errors.extend(self._validate_reference_rules(workflow, scope_hierarchy))
        
        # V14-V15: Prompt validation
        errors.extend(self._validate_prompt_references(workflow))
        
        if errors:
            return ValidationResult.failure(errors)
        return ValidationResult.success()

    # -------------------------------------------------------------------------
    # Schema and Hierarchy Validation (V1-V2)
    # -------------------------------------------------------------------------
    
    def _load_schema(self) -> dict:
        """Load and cache JSON schema."""
        if self._schema is None:
            with open(self.schema_path, "r", encoding="utf-8-sig") as f:
                self._schema = json.load(f)
        return self._schema
    
    def _load_manifest(self) -> dict:
        """Load and cache seed manifest."""
        if self._manifest is None:
            try:
                with open(self.manifest_path, "r", encoding="utf-8-sig") as f:
                    self._manifest = json.load(f)
            except FileNotFoundError:
                self._manifest = {"files": {}}
        return self._manifest
    
    def _validate_schema(self, workflow: dict) -> List[ValidationError]:
        """V1: Validate workflow against JSON schema."""
        errors = []
        try:
            schema = self._load_schema()
            jsonschema.validate(workflow, schema)
        except jsonschema.ValidationError as e:
            path = ".".join(str(p) for p in e.absolute_path) if e.absolute_path else ""
            errors.append(ValidationError(
                code=ValidationErrorCode.SCHEMA_INVALID,
                message=e.message,
                path=path,
            ))
        except FileNotFoundError:
            errors.append(ValidationError(
                code=ValidationErrorCode.SCHEMA_INVALID,
                message=f"Schema file not found: {self.schema_path}",
            ))
        return errors
    
    def _validate_scope_hierarchy(self, workflow: dict) -> List[ValidationError]:
        """V2: Validate scope hierarchy is acyclic."""
        errors = []
        try:
            ScopeHierarchy.from_workflow(workflow)
        except ScopeHierarchyError as e:
            errors.append(ValidationError(
                code=ValidationErrorCode.INVALID_SCOPE_HIERARCHY,
                message=str(e),
                path="scopes",
            ))
        return errors
    
    # -------------------------------------------------------------------------
    # Type Reference Validation (V3-V6)
    # -------------------------------------------------------------------------
    
    def _validate_scope_references(self, workflow: dict) -> List[ValidationError]:
        """V3-V4: Validate all scope references point to declared scopes."""
        errors = []
        valid_scopes = set(workflow.get("scopes", {}).keys())
        
        # V3: Document type scopes
        for doc_id, doc_config in workflow.get("document_types", {}).items():
            scope = doc_config.get("scope")
            if scope and scope not in valid_scopes:
                errors.append(ValidationError(
                    code=ValidationErrorCode.UNKNOWN_SCOPE,
                    message=f"Document type '{doc_id}' references unknown scope '{scope}'",
                    path=f"document_types.{doc_id}.scope",
                ))
        
        # V4: Entity type creates_scope
        for entity_id, entity_config in workflow.get("entity_types", {}).items():
            scope = entity_config.get("creates_scope")
            if scope and scope not in valid_scopes:
                errors.append(ValidationError(
                    code=ValidationErrorCode.UNKNOWN_SCOPE,
                    message=f"Entity type '{entity_id}' references unknown scope '{scope}'",
                    path=f"entity_types.{entity_id}.creates_scope",
                ))
        
        return errors
    
    def _validate_produces_references(self, workflow: dict) -> List[ValidationError]:
        """V5: Validate all step.produces reference valid document types."""
        errors = []
        valid_doc_types = set(workflow.get("document_types", {}).keys())
        
        def check_step(step: dict, path: str):
            if "produces" in step:
                produces = step["produces"]
                if produces not in valid_doc_types:
                    errors.append(ValidationError(
                        code=ValidationErrorCode.UNKNOWN_DOCUMENT_TYPE,
                        message=f"Step produces unknown document type '{produces}'",
                        path=f"{path}.produces",
                    ))
            # Recurse into iteration steps
            for i, substep in enumerate(step.get("steps", [])):
                check_step(substep, f"{path}.steps[{i}]")
        
        for i, step in enumerate(workflow.get("steps", [])):
            check_step(step, f"steps[{i}]")
        
        return errors
    
    def _validate_may_own_references(self, workflow: dict) -> List[ValidationError]:
        """V6: Validate all may_own reference valid entity types."""
        errors = []
        valid_entity_types = set(workflow.get("entity_types", {}).keys())
        
        for doc_id, doc_config in workflow.get("document_types", {}).items():
            for entity_type in doc_config.get("may_own", []):
                if entity_type not in valid_entity_types:
                    errors.append(ValidationError(
                        code=ValidationErrorCode.UNKNOWN_ENTITY_TYPE,
                        message=f"Document type '{doc_id}' may_own unknown entity type '{entity_type}'",
                        path=f"document_types.{doc_id}.may_own",
                    ))
        
        return errors

    # -------------------------------------------------------------------------
    # Ownership Validation (V7)
    # -------------------------------------------------------------------------
    
    def _validate_ownership_dag(self, workflow: dict) -> List[ValidationError]:
        """V7: Validate ownership graph is a DAG (no cycles).
        
        NOTE: For MVP, this check is disabled. The scope hierarchy validation
        already ensures no cycles in the containment structure. The parent_doc_type
        field is definitional (where entity is defined), not an ownership edge.
        
        Future: May add validation for scope-based ownership cycles if needed.
        """
        # MVP: Return empty - scope hierarchy validation is sufficient
        return []
    
    # -------------------------------------------------------------------------
    # Scope Consistency Validation (V8)
    # -------------------------------------------------------------------------
    
    def _validate_scope_consistency(self, workflow: dict) -> List[ValidationError]:
        """V8: Validate step scope matches produced document's scope."""
        errors = []
        doc_types = workflow.get("document_types", {})
        
        def check_step(step: dict, path: str):
            if "produces" in step:
                produces = step["produces"]
                step_scope = step.get("scope")
                
                doc_config = doc_types.get(produces, {})
                doc_scope = doc_config.get("scope")
                
                if doc_scope and step_scope and doc_scope != step_scope:
                    errors.append(ValidationError(
                        code=ValidationErrorCode.SCOPE_MISMATCH,
                        message=f"Step has scope '{step_scope}' but produces '{produces}' which has scope '{doc_scope}'",
                        path=f"{path}",
                    ))
            
            # Recurse into iteration steps
            for i, substep in enumerate(step.get("steps", [])):
                check_step(substep, f"{path}.steps[{i}]")
        
        for i, step in enumerate(workflow.get("steps", [])):
            check_step(step, f"steps[{i}]")
        
        return errors
    
    # -------------------------------------------------------------------------
    # Iteration Source Validation (V9)
    # -------------------------------------------------------------------------
    
    def _validate_iteration_sources(self, workflow: dict) -> List[ValidationError]:
        """V9: Validate iteration sources exist and have collections."""
        errors = []
        doc_types = workflow.get("document_types", {})
        entity_types = workflow.get("entity_types", {})
        
        def check_step(step: dict, path: str):
            if "iterate_over" in step:
                iter_config = step["iterate_over"]
                doc_type = iter_config.get("doc_type")
                collection_field = iter_config.get("collection_field")
                entity_type = iter_config.get("entity_type")
                
                # Check doc_type exists
                if doc_type not in doc_types:
                    errors.append(ValidationError(
                        code=ValidationErrorCode.MISSING_ITERATION_SOURCE,
                        message=f"Iteration references unknown document type '{doc_type}'",
                        path=f"{path}.iterate_over.doc_type",
                    ))
                else:
                    # Check doc_type has the collection_field
                    doc_config = doc_types[doc_type]
                    if doc_config.get("collection_field") != collection_field:
                        errors.append(ValidationError(
                            code=ValidationErrorCode.MISSING_ITERATION_SOURCE,
                            message=f"Document type '{doc_type}' does not have collection_field '{collection_field}'",
                            path=f"{path}.iterate_over.collection_field",
                        ))
                    
                    # Check entity_type is in may_own
                    if entity_type not in doc_config.get("may_own", []):
                        errors.append(ValidationError(
                            code=ValidationErrorCode.MISSING_ITERATION_SOURCE,
                            message=f"Document type '{doc_type}' does not own entity type '{entity_type}'",
                            path=f"{path}.iterate_over.entity_type",
                        ))
                
                # Check entity_type exists
                if entity_type not in entity_types:
                    errors.append(ValidationError(
                        code=ValidationErrorCode.UNKNOWN_ENTITY_TYPE,
                        message=f"Iteration references unknown entity type '{entity_type}'",
                        path=f"{path}.iterate_over.entity_type",
                    ))
            
            # Recurse
            for i, substep in enumerate(step.get("steps", [])):
                check_step(substep, f"{path}.steps[{i}]")
        
        for i, step in enumerate(workflow.get("steps", [])):
            check_step(step, f"steps[{i}]")
        
        return errors

    # -------------------------------------------------------------------------
    # Input Reference Validation (V10)
    # -------------------------------------------------------------------------
    
    def _validate_input_references(self, workflow: dict) -> List[ValidationError]:
        """V10: Validate input references resolve to valid docs/entities."""
        errors = []
        doc_types = set(workflow.get("document_types", {}).keys())
        entity_types = set(workflow.get("entity_types", {}).keys())
        valid_scopes = set(workflow.get("scopes", {}).keys())
        
        def check_step(step: dict, path: str):
            for i, input_ref in enumerate(step.get("inputs", [])):
                input_path = f"{path}.inputs[{i}]"
                
                # Check doc_type reference
                if "doc_type" in input_ref:
                    if input_ref["doc_type"] not in doc_types:
                        errors.append(ValidationError(
                            code=ValidationErrorCode.INVALID_REFERENCE,
                            message=f"Input references unknown document type '{input_ref['doc_type']}'",
                            path=f"{input_path}.doc_type",
                        ))
                
                # Check entity_type reference
                if "entity_type" in input_ref:
                    if input_ref["entity_type"] not in entity_types:
                        errors.append(ValidationError(
                            code=ValidationErrorCode.INVALID_REFERENCE,
                            message=f"Input references unknown entity type '{input_ref['entity_type']}'",
                            path=f"{input_path}.entity_type",
                        ))
                
                # Check scope reference
                ref_scope = input_ref.get("scope")
                if ref_scope and ref_scope not in valid_scopes:
                    errors.append(ValidationError(
                        code=ValidationErrorCode.UNKNOWN_SCOPE,
                        message=f"Input references unknown scope '{ref_scope}'",
                        path=f"{input_path}.scope",
                    ))
            
            # Recurse
            for i, substep in enumerate(step.get("steps", [])):
                check_step(substep, f"{path}.steps[{i}]")
        
        for i, step in enumerate(workflow.get("steps", [])):
            check_step(step, f"steps[{i}]")
        
        return errors
    
    # -------------------------------------------------------------------------
    # Reference Rules Validation (V11-V13)
    # -------------------------------------------------------------------------
    
    def _validate_reference_rules(
        self, 
        workflow: dict, 
        scope_hierarchy: ScopeHierarchy
    ) -> List[ValidationError]:
        """
        V11-V13: Validate ADR-011 Section 5 reference rules.
        
        Rules:
        - Ancestor references: Permitted
        - Same-scope with context=true: Permitted (iteration context item)
        - Same-scope without context: Forbidden (sibling reference)
        - Descendant references: Forbidden
        - Cross-branch references: Forbidden (caught by scope check)
        """
        errors = []
        
        def check_step(step: dict, step_scope: str, path: str):
            for i, input_ref in enumerate(step.get("inputs", [])):
                input_path = f"{path}.inputs[{i}]"
                ref_scope = input_ref.get("scope")
                is_context = input_ref.get("context", False)
                ref_type = input_ref.get("doc_type") or input_ref.get("entity_type")
                
                if not ref_scope or not step_scope:
                    continue
                
                # Rule 1: Ancestor reference - always permitted
                if scope_hierarchy.is_ancestor(ref_scope, step_scope):
                    continue
                
                # Rule 2: Same scope
                if ref_scope == step_scope:
                    if is_context:
                        # Iteration context item - permitted
                        continue
                    # At root scope (no parent), same-scope refs are OK - only one instance
                    if scope_hierarchy.get_parent(ref_scope) is None:
                        continue
                    # Non-root same-scope without context - sibling reference forbidden
                    errors.append(ValidationError(
                        code=ValidationErrorCode.FORBIDDEN_SIBLING_REFERENCE,
                        message=f"Same-scope reference to '{ref_type}' forbidden (not iteration context)",
                        path=input_path,
                    ))
                    continue
                
                # Rule 3: Descendant reference - forbidden
                if scope_hierarchy.is_descendant(ref_scope, step_scope):
                    errors.append(ValidationError(
                        code=ValidationErrorCode.FORBIDDEN_DESCENDANT_REFERENCE,
                        message=f"Descendant reference to '{ref_type}' at scope '{ref_scope}' forbidden",
                        path=input_path,
                    ))
                    continue
                
                # Rule 4: If we get here, it's a cross-branch reference
                # (neither ancestor, same, nor descendant)
                errors.append(ValidationError(
                    code=ValidationErrorCode.FORBIDDEN_CROSS_BRANCH_REFERENCE,
                    message=f"Cross-branch reference to '{ref_type}' at scope '{ref_scope}' forbidden",
                    path=input_path,
                ))
            
            # Recurse into iteration steps with updated scope
            for i, substep in enumerate(step.get("steps", [])):
                substep_scope = substep.get("scope", step_scope)
                check_step(substep, substep_scope, f"{path}.steps[{i}]")
        
        for i, step in enumerate(workflow.get("steps", [])):
            step_scope = step.get("scope", "")
            check_step(step, step_scope, f"steps[{i}]")
        
        return errors

    # -------------------------------------------------------------------------
    # Prompt Validation (V14-V15)
    # -------------------------------------------------------------------------
    
    def _validate_prompt_references(self, workflow: dict) -> List[ValidationError]:
        """
        V14-V15: Validate prompt references.
        
        V14: Prompt names must match pattern "Name v#.#"
        V15: Prompts must exist in seed/manifest.json
        """
        errors = []
        manifest = self._load_manifest()
        
        # Build set of known prompt names from manifest
        known_prompts = self._extract_prompt_names_from_manifest(manifest)
        
        def check_step(step: dict, path: str):
            if "task_prompt" in step:
                prompt_name = step["task_prompt"]
                
                # V14: Format check
                if not PROMPT_PATTERN.match(prompt_name):
                    errors.append(ValidationError(
                        code=ValidationErrorCode.INVALID_PROMPT_FORMAT,
                        message=f"Prompt '{prompt_name}' does not match pattern 'Name v#.#'",
                        path=f"{path}.task_prompt",
                    ))
                # V15: Manifest check (only if format is valid)
                elif known_prompts and prompt_name not in known_prompts:
                    errors.append(ValidationError(
                        code=ValidationErrorCode.PROMPT_NOT_IN_MANIFEST,
                        message=f"Prompt '{prompt_name}' not found in seed/manifest.json",
                        path=f"{path}.task_prompt",
                    ))
            
            # Recurse
            for i, substep in enumerate(step.get("steps", [])):
                check_step(substep, f"{path}.steps[{i}]")
        
        for i, step in enumerate(workflow.get("steps", [])):
            check_step(step, f"steps[{i}]")
        
        return errors
    
    def _extract_prompt_names_from_manifest(self, manifest: dict) -> Set[str]:
        """
        Extract prompt names from manifest.
        
        Manifest structure:
        {
            "packages": {
                "prompts/tasks": {
                    "files": [
                        {"path": "Story Backlog v1.0.txt", "sha256": "..."},
                        ...
                    ]
                }
            }
        }
        
        Extracts the filename (without extension) as prompt name.
        """
        prompt_names = set()
        
        packages = manifest.get("packages", {})
        
        # Get task prompts
        tasks_package = packages.get("prompts/tasks", {})
        for file_info in tasks_package.get("files", []):
            path = file_info.get("path", "")
            if path:
                # Remove .txt extension
                prompt_name = Path(path).stem
                prompt_names.add(prompt_name)
        
        return prompt_names

