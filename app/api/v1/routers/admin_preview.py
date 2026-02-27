"""
Admin Preview & Dry-Run API endpoints.

Per ADR-044 WS-044-06, these endpoints enable:
- Preview of document type configuration
- Dry-run validation before activation
- Diff comparison between versions
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.services.preview_service import (
    PreviewService,
    PreviewResult,
    PreviewStatus,
    PromptPreview,
    SchemaPreview,
    PreviewDiff,
    get_preview_service,
)


router = APIRouter(prefix="/admin/preview", tags=["admin-preview"])


# ===========================================================================
# Response Models
# ===========================================================================

class ValidationResultResponse(BaseModel):
    """Validation result."""
    rule_id: str
    severity: str
    message: str
    file_path: Optional[str] = None


class ValidationReportResponse(BaseModel):
    """Validation report."""
    valid: bool
    error_count: int
    warning_count: int
    errors: List[ValidationResultResponse]
    warnings: List[ValidationResultResponse]


class PromptPreviewResponse(BaseModel):
    """Prompt preview response."""
    role_prompt: Optional[str] = None
    task_prompt: Optional[str] = None
    pgc_context: Optional[str] = None
    questions_prompt: Optional[str] = None
    qa_prompt: Optional[str] = None
    assembled_prompt: Optional[str] = None
    token_estimate: int = 0


class SchemaPreviewResponse(BaseModel):
    """Schema preview response."""
    schema_: Optional[Dict[str, Any]] = Field(None, alias="schema")
    required_fields: List[str] = Field(default_factory=list)
    optional_fields: List[str] = Field(default_factory=list)
    field_count: int = 0

    model_config = {"populate_by_name": True}


class DiffItemResponse(BaseModel):
    """Diff item response."""
    artifact_type: str
    change_type: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    summary: Optional[str] = None


class PreviewDiffResponse(BaseModel):
    """Preview diff response."""
    previous_version: Optional[str] = None
    current_version: str
    has_changes: bool
    changes: List[DiffItemResponse]
    breaking_changes: List[str]


class PreviewResultResponse(BaseModel):
    """Full preview result response."""
    doc_type_id: str
    version: str
    status: str
    validation: Optional[ValidationReportResponse] = None
    prompts: Optional[PromptPreviewResponse] = None
    schema_preview: Optional[SchemaPreviewResponse] = Field(None, alias="schema")
    diff: Optional[PreviewDiffResponse] = None
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    execution_time_ms: int = 0
    timestamp: datetime

    model_config = {"populate_by_name": True}


class ActivationReadinessResponse(BaseModel):
    """Response for activation readiness check."""
    doc_type_id: str
    version: str
    ready_for_activation: bool
    validation: ValidationReportResponse
    blocking_errors: List[str]
    warnings: List[str]


# ===========================================================================
# Helper Functions
# ===========================================================================

def _to_validation_response(report) -> ValidationReportResponse:
    """Convert ValidationReport to response model."""
    return ValidationReportResponse(
        valid=report.valid,
        error_count=len(report.errors),
        warning_count=len(report.warnings),
        errors=[
            ValidationResultResponse(
                rule_id=e.rule_id,
                severity=e.severity.value,
                message=e.message,
                file_path=e.file_path,
            )
            for e in report.errors
        ],
        warnings=[
            ValidationResultResponse(
                rule_id=w.rule_id,
                severity=w.severity.value,
                message=w.message,
                file_path=w.file_path,
            )
            for w in report.warnings
        ],
    )


def _to_prompt_response(preview: PromptPreview) -> PromptPreviewResponse:
    """Convert PromptPreview to response model."""
    return PromptPreviewResponse(
        role_prompt=preview.role_prompt,
        task_prompt=preview.task_prompt,
        pgc_context=preview.pgc_context,
        questions_prompt=preview.questions_prompt,
        qa_prompt=preview.qa_prompt,
        assembled_prompt=preview.assembled_prompt,
        token_estimate=preview.token_estimate,
    )


def _to_schema_response(preview: SchemaPreview) -> SchemaPreviewResponse:
    """Convert SchemaPreview to response model."""
    return SchemaPreviewResponse(
        schema=preview.schema,
        required_fields=preview.required_fields,
        optional_fields=preview.optional_fields,
        field_count=preview.field_count,
    )


def _to_diff_response(diff: PreviewDiff) -> PreviewDiffResponse:
    """Convert PreviewDiff to response model."""
    return PreviewDiffResponse(
        previous_version=diff.previous_version,
        current_version=diff.current_version,
        has_changes=diff.has_changes,
        changes=[
            DiffItemResponse(
                artifact_type=c.artifact_type,
                change_type=c.change_type,
                old_value=c.old_value,
                new_value=c.new_value,
                summary=c.summary,
            )
            for c in diff.changes
        ],
        breaking_changes=diff.breaking_changes,
    )


def _to_preview_response(result: PreviewResult) -> PreviewResultResponse:
    """Convert PreviewResult to response model."""
    return PreviewResultResponse(
        doc_type_id=result.doc_type_id,
        version=result.version,
        status=result.status.value,
        validation=_to_validation_response(result.validation_report) if result.validation_report else None,
        prompts=_to_prompt_response(result.prompt_preview) if result.prompt_preview else None,
        schema=_to_schema_response(result.schema_preview) if result.schema_preview else None,
        diff=_to_diff_response(result.diff) if result.diff else None,
        warnings=result.warnings,
        errors=result.errors,
        execution_time_ms=result.execution_time_ms,
        timestamp=result.timestamp,
    )


# ===========================================================================
# Preview Endpoints
# ===========================================================================

@router.get(
    "/{doc_type_id}/{version}",
    response_model=PreviewResultResponse,
    summary="Preview document type",
    description="Execute a full preview of a document type configuration.",
)
async def preview_document_type(
    doc_type_id: str,
    version: str,
    include_diff: bool = Query(default=True, description="Include diff vs active version"),
    service: PreviewService = Depends(get_preview_service),
) -> PreviewResultResponse:
    """Preview a document type configuration."""
    result = service.preview_document_type(
        doc_type_id=doc_type_id,
        version=version,
        include_diff=include_diff,
    )
    return _to_preview_response(result)


@router.get(
    "/{doc_type_id}/{version}/prompts",
    response_model=PromptPreviewResponse,
    summary="Preview prompts",
    description="Preview the assembled prompts for a document type.",
)
async def preview_prompts(
    doc_type_id: str,
    version: str,
    service: PreviewService = Depends(get_preview_service),
) -> PromptPreviewResponse:
    """Preview assembled prompts."""
    try:
        preview = service.preview_prompt_assembly(doc_type_id, version)
        return _to_prompt_response(preview)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "PREVIEW_ERROR", "message": str(e)},
        )


@router.get(
    "/{doc_type_id}/{version}/schema",
    response_model=SchemaPreviewResponse,
    summary="Preview schema",
    description="Preview the output schema for a document type.",
)
async def preview_schema(
    doc_type_id: str,
    version: str,
    service: PreviewService = Depends(get_preview_service),
) -> SchemaPreviewResponse:
    """Preview output schema."""
    try:
        preview = service.preview_schema(doc_type_id, version)
        return _to_schema_response(preview)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "PREVIEW_ERROR", "message": str(e)},
        )


# ===========================================================================
# Diff Endpoints
# ===========================================================================

@router.get(
    "/{doc_type_id}/{version}/diff",
    response_model=PreviewDiffResponse,
    summary="Generate diff",
    description="Generate diff between version and active release (or specified version).",
)
async def generate_diff(
    doc_type_id: str,
    version: str,
    compare_to: Optional[str] = Query(None, description="Version to compare against (default: active)"),
    service: PreviewService = Depends(get_preview_service),
) -> PreviewDiffResponse:
    """Generate diff between versions."""
    diff = service.generate_diff(
        doc_type_id=doc_type_id,
        new_version=version,
        old_version=compare_to,
    )
    return _to_diff_response(diff)


# ===========================================================================
# Activation Readiness Endpoints
# ===========================================================================

@router.get(
    "/{doc_type_id}/{version}/ready",
    response_model=ActivationReadinessResponse,
    summary="Check activation readiness",
    description="Validate if a version is ready for activation. Failures here block promotion.",
)
async def check_activation_readiness(
    doc_type_id: str,
    version: str,
    service: PreviewService = Depends(get_preview_service),
) -> ActivationReadinessResponse:
    """
    Check if a version is ready for activation.

    This is the gatekeeper - failures here MUST block promotion.
    """
    result = service.validate_for_activation(doc_type_id, version)

    return ActivationReadinessResponse(
        doc_type_id=doc_type_id,
        version=version,
        ready_for_activation=result.status == PreviewStatus.SUCCESS,
        validation=_to_validation_response(result.validation_report) if result.validation_report else ValidationReportResponse(
            valid=False,
            error_count=len(result.errors),
            warning_count=0,
            errors=[],
            warnings=[],
        ),
        blocking_errors=result.errors,
        warnings=result.warnings,
    )
