"""Workflow-related API schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ScopeResponse(BaseModel):
    """Scope configuration in response."""
    
    name: str
    parent: Optional[str] = None


class DocumentTypeResponse(BaseModel):
    """Document type configuration in response."""
    
    name: str
    scope: str
    acceptance_required: bool = False
    accepted_by: List[str] = Field(default_factory=list)


class EntityTypeResponse(BaseModel):
    """Entity type configuration in response."""
    
    name: str
    parent_doc_type: str
    creates_scope: str


class StepSummary(BaseModel):
    """Summary of a workflow step."""
    
    step_id: str
    scope: str
    role: Optional[str] = None
    produces: Optional[str] = None
    is_iteration: bool = False


class WorkflowSummary(BaseModel):
    """Brief workflow info for list responses."""
    
    workflow_id: str
    name: str
    description: str
    revision: str
    effective_date: str
    step_count: int


class WorkflowDetail(BaseModel):
    """Full workflow definition response."""
    
    workflow_id: str
    name: str
    description: str
    schema_version: str
    revision: str
    effective_date: str
    scopes: Dict[str, ScopeResponse]
    document_types: Dict[str, DocumentTypeResponse]
    entity_types: Dict[str, EntityTypeResponse]
    steps: List[StepSummary]
    
    model_config = {"json_schema_extra": {
        "example": {
            "workflow_id": "software_product_development",
            "name": "Software Product Development",
            "description": "End-to-end software development workflow",
            "schema_version": "workflow.v1",
            "revision": "1",
            "effective_date": "2026-01-01",
            "scopes": {
                "project": {"name": "project", "parent": None},
                "epic": {"name": "epic", "parent": "project"}
            },
            "document_types": {},
            "entity_types": {},
            "steps": []
        }
    }}


class WorkflowListResponse(BaseModel):
    """Response for list workflows endpoint."""
    
    workflows: List[WorkflowSummary]
    total: int
