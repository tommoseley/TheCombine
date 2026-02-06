"""
Configuration Validator for Governance Guardrails.

Per ADR-044 WS-044-08, this service prevents known failure modes
by validating configuration artifacts before they can be committed or activated.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from app.config.package_model import (
    AuthorityLevel,
    CreationMode,
)
from app.config.package_loader import (
    PackageLoader,
    get_package_loader,
    PackageNotFoundError,
    VersionNotFoundError,
)

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Severity level for validation results."""
    ERROR = "error"      # Blocks commit/activation
    WARNING = "warning"  # Allowed but flagged


@dataclass
class ValidationResult:
    """A single validation result."""
    rule_id: str
    severity: ValidationSeverity
    message: str
    file_path: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class ValidationReport:
    """Complete validation report."""
    valid: bool
    errors: List[ValidationResult] = field(default_factory=list)
    warnings: List[ValidationResult] = field(default_factory=list)

    def add_error(self, rule_id: str, message: str, file_path: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
        """Add an error result."""
        self.errors.append(ValidationResult(
            rule_id=rule_id,
            severity=ValidationSeverity.ERROR,
            message=message,
            file_path=file_path,
            details=details,
        ))
        self.valid = False

    def add_warning(self, rule_id: str, message: str, file_path: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
        """Add a warning result."""
        self.warnings.append(ValidationResult(
            rule_id=rule_id,
            severity=ValidationSeverity.WARNING,
            message=message,
            file_path=file_path,
            details=details,
        ))

    def merge(self, other: "ValidationReport") -> None:
        """Merge another report into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.valid:
            self.valid = False


class ConfigValidator:
    """
    Validates configuration artifacts for governance compliance.

    Per ADR-044, the following violations are BLOCKED (not warned):
    - No skipping mandatory PGC for Descriptive/Prescriptive documents
    - No extracted docs registered as document types
    - No release without validation passing
    - Cross-package integrity violations
    - Schema compatibility violations
    """

    def __init__(self, loader: Optional[PackageLoader] = None):
        """
        Initialize the validator.

        Args:
            loader: Optional PackageLoader instance.
        """
        self._loader = loader or get_package_loader()

    # =========================================================================
    # Package Validation
    # =========================================================================

    def validate_package(self, package_path: Path) -> ValidationReport:
        """
        Validate a Document Type Package.

        Args:
            package_path: Path to the package release directory

        Returns:
            ValidationReport with all findings
        """
        report = ValidationReport(valid=True)

        manifest_path = package_path / "package.yaml"
        if not manifest_path.exists():
            report.add_error(
                rule_id="MANIFEST_MISSING",
                message="Package manifest (package.yaml) not found",
                file_path=str(package_path),
            )
            return report

        try:
            with open(manifest_path, "r") as f:
                manifest = yaml.safe_load(f)
        except yaml.YAMLError as e:
            report.add_error(
                rule_id="MANIFEST_INVALID_YAML",
                message=f"Invalid YAML in package.yaml: {e}",
                file_path=str(manifest_path),
            )
            return report

        # Run all validation rules
        self._validate_required_fields(manifest, manifest_path, report)
        self._validate_creation_mode(manifest, manifest_path, report)
        self._validate_pgc_requirement(manifest, package_path, report)
        self._validate_artifact_references(manifest, package_path, report)
        self._validate_shared_references(manifest, report)

        return report

    def _validate_required_fields(
        self,
        manifest: Dict[str, Any],
        manifest_path: Path,
        report: ValidationReport,
    ) -> None:
        """Validate required fields are present."""
        required_fields = [
            "doc_type_id",
            "display_name",
            "version",
            "authority_level",
            "creation_mode",
        ]

        for field_name in required_fields:
            if field_name not in manifest:
                report.add_error(
                    rule_id="REQUIRED_FIELD_MISSING",
                    message=f"Required field '{field_name}' is missing",
                    file_path=str(manifest_path),
                )

    def _validate_creation_mode(
        self,
        manifest: Dict[str, Any],
        manifest_path: Path,
        report: ValidationReport,
    ) -> None:
        """
        Validate creation mode integrity.

        Rule: No extracted docs registered as document types.
        """
        creation_mode = manifest.get("creation_mode", "")

        if creation_mode == "extracted":
            report.add_error(
                rule_id="EXTRACTED_DOC_FORBIDDEN",
                message="Extracted documents cannot be registered as document types. "
                        "Extracted content belongs to data artifacts, not configuration.",
                file_path=str(manifest_path),
                details={"creation_mode": creation_mode},
            )

    def _validate_pgc_requirement(
        self,
        manifest: Dict[str, Any],
        package_path: Path,
        report: ValidationReport,
    ) -> None:
        """
        Validate PGC requirement for authority level.

        Rule: No skipping mandatory PGC for Descriptive/Prescriptive documents.

        PGC can be satisfied by either:
        1. An embedded pgc_context artifact in the package
        2. A standalone PGC fragment at prompts/pgc/{doc_type_id}.v1/
        """
        authority_level = manifest.get("authority_level", "")
        creation_mode = manifest.get("creation_mode", "")
        doc_type_id = manifest.get("doc_type_id", "")

        # PGC is only required for LLM-generated documents
        if creation_mode != "llm_generated":
            return

        # Descriptive and Prescriptive documents require PGC
        requires_pgc = authority_level in ("descriptive", "prescriptive")

        if not requires_pgc:
            return

        # Check if PGC context artifact is defined in package
        artifacts = manifest.get("artifacts", {})
        pgc_context = artifacts.get("pgc_context")

        if pgc_context:
            # Check if PGC context file exists in package
            pgc_path = package_path / pgc_context
            if not pgc_path.exists():
                report.add_error(
                    rule_id="PGC_FILE_MISSING",
                    message=f"PGC context file not found: {pgc_context}",
                    file_path=str(pgc_path),
                )
            return  # PGC is defined in package, validation complete

        # Check for standalone PGC fragment
        # Convention: prompts/pgc/{doc_type_id}.v1/releases/{version}/pgc.prompt.txt
        if self._loader and doc_type_id:
            pgc_fragment_id = f"{doc_type_id}.v1"
            pgc_fragments = self._loader.list_pgc()

            if pgc_fragment_id in pgc_fragments:
                # Standalone PGC fragment exists - requirement satisfied
                return

        # No PGC found - report error
        report.add_error(
            rule_id="PGC_REQUIRED",
            message=f"Documents with authority_level='{authority_level}' require PGC context. "
                    f"Add pgc_context artifact to package or create standalone fragment at "
                    f"prompts/pgc/{doc_type_id}.v1/",
            file_path=str(package_path / "package.yaml"),
            details={
                "authority_level": authority_level,
                "creation_mode": creation_mode,
            },
        )

    def _validate_artifact_references(
        self,
        manifest: Dict[str, Any],
        package_path: Path,
        report: ValidationReport,
    ) -> None:
        """Validate that referenced artifacts exist."""
        artifacts = manifest.get("artifacts", {})

        artifact_files = [
            ("task_prompt", "Task prompt"),
            ("qa_prompt", "QA prompt"),
            ("pgc_context", "PGC context"),
            ("questions_prompt", "Questions prompt"),
            ("schema", "Output schema"),
            ("full_docdef", "Full DocDef"),
            ("sidecar_docdef", "Sidecar DocDef"),
            ("gating_rules", "Gating rules"),
        ]

        for artifact_key, artifact_name in artifact_files:
            artifact_path = artifacts.get(artifact_key)
            if artifact_path:
                full_path = package_path / artifact_path
                if not full_path.exists():
                    report.add_error(
                        rule_id="ARTIFACT_FILE_MISSING",
                        message=f"{artifact_name} file not found: {artifact_path}",
                        file_path=str(full_path),
                    )

    def _validate_shared_references(
        self,
        manifest: Dict[str, Any],
        report: ValidationReport,
    ) -> None:
        """Validate shared artifact references resolve."""
        # Validate role prompt reference
        role_ref = manifest.get("role_prompt_ref")
        if role_ref:
            if not self._validate_ref_format(role_ref, "role"):
                report.add_error(
                    rule_id="INVALID_ROLE_REF",
                    message=f"Invalid role prompt reference format: {role_ref}. "
                            "Expected: prompt:role:<role_id>:<version>",
                    details={"role_prompt_ref": role_ref},
                )
            else:
                # Check if role exists
                parts = role_ref.split(":")
                role_id = parts[2]
                version = parts[3]
                try:
                    self._loader.get_role(role_id, version)
                except (PackageNotFoundError, VersionNotFoundError):
                    report.add_error(
                        rule_id="ROLE_NOT_FOUND",
                        message=f"Referenced role not found: {role_id} v{version}",
                        details={"role_prompt_ref": role_ref},
                    )

        # Validate template reference
        template_ref = manifest.get("template_ref")
        if template_ref:
            if not self._validate_ref_format(template_ref, "template"):
                report.add_error(
                    rule_id="INVALID_TEMPLATE_REF",
                    message=f"Invalid template reference format: {template_ref}. "
                            "Expected: prompt:template:<template_id>:<version>",
                    details={"template_ref": template_ref},
                )
            else:
                # Check if template exists
                parts = template_ref.split(":")
                template_id = parts[2]
                version = parts[3]
                try:
                    self._loader.get_template(template_id, version)
                except (PackageNotFoundError, VersionNotFoundError):
                    report.add_error(
                        rule_id="TEMPLATE_NOT_FOUND",
                        message=f"Referenced template not found: {template_id} v{version}",
                        details={"template_ref": template_ref},
                    )

    def _validate_ref_format(self, ref: str, ref_type: str) -> bool:
        """Validate reference format."""
        parts = ref.split(":")
        if len(parts) != 4:
            return False
        if parts[0] != "prompt":
            return False
        if parts[1] != ref_type:
            return False
        return True

    # =========================================================================
    # Cross-Package Validation
    # =========================================================================

    def validate_activation(
        self,
        doc_type_id: str,
        version: str,
    ) -> ValidationReport:
        """
        Validate that a release can be activated.

        Checks cross-package dependency closure:
        - All required_inputs have active releases
        - All shared artifact references resolve

        Args:
            doc_type_id: Document type to activate
            version: Version to activate

        Returns:
            ValidationReport with all findings
        """
        report = ValidationReport(valid=True)

        # Load the package
        try:
            package = self._loader.get_document_type(doc_type_id, version)
        except PackageNotFoundError:
            report.add_error(
                rule_id="PACKAGE_NOT_FOUND",
                message=f"Document type not found: {doc_type_id}",
                details={"doc_type_id": doc_type_id, "version": version},
            )
            return report
        except VersionNotFoundError:
            report.add_error(
                rule_id="VERSION_NOT_FOUND",
                message=f"Version not found: {version} for {doc_type_id}",
                details={"doc_type_id": doc_type_id, "version": version},
            )
            return report

        # Validate required inputs have active releases
        active = self._loader.get_active_releases()

        for required_input in package.required_inputs:
            if required_input not in active.document_types:
                report.add_error(
                    rule_id="REQUIRED_INPUT_NOT_ACTIVE",
                    message=f"Required input '{required_input}' has no active release. "
                            f"Activate {required_input} before activating {doc_type_id}.",
                    details={
                        "doc_type_id": doc_type_id,
                        "required_input": required_input,
                    },
                )

        # Validate role reference
        if package.role_prompt_ref:
            parts = package.role_prompt_ref.split(":")
            if len(parts) == 4:
                role_id = parts[2]
                role_version = parts[3]
                try:
                    self._loader.get_role(role_id, role_version)
                except (PackageNotFoundError, VersionNotFoundError):
                    report.add_error(
                        rule_id="ROLE_NOT_FOUND",
                        message=f"Referenced role not found: {role_id} v{role_version}",
                        details={"role_prompt_ref": package.role_prompt_ref},
                    )

        # Validate template reference
        if package.template_ref:
            parts = package.template_ref.split(":")
            if len(parts) == 4:
                template_id = parts[2]
                template_version = parts[3]
                try:
                    self._loader.get_template(template_id, template_version)
                except (PackageNotFoundError, VersionNotFoundError):
                    report.add_error(
                        rule_id="TEMPLATE_NOT_FOUND",
                        message=f"Referenced template not found: {template_id} v{template_version}",
                        details={"template_ref": package.template_ref},
                    )

        return report

    def validate_all_active_packages(self) -> ValidationReport:
        """
        Validate all currently active packages.

        Returns:
            ValidationReport with all findings across active packages
        """
        report = ValidationReport(valid=True)

        active = self._loader.get_active_releases()

        for doc_type_id, version in active.document_types.items():
            pkg_report = self.validate_activation(doc_type_id, version)
            if not pkg_report.valid:
                for error in pkg_report.errors:
                    # Add context about which package
                    error.message = f"[{doc_type_id}] {error.message}"
                report.merge(pkg_report)

        return report

    # =========================================================================
    # Schema Compatibility Validation
    # =========================================================================

    def validate_schema_compatibility(
        self,
        doc_type_id: str,
        old_version: str,
        new_version: str,
    ) -> ValidationReport:
        """
        Validate schema compatibility between versions.

        Detects breaking changes that require major version bump.

        Args:
            doc_type_id: Document type
            old_version: Previous version
            new_version: New version

        Returns:
            ValidationReport with compatibility findings
        """
        report = ValidationReport(valid=True)

        try:
            old_package = self._loader.get_document_type(doc_type_id, old_version)
            new_package = self._loader.get_document_type(doc_type_id, new_version)
        except (PackageNotFoundError, VersionNotFoundError) as e:
            report.add_warning(
                rule_id="SCHEMA_COMPARISON_SKIPPED",
                message=f"Could not compare schemas: {e}",
            )
            return report

        old_schema = old_package.get_schema()
        new_schema = new_package.get_schema()

        if not old_schema or not new_schema:
            return report

        # Check for removed required fields (breaking change)
        old_required = set(old_schema.get("required", []))
        new_required = set(new_schema.get("required", []))

        removed_required = old_required - new_required
        if removed_required:
            # This is actually not breaking - removing required makes it more flexible
            pass

        # Check for new required fields (breaking change)
        added_required = new_required - old_required
        if added_required:
            # Parse versions to check if major bump
            old_major = int(old_version.split(".")[0])
            new_major = int(new_version.split(".")[0])

            if new_major <= old_major:
                report.add_error(
                    rule_id="BREAKING_SCHEMA_CHANGE",
                    message=f"Adding required fields ({', '.join(added_required)}) is a breaking change. "
                            "Requires major version bump.",
                    details={
                        "added_required_fields": list(added_required),
                        "old_version": old_version,
                        "new_version": new_version,
                    },
                )

        # Check for removed properties (breaking change)
        old_props = set(old_schema.get("properties", {}).keys())
        new_props = set(new_schema.get("properties", {}).keys())

        removed_props = old_props - new_props
        if removed_props:
            old_major = int(old_version.split(".")[0])
            new_major = int(new_version.split(".")[0])

            if new_major <= old_major:
                report.add_error(
                    rule_id="BREAKING_SCHEMA_CHANGE",
                    message=f"Removing properties ({', '.join(removed_props)}) is a breaking change. "
                            "Requires major version bump.",
                    details={
                        "removed_properties": list(removed_props),
                        "old_version": old_version,
                        "new_version": new_version,
                    },
                )

        return report


# Module-level singleton
_validator: Optional[ConfigValidator] = None


def get_config_validator() -> ConfigValidator:
    """Get the singleton ConfigValidator instance."""
    global _validator
    if _validator is None:
        _validator = ConfigValidator()
    return _validator


def reset_config_validator() -> None:
    """Reset the singleton (for testing)."""
    global _validator
    _validator = None
