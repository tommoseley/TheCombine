"""Typed workflow models for The Combine.

These dataclasses represent a validated workflow definition.
Created by WorkflowLoader after validation passes.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ScopeConfig:
    """Configuration for a scope level."""
    parent: Optional[str]
    # Extensible - additional fields ignored


@dataclass
class DocumentTypeConfig:
    """Configuration for a document type."""
    name: str
    scope: str
    may_own: List[str] = field(default_factory=list)
    collection_field: Optional[str] = None
    acceptance_required: bool = False
    accepted_by: List[str] = field(default_factory=list)
    # Extensible - additional fields stored here
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityTypeConfig:
    """Configuration for an entity type."""
    name: str
    parent_doc_type: Optional[str]
    creates_scope: str
    # Extensible
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InputReference:
    """Reference to an input document or entity."""
    scope: str
    doc_type: Optional[str] = None
    entity_type: Optional[str] = None
    required: bool = True
    context: bool = False


@dataclass
class IterationConfig:
    """Configuration for iteration over a collection."""
    doc_type: str
    collection_field: str
    entity_type: str


@dataclass
class WorkflowStep:
    """A single step in a workflow.
    
    Can be either:
    - Production step: has role, task_prompt, produces
    - Iteration step: has iterate_over, steps
    """
    step_id: str
    scope: str
    
    # Production step fields
    role: Optional[str] = None
    task_prompt: Optional[str] = None
    produces: Optional[str] = None
    inputs: List[InputReference] = field(default_factory=list)
    
    # Iteration step fields
    iterate_over: Optional[IterationConfig] = None
    steps: List["WorkflowStep"] = field(default_factory=list)
    
    @property
    def is_iteration(self) -> bool:
        """True if this is an iteration step."""
        return self.iterate_over is not None
    
    @property
    def is_production(self) -> bool:
        """True if this is a production step."""
        return self.role is not None and self.task_prompt is not None


@dataclass
class Workflow:
    """A complete workflow definition.
    
    Created by WorkflowLoader after validation passes.
    """
    schema_version: str
    workflow_id: str
    revision: str
    effective_date: str
    name: str
    description: str
    
    scopes: Dict[str, ScopeConfig]
    document_types: Dict[str, DocumentTypeConfig]
    entity_types: Dict[str, EntityTypeConfig]
    steps: List[WorkflowStep]
    
    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Find a step by ID, searching recursively."""
        return self._find_step(step_id, self.steps)
    
    def _find_step(self, step_id: str, steps: List[WorkflowStep]) -> Optional[WorkflowStep]:
        """Recursively search for step."""
        for step in steps:
            if step.step_id == step_id:
                return step
            if step.steps:
                found = self._find_step(step_id, step.steps)
                if found:
                    return found
        return None
    
    def get_production_steps(self) -> List[WorkflowStep]:
        """Get all production steps (flattened from iterations)."""
        result = []
        self._collect_production_steps(self.steps, result)
        return result
    
    def _collect_production_steps(
        self, 
        steps: List[WorkflowStep], 
        result: List[WorkflowStep]
    ) -> None:
        """Recursively collect production steps."""
        for step in steps:
            if step.is_production:
                result.append(step)
            if step.steps:
                self._collect_production_steps(step.steps, result)