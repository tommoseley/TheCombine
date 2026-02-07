"""
Validator Handler - validates inputs against configurable rules.

Per ADR-048, validators perform fail-fast checks before operations
that have side effects (like spawning a POW).
"""

import logging
from typing import Any, Dict, List

from jsonpath_ng import parse as jsonpath_parse
from jsonpath_ng.exceptions import JsonPathParserError

from app.api.services.mech_handlers.base import (
    MechHandler,
    MechResult,
    ExecutionContext,
)
from app.api.services.mech_handlers.registry import register_handler

logger = logging.getLogger(__name__)


@register_handler
class ValidatorHandler(MechHandler):
    """
    Handler for validator operations.

    Validates inputs against configurable rules. Returns success with
    no output if valid, or fails with error details if invalid.

    Config:
        validate_fields: List of field validations
            - path: JSONPath to the field
            - check: Type of check (enum, equals, pow_ref_resolvable, required)
            - error_code: Machine-readable error code
            - error_message: Human-readable error message

    Example config:
        validate_fields:
          - path: $.decision.confidence
            check: enum
            allowed: ["low", "medium", "high"]
            error_code: "invalid_confidence"
            error_message: "Confidence must be low, medium, or high"
    """

    operation_type = "validator"

    # Known POW refs that are considered valid
    # In production, this would check against active_releases.json
    KNOWN_POW_REFS = {
        "pow:software_product_development@1.0.0",
        "pow:problem_discovery@1.0.0",
        "pow:change_and_migration@1.0.0",
        "pow:integration_delivery@1.0.0",
        "pow:document_factory@1.0.0",
    }

    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> MechResult:
        """
        Execute validation checks.

        Args:
            config: Validator configuration with rules
            context: Execution context with inputs

        Returns:
            MechResult - success with empty output if valid, fail if invalid
        """
        try:
            # Get the input to validate (typically routing_decision)
            input_data = None
            for key in ["routing_decision", "source_document", "input"]:
                if context.has_input(key):
                    input_data = context.get_input(key)
                    break

            if input_data is None:
                return MechResult.fail(
                    error="No input to validate",
                    error_code="input_missing",
                )

            if not isinstance(input_data, dict):
                return MechResult.fail(
                    error=f"Input must be a dict, got {type(input_data).__name__}",
                    error_code="invalid_input_type",
                )

            # Run validation checks
            validate_fields = config.get("validate_fields", [])
            errors = []

            for field_config in validate_fields:
                error = self._validate_field(input_data, field_config, config)
                if error:
                    errors.append(error)

            if errors:
                # Return first error (could aggregate in future)
                first_error = errors[0]
                return MechResult.fail(
                    error=first_error["message"],
                    error_code=first_error["code"],
                )

            logger.info("Validator: all checks passed")
            return MechResult.ok(output={})

        except Exception as e:
            logger.exception(f"Validator failed: {e}")
            return MechResult.fail(
                error=str(e),
                error_code="validation_error",
            )

    def _validate_field(
        self,
        data: Dict[str, Any],
        field_config: Dict[str, Any],
        global_config: Dict[str, Any],
    ) -> Dict[str, str] | None:
        """
        Validate a single field.

        Returns:
            Error dict with 'code' and 'message', or None if valid
        """
        path = field_config.get("path")
        check = field_config.get("check")
        error_code = field_config.get("error_code", "validation_failed")
        error_message = field_config.get("error_message", "Validation failed")

        # Extract value using JSONPath
        value = None
        try:
            jsonpath_expr = jsonpath_parse(path)
            matches = jsonpath_expr.find(data)
            if matches:
                value = matches[0].value
        except JsonPathParserError:
            return {"code": "invalid_path", "message": f"Invalid path: {path}"}

        # Run check
        if check == "required":
            if value is None:
                return {"code": error_code, "message": error_message}

        elif check == "enum":
            allowed = field_config.get("allowed", [])
            if value not in allowed:
                return {"code": error_code, "message": error_message}

        elif check == "equals":
            expected = field_config.get("expected")
            if value != expected:
                return {"code": error_code, "message": error_message}

        elif check == "pow_ref_resolvable":
            if not self._is_pow_ref_resolvable(value, global_config):
                return {"code": error_code, "message": error_message}

        return None

    def _is_pow_ref_resolvable(
        self,
        pow_ref: str,
        config: Dict[str, Any],
    ) -> bool:
        """
        Check if a POW reference can be resolved.

        In production, this would check against PackageLoader or active_releases.
        For now, we check against a known list.
        """
        if not pow_ref:
            return False

        # Check against known refs
        if pow_ref in self.KNOWN_POW_REFS:
            return True

        # Also accept any pow: ref if must_resolve_pow_ref is false
        if not config.get("must_resolve_pow_ref", True):
            return pow_ref.startswith("pow:")

        # Unknown ref
        logger.warning(f"Unknown POW ref: {pow_ref}")
        return False

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate validator configuration."""
        errors = []

        validate_fields = config.get("validate_fields")
        if validate_fields and not isinstance(validate_fields, list):
            errors.append("validate_fields must be a list")

        return errors
