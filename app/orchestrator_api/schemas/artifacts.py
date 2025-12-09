"""Pydantic schemas for pipeline artifacts."""
from typing import List, Optional

from pydantic import BaseModel, Field


class Story(BaseModel):
    """User story within an epic."""

    id: str = Field(pattern=r"^STORY-\d+$")
    title: str = Field(max_length=100)
    user_story: str
    acceptance_criteria: List[str]
    estimate_hours: int = Field(gt=0, le=40)
    priority: str = Field(pattern=r"^(critical|high|medium|low)$")


class EpicSpec(BaseModel):
    """PM phase output schema."""

    epic_id: str
    title: str = Field(max_length=100)
    goal: str = Field(max_length=500)
    success_criteria: List[str] = Field(min_length=1)
    stories: List[Story] = Field(min_length=1)
    out_of_scope: List[str] = []
    risks: List[str] = []
    total_estimate_hours: int = Field(gt=0)


class MethodSpec(BaseModel):
    """Method specification."""

    name: str
    purpose: str
    params: List[dict]
    returns: str
    raises: List[str] = []


class ComponentSpec(BaseModel):
    """Component specification."""

    name: str
    purpose: str
    file_path: str
    responsibilities: List[str]
    dependencies: List[str]
    public_interface: List[MethodSpec]
    error_handling: List[str]
    test_count: int


class ADR(BaseModel):
    """Architecture Decision Record."""

    id: str
    title: str
    decision: str
    rationale: str
    consequences: dict


class ArchitectureSpec(BaseModel):
    """Architect phase output schema."""

    epic_id: str
    components: List[ComponentSpec]
    adrs: List[ADR]
    test_strategy: dict
    acceptance_criteria: List[str]


class FileSpec(BaseModel):
    """File specification."""

    path: str
    content: str
    imports: List[str] = []
    classes: List[str] = []
    functions: List[str] = []


class CodeDeliverable(BaseModel):
    """Developer phase output schema."""

    files: List[FileSpec]
    test_files: List[FileSpec]
    dependencies: List[str]
    migration_scripts: List[FileSpec] = []


class IssueSpec(BaseModel):
    """QA issue specification."""

    id: str
    severity: str = Field(pattern=r"^(critical|high|medium|low)$")
    category: str
    description: str
    location: str
    fix_required: bool


class QAReport(BaseModel):
    """QA phase output schema."""

    passed: bool
    issues: List[IssueSpec]
    test_results: dict
    recommendations: List[str]
