"""
Preview & Dry-Run Engine.

Per ADR-044 WS-044-06, this service enables:
- Preview of document generation using staged/uncommitted artifacts
- Dry-run execution without persisting results
- Comparison of outputs vs prior release
- Validation that failures block promotion
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config.package_loader import (
    PackageLoader,
    DocumentTypePackage,
    get_package_loader,
    PackageNotFoundError,
    VersionNotFoundError,
)
from app.api.services.config_validator import (
    ConfigValidator,
    ValidationReport,
    get_config_validator,
)

logger = logging.getLogger(__name__)


class PreviewStatus(str, Enum):
    """Status of a preview execution."""
    SUCCESS = "success"
    VALIDATION_FAILED = "validation_failed"
    GENERATION_FAILED = "generation_failed"
    ERROR = "error"


@dataclass
class PromptPreview:
    """Preview of an assembled prompt."""
    role_prompt: Optional[str] = None
    task_prompt: Optional[str] = None
    pgc_context: Optional[str] = None
    questions_prompt: Optional[str] = None
    qa_prompt: Optional[str] = None
    assembled_prompt: Optional[str] = None
    token_estimate: int = 0


@dataclass
class SchemaPreview:
    """Preview of schema validation."""
    schema: Optional[Dict[str, Any]] = None
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    field_count: int = 0


@dataclass
class DiffItem:
    """A single diff between versions."""
    artifact_type: str
    change_type: str  # added, removed, modified
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    summary: Optional[str] = None


@dataclass
class PreviewDiff:
    """Diff between current and previous release."""
    previous_version: Optional[str] = None
    current_version: str = ""
    has_changes: bool = False
    changes: List[DiffItem] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)


@dataclass
class PreviewResult:
    """Result of a preview execution."""
    doc_type_id: str
    version: str
    status: PreviewStatus
    validation_report: Optional[ValidationReport] = None
    prompt_preview: Optional[PromptPreview] = None
    schema_preview: Optional[SchemaPreview] = None
    diff: Optional[PreviewDiff] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    execution_time_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


class PreviewServiceError(Exception):
    """Base exception for preview service errors."""
    pass


class PreviewService:
    """
    Preview & Dry-Run Engine.

    Enables testing of configuration changes before activation:
    - Assembles prompts from staged artifacts
    - Validates against governance rules
    - Compares with prior release
    - Reports potential issues
    """

    def __init__(
        self,
        loader: Optional[PackageLoader] = None,
        validator: Optional[ConfigValidator] = None,
    ):
        self._loader = loader or get_package_loader()
        self._validator = validator or get_config_validator()

    # =========================================================================
    # Preview Execution
    # =========================================================================

    def preview_document_type(
        self,
        doc_type_id: str,
        version: str,
        include_diff: bool = True,
    ) -> PreviewResult:
        """
        Execute a full preview of a document type configuration.

        Args:
            doc_type_id: Document type to preview
            version: Version to preview
            include_diff: Whether to include diff vs previous release

        Returns:
            PreviewResult with all preview data
        """
        import time
        start_time = time.time()

        result = PreviewResult(
            doc_type_id=doc_type_id,
            version=version,
            status=PreviewStatus.SUCCESS,
        )

        try:
            # Load the package
            package = self._loader.get_document_type(doc_type_id, version)

            # Run validation
            package_path = self._get_package_path(doc_type_id, version)
            validation_report = self._validator.validate_package(package_path)
            result.validation_report = validation_report

            if not validation_report.valid:
                result.status = PreviewStatus.VALIDATION_FAILED
                result.errors = [e.message for e in validation_report.errors]
            else:
                # Preview prompts
                result.prompt_preview = self._preview_prompts(package)

                # Preview schema
                result.schema_preview = self._preview_schema(package)

                # Add warnings from validation
                result.warnings = [w.message for w in validation_report.warnings]

            # Generate diff if requested
            if include_diff:
                result.diff = self._generate_diff(doc_type_id, version)

        except (PackageNotFoundError, VersionNotFoundError) as e:
            result.status = PreviewStatus.ERROR
            result.errors = [str(e)]
        except Exception as e:
            logger.exception(f"Preview failed for {doc_type_id} v{version}")
            result.status = PreviewStatus.ERROR
            result.errors = [f"Preview error: {str(e)}"]

        result.execution_time_ms = int((time.time() - start_time) * 1000)
        return result

    def preview_prompt_assembly(
        self,
        doc_type_id: str,
        version: str,
    ) -> PromptPreview:
        """
        Preview the assembled prompt for a document type.

        Args:
            doc_type_id: Document type
            version: Version to preview

        Returns:
            PromptPreview with all prompt components
        """
        package = self._loader.get_document_type(doc_type_id, version)
        return self._preview_prompts(package)

    def preview_schema(
        self,
        doc_type_id: str,
        version: str,
    ) -> SchemaPreview:
        """
        Preview the output schema for a document type.

        Args:
            doc_type_id: Document type
            version: Version to preview

        Returns:
            SchemaPreview with schema details
        """
        package = self._loader.get_document_type(doc_type_id, version)
        return self._preview_schema(package)

    # =========================================================================
    # Diff Generation
    # =========================================================================

    def generate_diff(
        self,
        doc_type_id: str,
        new_version: str,
        old_version: Optional[str] = None,
    ) -> PreviewDiff:
        """
        Generate diff between two versions.

        Args:
            doc_type_id: Document type
            new_version: New version to compare
            old_version: Old version (default: active version)

        Returns:
            PreviewDiff with all changes
        """
        return self._generate_diff(doc_type_id, new_version, old_version)

    # =========================================================================
    # Dry-Run Validation
    # =========================================================================

    def validate_for_activation(
        self,
        doc_type_id: str,
        version: str,
    ) -> PreviewResult:
        """
        Run all validations required before activation.

        This is the gatekeeper check - failures here MUST block promotion.

        Args:
            doc_type_id: Document type
            version: Version to validate

        Returns:
            PreviewResult with validation status
        """
        import time
        start_time = time.time()

        result = PreviewResult(
            doc_type_id=doc_type_id,
            version=version,
            status=PreviewStatus.SUCCESS,
        )

        try:
            # Run package validation
            package_path = self._get_package_path(doc_type_id, version)
            package_report = self._validator.validate_package(package_path)

            # Run activation validation (cross-package dependencies)
            activation_report = self._validator.validate_activation(doc_type_id, version)

            # Merge reports
            combined_report = ValidationReport(valid=True)
            combined_report.merge(package_report)
            combined_report.merge(activation_report)

            result.validation_report = combined_report

            if not combined_report.valid:
                result.status = PreviewStatus.VALIDATION_FAILED
                result.errors = [e.message for e in combined_report.errors]

            result.warnings = [w.message for w in combined_report.warnings]

        except Exception as e:
            logger.exception(f"Activation validation failed for {doc_type_id} v{version}")
            result.status = PreviewStatus.ERROR
            result.errors = [f"Validation error: {str(e)}"]

        result.execution_time_ms = int((time.time() - start_time) * 1000)
        return result

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _get_package_path(self, doc_type_id: str, version: str) -> Path:
        """Get the filesystem path to a package."""
        return (
            self._loader.config_path
            / "document_types"
            / doc_type_id
            / "releases"
            / version
        )

    def _preview_prompts(self, package: DocumentTypePackage) -> PromptPreview:
        """Generate prompt preview from package."""
        preview = PromptPreview()

        # Get task prompt
        task_prompt = package.get_task_prompt()
        if task_prompt:
            preview.task_prompt = task_prompt
            preview.token_estimate += self._estimate_tokens(task_prompt)

        # Get PGC context
        pgc_context = package.get_pgc_context()
        if pgc_context:
            preview.pgc_context = pgc_context
            preview.token_estimate += self._estimate_tokens(pgc_context)

        # Get QA prompt
        qa_prompt = package.get_qa_prompt()
        if qa_prompt:
            preview.qa_prompt = qa_prompt
            preview.token_estimate += self._estimate_tokens(qa_prompt)

        # Get questions prompt if method exists
        if hasattr(package, 'get_questions_prompt'):
            questions_prompt = package.get_questions_prompt()
            if questions_prompt:
                preview.questions_prompt = questions_prompt
                preview.token_estimate += self._estimate_tokens(questions_prompt)

        # Get role prompt if referenced
        if package.role_prompt_ref:
            try:
                parts = package.role_prompt_ref.split(":")
                if len(parts) == 4:
                    role_id = parts[2]
                    role_version = parts[3]
                    role = self._loader.get_role(role_id, role_version)
                    preview.role_prompt = role.content
                    preview.token_estimate += self._estimate_tokens(role.content)
            except Exception:
                pass  # Role not found, will be caught in validation

        # Assemble full prompt
        assembled_parts = []
        if preview.role_prompt:
            assembled_parts.append(f"# ROLE\n{preview.role_prompt}")
        if preview.task_prompt:
            assembled_parts.append(f"# TASK\n{preview.task_prompt}")
        if preview.pgc_context:
            assembled_parts.append(f"# CONTEXT\n{preview.pgc_context}")

        if assembled_parts:
            preview.assembled_prompt = "\n\n".join(assembled_parts)

        return preview

    def _preview_schema(self, package: DocumentTypePackage) -> SchemaPreview:
        """Generate schema preview from package."""
        preview = SchemaPreview()

        schema = package.get_schema()
        if schema:
            preview.schema = schema
            preview.required_fields = schema.get("required", [])

            properties = schema.get("properties", {})
            all_fields = list(properties.keys())
            preview.optional_fields = [
                f for f in all_fields if f not in preview.required_fields
            ]
            preview.field_count = len(all_fields)

        return preview

    def _generate_diff(
        self,
        doc_type_id: str,
        new_version: str,
        old_version: Optional[str] = None,
    ) -> PreviewDiff:
        """Generate diff between versions."""
        diff = PreviewDiff(current_version=new_version)

        # Determine old version
        if old_version is None:
            active = self._loader.get_active_releases()
            old_version = active.document_types.get(doc_type_id)

        if old_version is None or old_version == new_version:
            diff.has_changes = False
            return diff

        diff.previous_version = old_version

        try:
            old_package = self._loader.get_document_type(doc_type_id, old_version)
            new_package = self._loader.get_document_type(doc_type_id, new_version)

            # Compare prompts
            self._diff_prompts(old_package, new_package, diff)

            # Compare schemas
            self._diff_schemas(old_package, new_package, diff)

            # Compare metadata
            self._diff_metadata(old_package, new_package, diff)

            diff.has_changes = len(diff.changes) > 0

        except (PackageNotFoundError, VersionNotFoundError):
            # Can't generate diff if old version doesn't exist
            diff.has_changes = True
            diff.changes.append(DiffItem(
                artifact_type="package",
                change_type="added",
                summary=f"New version {new_version} (no previous version to compare)",
            ))

        return diff

    def _diff_prompts(
        self,
        old_package: DocumentTypePackage,
        new_package: DocumentTypePackage,
        diff: PreviewDiff,
    ) -> None:
        """Compare prompts between packages."""
        prompt_types = [
            ("task_prompt", "Task Prompt"),
            ("qa_prompt", "QA Prompt"),
            ("pgc_context", "PGC Context"),
        ]

        for artifact_key, display_name in prompt_types:
            old_getter = getattr(old_package, f"get_{artifact_key}", None)
            new_getter = getattr(new_package, f"get_{artifact_key}", None)
            old_content = old_getter() if old_getter else None
            new_content = new_getter() if new_getter else None

            if old_content != new_content:
                if old_content is None and new_content is not None:
                    change_type = "added"
                elif old_content is not None and new_content is None:
                    change_type = "removed"
                else:
                    change_type = "modified"

                diff.changes.append(DiffItem(
                    artifact_type=artifact_key,
                    change_type=change_type,
                    old_value=self._truncate(old_content, 200) if old_content else None,
                    new_value=self._truncate(new_content, 200) if new_content else None,
                    summary=f"{display_name} {change_type}",
                ))

    def _diff_schemas(
        self,
        old_package: DocumentTypePackage,
        new_package: DocumentTypePackage,
        diff: PreviewDiff,
    ) -> None:
        """Compare schemas between packages."""
        old_schema = old_package.get_schema() or {}
        new_schema = new_package.get_schema() or {}

        if old_schema != new_schema:
            # Check for breaking changes
            old_required = set(old_schema.get("required", []))
            new_required = set(new_schema.get("required", []))
            old_props = set(old_schema.get("properties", {}).keys())
            new_props = set(new_schema.get("properties", {}).keys())

            added_required = new_required - old_required
            removed_props = old_props - new_props

            if added_required:
                diff.breaking_changes.append(
                    f"Added required fields: {', '.join(added_required)}"
                )

            if removed_props:
                diff.breaking_changes.append(
                    f"Removed properties: {', '.join(removed_props)}"
                )

            summary = "Schema modified"
            if diff.breaking_changes:
                summary += " (BREAKING)"

            diff.changes.append(DiffItem(
                artifact_type="schema",
                change_type="modified",
                summary=summary,
            ))

    def _diff_metadata(
        self,
        old_package: DocumentTypePackage,
        new_package: DocumentTypePackage,
        diff: PreviewDiff,
    ) -> None:
        """Compare metadata between packages."""
        metadata_fields = [
            ("authority_level", "Authority Level"),
            ("creation_mode", "Creation Mode"),
            ("production_mode", "Production Mode"),
        ]

        for field_name, display_name in metadata_fields:
            old_value = getattr(old_package, field_name, None)
            new_value = getattr(new_package, field_name, None)

            # Convert enums to strings for comparison
            if hasattr(old_value, "value"):
                old_value = old_value.value
            if hasattr(new_value, "value"):
                new_value = new_value.value

            if old_value != new_value:
                diff.changes.append(DiffItem(
                    artifact_type="metadata",
                    change_type="modified",
                    old_value=str(old_value) if old_value else None,
                    new_value=str(new_value) if new_value else None,
                    summary=f"{display_name} changed: {old_value} -> {new_value}",
                ))

                # Authority level changes are breaking
                if field_name == "authority_level":
                    diff.breaking_changes.append(
                        f"Authority level changed from {old_value} to {new_value}"
                    )

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimate (4 chars per token)."""
        if not text:
            return 0
        return len(text) // 4

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text for display."""
        if not text or len(text) <= max_length:
            return text
        return text[:max_length] + "..."


# Module-level singleton
_preview_service: Optional[PreviewService] = None


def get_preview_service() -> PreviewService:
    """Get the singleton PreviewService instance."""
    global _preview_service
    if _preview_service is None:
        _preview_service = PreviewService()
    return _preview_service


def reset_preview_service() -> None:
    """Reset the singleton (for testing)."""
    global _preview_service
    _preview_service = None
