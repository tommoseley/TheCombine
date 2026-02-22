"""Pydantic schemas for pipeline artifacts."""
from typing import List

from pydantic import BaseModel, Field


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
