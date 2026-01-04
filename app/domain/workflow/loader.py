"""Workflow loader - load, validate, and parse workflow definitions.

Combines validation (Phase 0) with typed model creation.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.domain.workflow.models import (
    DocumentTypeConfig,
    EntityTypeConfig,
    InputReference,
    IterationConfig,
    ScopeConfig,
    Workflow,
    WorkflowStep,
)
from app.domain.workflow.types import ValidationResult
from app.domain.workflow.validator import WorkflowValidator


class WorkflowLoadError(Exception):
    """Raised when workflow loading fails."""
    
    def __init__(self, message: str, errors: Optional[List] = None):
        super().__init__(message)
        self.errors = errors or []


class WorkflowLoader:
    """Load and parse workflow definitions.
    
    Usage:
        loader = WorkflowLoader()
        workflow = loader.load(Path("seed/workflows/my_workflow.v1.json"))
    """
    
    def __init__(self, validator: Optional[WorkflowValidator] = None):
        """Initialize loader with optional custom validator."""
        self.validator = validator or WorkflowValidator()
    
    def load(self, path: Path) -> Workflow:
        """Load workflow from file path.
        
        Args:
            path: Path to workflow JSON file
            
        Returns:
            Parsed and validated Workflow
            
        Raises:
            WorkflowLoadError: If file not found or validation fails
        """
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                raw = json.load(f)
        except FileNotFoundError:
            raise WorkflowLoadError(f"Workflow file not found: {path}")
        except json.JSONDecodeError as e:
            raise WorkflowLoadError(f"Invalid JSON in {path}: {e}")
        
        return self.load_dict(raw)
    
    def load_dict(self, raw: Dict[str, Any]) -> Workflow:
        """Load workflow from dictionary.
        
        Args:
            raw: Raw workflow dict (e.g., from JSON)
            
        Returns:
            Parsed and validated Workflow
            
        Raises:
            WorkflowLoadError: If validation fails
        """
        # Validate first
        result = self.validator.validate(raw)
        if not result.valid:
            # Filter out prompt-not-in-manifest errors for flexibility
            critical_errors = [
                e for e in result.errors 
                if e.code.value != "PROMPT_NOT_IN_MANIFEST"
            ]
            if critical_errors:
                raise WorkflowLoadError(
                    f"Workflow validation failed with {len(critical_errors)} errors",
                    errors=critical_errors
                )
        
        # Parse into typed models
        return self._parse(raw)
    
    def _parse(self, raw: Dict[str, Any]) -> Workflow:
        """Parse raw dict into typed Workflow model."""
        return Workflow(
            schema_version=raw["schema_version"],
            workflow_id=raw["workflow_id"],
            revision=raw["revision"],
            effective_date=raw["effective_date"],
            name=raw["name"],
            description=raw.get("description", ""),
            scopes=self._parse_scopes(raw.get("scopes", {})),
            document_types=self._parse_document_types(raw.get("document_types", {})),
            entity_types=self._parse_entity_types(raw.get("entity_types", {})),
            steps=self._parse_steps(raw.get("steps", [])),
        )
    
    def _parse_scopes(self, raw: Dict[str, Any]) -> Dict[str, ScopeConfig]:
        """Parse scopes section."""
        return {
            scope_id: ScopeConfig(parent=config.get("parent"))
            for scope_id, config in raw.items()
        }
    
    def _parse_document_types(self, raw: Dict[str, Any]) -> Dict[str, DocumentTypeConfig]:
        """Parse document_types section."""
        result = {}
        for doc_id, config in raw.items():
            # Extract known fields, rest goes to extra
            known_fields = {"name", "scope", "may_own", "collection_field", 
                          "acceptance_required", "accepted_by"}
            extra = {k: v for k, v in config.items() if k not in known_fields}
            
            result[doc_id] = DocumentTypeConfig(
                name=config["name"],
                scope=config["scope"],
                may_own=config.get("may_own", []),
                collection_field=config.get("collection_field"),
                acceptance_required=config.get("acceptance_required", False),
                accepted_by=config.get("accepted_by", []),
                extra=extra,
            )
        return result
    
    def _parse_entity_types(self, raw: Dict[str, Any]) -> Dict[str, EntityTypeConfig]:
        """Parse entity_types section."""
        result = {}
        for entity_id, config in raw.items():
            known_fields = {"name", "parent_doc_type", "creates_scope"}
            extra = {k: v for k, v in config.items() if k not in known_fields}
            
            result[entity_id] = EntityTypeConfig(
                name=config["name"],
                parent_doc_type=config["parent_doc_type"],
                creates_scope=config["creates_scope"],
                extra=extra,
            )
        return result
    
    def _parse_steps(self, raw: List[Dict[str, Any]]) -> List[WorkflowStep]:
        """Parse steps array recursively."""
        return [self._parse_step(step) for step in raw]
    
    def _parse_step(self, raw: Dict[str, Any]) -> WorkflowStep:
        """Parse a single step (production or iteration)."""
        # Parse inputs if present
        inputs = [
            self._parse_input_ref(inp) 
            for inp in raw.get("inputs", [])
        ]
        
        # Parse iteration config if present
        iterate_over = None
        if "iterate_over" in raw:
            iter_raw = raw["iterate_over"]
            iterate_over = IterationConfig(
                doc_type=iter_raw["doc_type"],
                collection_field=iter_raw["collection_field"],
                entity_type=iter_raw["entity_type"],
            )
        
        # Parse nested steps if present
        nested_steps = self._parse_steps(raw.get("steps", []))
        
        return WorkflowStep(
            step_id=raw["step_id"],
            scope=raw.get("scope", ""),
            role=raw.get("role"),
            task_prompt=raw.get("task_prompt"),
            produces=raw.get("produces"),
            inputs=inputs,
            iterate_over=iterate_over,
            steps=nested_steps,
        )
    
    def _parse_input_ref(self, raw: Dict[str, Any]) -> InputReference:
        """Parse an input reference."""
        return InputReference(
            scope=raw["scope"],
            doc_type=raw.get("doc_type"),
            entity_type=raw.get("entity_type"),
            required=raw.get("required", True),
            context=raw.get("context", False),
        )