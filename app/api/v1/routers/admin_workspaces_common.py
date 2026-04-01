"""
Shared request/response models and helpers for admin workspace endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Request
from pydantic import BaseModel, Field


# ===========================================================================
# Request/Response Models
# ===========================================================================

class Tier1ResultModel(BaseModel):
    """Single tier 1 validation result."""
    rule_id: str
    status: str
    message: Optional[str] = None
    artifact_id: Optional[str] = None


class Tier1ReportModel(BaseModel):
    """Tier 1 validation report."""
    passed: bool
    results: List[Tier1ResultModel]


class WorkspaceStateResponse(BaseModel):
    """Workspace state response."""
    workspace_id: str
    user_id: str
    branch: str
    base_commit: str
    is_dirty: bool
    modified_artifacts: List[str]
    modified_files: List[str]
    tier1: Tier1ReportModel
    last_touched: datetime
    expires_at: datetime


class CreateWorkspaceResponse(BaseModel):
    """Response for workspace creation."""
    workspace_id: str
    branch: str
    base_commit: str


class ArtifactContentResponse(BaseModel):
    """Artifact content response."""
    artifact_id: str
    content: str
    version: str


class WriteArtifactRequest(BaseModel):
    """Request to write artifact content."""
    content: str = Field(..., description="New artifact content")


class WriteArtifactResponse(BaseModel):
    """Response for artifact write."""
    success: bool
    tier1: Tier1ReportModel


class PreviewProvenanceModel(BaseModel):
    """Provenance information for preview."""
    role: Optional[str] = None
    schema_: Optional[str] = Field(None, alias="schema")
    package: Optional[str] = None

    model_config = {"populate_by_name": True}


class PreviewResponse(BaseModel):
    """Preview response with resolved prompt."""
    resolved_prompt: str
    provenance: PreviewProvenanceModel


class CommitRequest(BaseModel):
    """Request to commit changes."""
    message: str = Field(..., min_length=1, max_length=1000)


class CommitResponse(BaseModel):
    """Response for commit."""
    commit_hash: str
    commit_hash_short: str
    message: str


class CreateOrchestrationWorkflowRequest(BaseModel):
    """Request to create an orchestration workflow."""
    workflow_id: str = Field(..., min_length=2, max_length=100, pattern=r'^[a-z][a-z0-9_]*$')
    name: Optional[str] = Field(None, max_length=200)
    version: str = Field("1.0.0", pattern=r'^\d+\.\d+\.\d+$')
    pow_class: str = Field("template", pattern=r'^(reference|template|instance)$')
    derived_from: Optional[Dict[str, str]] = None
    source_version: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class CreateOrchestrationWorkflowResponse(BaseModel):
    """Response for orchestration workflow creation."""
    workflow_id: str
    version: str
    artifact_id: str


class CreateDocumentTypeRequest(BaseModel):
    """Request to create a document type (DCW)."""
    doc_type_id: str = Field(..., min_length=2, max_length=100, pattern=r'^[a-z][a-z0-9_]*$')
    display_name: Optional[str] = Field(None, max_length=200)
    version: str = Field("1.0.0", pattern=r'^\d+\.\d+\.\d+$')
    scope: str = Field("project", pattern=r'^[a-z][a-z0-9_]*$')
    role_ref: str = Field("prompt:role:technical_architect:1.0.0")


class CreateDocumentTypeResponse(BaseModel):
    """Response for document type creation."""
    doc_type_id: str
    version: str
    artifact_id: str


class CreateDcwWorkflowRequest(BaseModel):
    """Request to create a DCW workflow for an existing document type."""
    doc_type_id: str = Field(..., min_length=2, max_length=100, pattern=r'^[a-z][a-z0-9_]*$')
    version: str = Field("1.0.0", pattern=r'^\d+\.\d+\.\d+$')


class CreateDcwWorkflowResponse(BaseModel):
    """Response for DCW workflow creation."""
    doc_type_id: str
    version: str
    artifact_id: str


class CreateRolePromptRequest(BaseModel):
    """Request to create a role prompt."""
    role_id: str = Field(..., min_length=2, max_length=100, pattern=r'^[a-z][a-z0-9_]*$')
    name: Optional[str] = Field(None, max_length=200)
    version: str = Field("1.0.0", pattern=r'^\d+\.\d+\.\d+$')


class CreateRolePromptResponse(BaseModel):
    """Response for role prompt creation."""
    role_id: str
    version: str
    artifact_id: str


class CreateTemplateRequest(BaseModel):
    """Request to create a template."""
    template_id: str = Field(..., min_length=2, max_length=100, pattern=r'^[a-z][a-z0-9_]*$')
    name: Optional[str] = Field(None, max_length=200)
    purpose: str = Field("general", pattern=r'^(document|qa|pgc|general)$')
    version: str = Field("1.0.0", pattern=r'^\d+\.\d+\.\d+$')


class CreateTemplateResponse(BaseModel):
    """Response for template creation."""
    template_id: str
    version: str
    artifact_id: str


class CreateSchemaRequest(BaseModel):
    """Request to create a standalone schema."""
    schema_id: str = Field(..., min_length=2, max_length=100, pattern=r'^[a-z][a-z0-9_]*$')
    title: Optional[str] = Field(None, max_length=200)
    version: str = Field("1.0.0", pattern=r'^\d+\.\d+\.\d+$')


class CreateSchemaResponse(BaseModel):
    """Response for schema creation."""
    schema_id: str
    version: str
    artifact_id: str


class ArtifactDiffModel(BaseModel):
    """Diff for a single artifact."""
    artifact_id: str
    file_path: str
    status: str  # M=modified, A=added, D=deleted
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    diff_content: str
    additions: int = 0
    deletions: int = 0


class DiffResponse(BaseModel):
    """Response for diff endpoint."""
    diffs: List[ArtifactDiffModel]
    total: int


# ===========================================================================
# Shared Helpers
# ===========================================================================

def get_user_info(request: Request) -> Dict[str, Any]:
    """
    Extract user info from request.

    Raises HTTPException 401 if no authenticated user is present.
    """
    from fastapi import HTTPException, status

    user = getattr(request.state, "user", None)
    if user:
        return {
            "user_id": str(user.id) if hasattr(user, "id") else "unknown",
            "user_name": user.name if hasattr(user, "name") else "Admin User",
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required for admin workspace operations",
    )


def state_to_response(state) -> WorkspaceStateResponse:
    """Convert WorkspaceState to response model."""
    return WorkspaceStateResponse(
        workspace_id=state.workspace_id,
        user_id=state.user_id,
        branch=state.branch,
        base_commit=state.base_commit,
        is_dirty=state.is_dirty,
        modified_artifacts=state.modified_artifacts,
        modified_files=state.modified_files,
        tier1=Tier1ReportModel(
            passed=state.tier1.passed,
            results=[
                Tier1ResultModel(
                    rule_id=r.rule_id,
                    status=r.status,
                    message=r.message,
                    artifact_id=r.artifact_id,
                )
                for r in state.tier1.results
            ],
        ),
        last_touched=state.last_touched,
        expires_at=state.expires_at,
    )
