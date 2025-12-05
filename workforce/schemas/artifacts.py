# workforce/schemas/artifacts.py

"""Artifact schemas and data models."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class Epic(BaseModel):
    """Epic artifact from PM Phase."""
    epic_id: str = Field(..., description="Epic identifier")
    title: str
    description: str
    business_value: str
    scope: str
    stories: List[Dict[str, Any]] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    version: str = "1.0"


class ArchitecturalNotes(BaseModel):
    """Architectural Notes from Architect Phase."""
    epic_id: str
    components: List[Dict[str, Any]] = Field(default_factory=list)
    adrs: List[Dict[str, Any]] = Field(default_factory=list)
    integration_points: List[str] = Field(default_factory=list)
    risks: List[Dict[str, Any]] = Field(default_factory=list)
    version: str = "1.0"


class BASpecification(BaseModel):
    """BA Specification from BA Phase."""
    epic_id: str
    quality_models: List[Dict[str, Any]] = Field(default_factory=list)
    test_requirements: Dict[str, int] = Field(default_factory=dict)
    operational_criteria: List[str] = Field(default_factory=list)
    human_approval_rules: List[str] = Field(default_factory=list)
    version: str = "1.0"


class ProposedChangeSet(BaseModel):
    """Proposed Change Set from Developer Phase."""
    epic_id: str
    files_to_create: List[str] = Field(default_factory=list)
    files_to_modify: List[str] = Field(default_factory=list)
    implementation_plan: str
    test_plan: str
    risks: List[Dict[str, Any]] = Field(default_factory=list)
    version: str = "1.0"


class Defect(BaseModel):
    """Individual defect identified by QA."""
    id: str
    severity: str
    category: str
    description: str
    file_path: Optional[str] = None
    suggested_fix: Optional[str] = None


class QAFeedback(BaseModel):
    """Structured feedback from QA Mentor to Dev Mentor."""
    attempt: int
    rejection_reason: str
    defects: List[Defect] = Field(default_factory=list)
    required_fixes: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class QAResult(BaseModel):
    """Result from QA Phase."""
    approved: bool
    verdict: str
    rejection_reason: Optional[str] = None
    defects: List[Defect] = Field(default_factory=list)
    required_fixes: List[str] = Field(default_factory=list)


class CommitResult(BaseModel):
    """Result from Commit Phase."""
    success: bool
    commit_sha: Optional[str] = None
    branch: Optional[str] = None
    error_message: Optional[str] = None


class PipelineResult(BaseModel):
    """Overall pipeline execution result."""
    success: bool
    epic_id: str
    commit: Optional[CommitResult] = None
    failure_reason: Optional[str] = None
    qa_attempts: int = 1
    last_qa_feedback: Optional[QAFeedback] = None
    pipeline_id: Optional[str] = None 