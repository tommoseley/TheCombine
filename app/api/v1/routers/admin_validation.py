"""
Admin Validation API endpoints.

Per ADR-044 WS-044-08, these endpoints provide governance guardrails
to prevent bad configurations from entering the system.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.services.config_validator import (
    ConfigValidator,
    ValidationReport,
    ValidationResult,
    ValidationSeverity,
    get_config_validator,
)
from app.config.package_loader import get_package_loader


router = APIRouter(prefix="/admin/validation", tags=["admin-validation"])


# ===========================================================================
# Response Models
# ===========================================================================

class ValidationResultResponse(BaseModel):
    """A single validation result."""
    rule_id: str
    severity: str
    message: str
    file_path: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ValidationReportResponse(BaseModel):
    """Complete validation report."""
    valid: bool
    error_count: int
    warning_count: int
    errors: List[ValidationResultResponse]
    warnings: List[ValidationResultResponse]


class ValidateActivationRequest(BaseModel):
    """Request to validate a release activation."""
    doc_type_id: str
    version: str


class ValidateSchemaCompatibilityRequest(BaseModel):
    """Request to validate schema compatibility."""
    doc_type_id: str
    old_version: str
    new_version: str


def _to_response(report: ValidationReport) -> ValidationReportResponse:
    """Convert internal report to API response."""
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
                details=e.details,
            )
            for e in report.errors
        ],
        warnings=[
            ValidationResultResponse(
                rule_id=w.rule_id,
                severity=w.severity.value,
                message=w.message,
                file_path=w.file_path,
                details=w.details,
            )
            for w in report.warnings
        ],
    )


# ===========================================================================
# Validation Endpoints
# ===========================================================================

@router.post(
    "/package/{doc_type_id}/{version}",
    response_model=ValidationReportResponse,
    summary="Validate package",
    description="Validate a Document Type Package for governance compliance.",
)
async def validate_package(
    doc_type_id: str,
    version: str,
    validator: ConfigValidator = Depends(get_config_validator),
) -> ValidationReportResponse:
    """
    Validate a Document Type Package.

    Checks:
    - Required fields present
    - Creation mode integrity (no extracted docs)
    - PGC requirement for Descriptive/Prescriptive docs
    - Artifact file references resolve
    - Shared artifact references resolve
    """
    loader = get_package_loader()
    config_path = loader.config_path

    package_path = config_path / "document_types" / doc_type_id / "releases" / version

    if not package_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "PACKAGE_NOT_FOUND",
                "message": f"Package not found: {doc_type_id} v{version}",
            },
        )

    report = validator.validate_package(package_path)
    return _to_response(report)


@router.post(
    "/activation",
    response_model=ValidationReportResponse,
    summary="Validate activation",
    description="Validate that a release can be activated (cross-package dependencies).",
)
async def validate_activation(
    request: ValidateActivationRequest,
    validator: ConfigValidator = Depends(get_config_validator),
) -> ValidationReportResponse:
    """
    Validate release activation.

    Checks:
    - Package exists at specified version
    - All required_inputs have active releases
    - All shared artifact references resolve
    """
    report = validator.validate_activation(request.doc_type_id, request.version)
    return _to_response(report)


@router.get(
    "/all-active",
    response_model=ValidationReportResponse,
    summary="Validate all active packages",
    description="Validate all currently active packages for cross-package integrity.",
)
async def validate_all_active(
    validator: ConfigValidator = Depends(get_config_validator),
) -> ValidationReportResponse:
    """
    Validate all active packages.

    Checks each active package for:
    - Required input dependencies
    - Shared artifact resolution
    """
    report = validator.validate_all_active_packages()
    return _to_response(report)


@router.post(
    "/schema-compatibility",
    response_model=ValidationReportResponse,
    summary="Validate schema compatibility",
    description="Check if schema changes between versions are compatible.",
)
async def validate_schema_compatibility(
    request: ValidateSchemaCompatibilityRequest,
    validator: ConfigValidator = Depends(get_config_validator),
) -> ValidationReportResponse:
    """
    Validate schema compatibility between versions.

    Detects breaking changes:
    - Added required fields
    - Removed properties

    Breaking changes require major version bump.
    """
    report = validator.validate_schema_compatibility(
        request.doc_type_id,
        request.old_version,
        request.new_version,
    )
    return _to_response(report)


# ===========================================================================
# Governance Rules Reference
# ===========================================================================

@router.get(
    "/rules",
    summary="List governance rules",
    description="List all governance rules enforced by the validator.",
)
async def list_rules() -> Dict[str, Any]:
    """
    List all governance rules.

    Rules are organized into two tiers:
    - Tier 1 (commit): Protect repository integrity - fail fast before Git history
    - Tier 2 (activation): Protect runtime safety - evaluated when staging/activating

    All rules are BLOCKED (not warned) per ADR-044.
    """
    return {
        "tiers": {
            "commit": {
                "description": "Commit-time blockers - protect repository integrity",
                "evaluated_at": "Before changes enter Git history",
            },
            "activation": {
                "description": "Activation-time blockers - protect runtime safety",
                "evaluated_at": "When staging or activating a release",
            },
        },
        "rules": [
            # Tier 1: Commit-time blockers (repository integrity)
            {
                "rule_id": "MANIFEST_MISSING",
                "tier": "commit",
                "severity": "error",
                "description": "Package must have a package.yaml manifest",
            },
            {
                "rule_id": "MANIFEST_INVALID_YAML",
                "tier": "commit",
                "severity": "error",
                "description": "Package manifest must be valid YAML",
            },
            {
                "rule_id": "REQUIRED_FIELD_MISSING",
                "tier": "commit",
                "severity": "error",
                "description": "Required fields must be present in manifest",
            },
            {
                "rule_id": "ARTIFACT_FILE_MISSING",
                "tier": "commit",
                "severity": "error",
                "description": "Referenced artifact files must exist",
            },
            {
                "rule_id": "INVALID_ROLE_REF",
                "tier": "commit",
                "severity": "error",
                "description": "Role reference must follow format prompt:role:<id>:<version>",
            },
            {
                "rule_id": "ROLE_NOT_FOUND",
                "tier": "commit",
                "severity": "error",
                "description": "Referenced role must exist at specified version",
            },
            {
                "rule_id": "INVALID_TEMPLATE_REF",
                "tier": "commit",
                "severity": "error",
                "description": "Template reference must follow format prompt:template:<id>:<version>",
            },
            {
                "rule_id": "TEMPLATE_NOT_FOUND",
                "tier": "commit",
                "severity": "error",
                "description": "Referenced template must exist at specified version",
            },
            # Tier 2: Activation-time blockers (runtime safety)
            {
                "rule_id": "EXTRACTED_DOC_FORBIDDEN",
                "tier": "activation",
                "severity": "error",
                "description": "Extracted documents cannot be registered as document types",
            },
            {
                "rule_id": "PGC_REQUIRED",
                "tier": "activation",
                "severity": "error",
                "description": "Descriptive/Prescriptive documents require PGC context",
            },
            {
                "rule_id": "PGC_FILE_MISSING",
                "tier": "activation",
                "severity": "error",
                "description": "Referenced PGC context file must exist",
            },
            {
                "rule_id": "PACKAGE_NOT_FOUND",
                "tier": "activation",
                "severity": "error",
                "description": "Package must exist for activation",
            },
            {
                "rule_id": "VERSION_NOT_FOUND",
                "tier": "activation",
                "severity": "error",
                "description": "Specified version must exist",
            },
            {
                "rule_id": "REQUIRED_INPUT_NOT_ACTIVE",
                "tier": "activation",
                "severity": "error",
                "description": "All required inputs must have active releases before activation",
            },
            {
                "rule_id": "BREAKING_SCHEMA_CHANGE",
                "tier": "activation",
                "severity": "error",
                "description": "Breaking schema changes require major version bump",
            },
        ],
        "principle": "All violations are BLOCKED, not warned. No configuration enters the system without passing validation.",
        "deferred": [
            "UNREFERENCED_ARTIFACT - Artifact exists but not referenced (future warning)",
            "Golden trace regression enforcement",
            "Prompt semantic QA beyond structural validation",
        ],
    }
