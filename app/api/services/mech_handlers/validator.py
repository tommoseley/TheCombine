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


# ---------------------------------------------------------------------------
# Pure functions (extracted for testability — WS-CRAP-004)
# ---------------------------------------------------------------------------

# Known POW refs that are considered valid
KNOWN_POW_REFS = {
    "pow:software_product_development@1.0.0",
    "pow:problem_discovery@1.0.0",
    "pow:change_and_migration@1.0.0",
    "pow:integration_delivery@1.0.0",
    "pow:document_factory@1.0.0",
}


def is_pow_ref_resolvable(
    pow_ref: str,
    must_resolve: bool = True,
    known_refs: set = None,
) -> bool:
    """Check if a POW reference can be resolved.

    Pure function — no I/O, no side effects.

    Args:
        pow_ref: POW reference string
        must_resolve: Whether the ref must be in the known list
        known_refs: Set of known valid POW refs (defaults to KNOWN_POW_REFS)

    Returns:
        True if the POW ref is resolvable
    """
    if not pow_ref:
        return False

    refs = known_refs if known_refs is not None else KNOWN_POW_REFS

    if pow_ref in refs:
        return True

    if not must_resolve:
        return pow_ref.startswith("pow:")

    return False


def validate_field(
    data: Dict[str, Any],
    field_config: Dict[str, Any],
    global_config: Dict[str, Any] = None,
) -> Dict[str, str] | None:
    """Validate a single field against its check rule.

    Pure function — no I/O, no side effects.

    Args:
        data: Input data dict to validate against
        field_config: Field validation config with path, check, error_code, error_message
        global_config: Global validator config (for pow_ref_resolvable)

    Returns:
        Error dict with 'code' and 'message', or None if valid
    """
    global_config = global_config or {}
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
        must_resolve = global_config.get("must_resolve_pow_ref", True)
        if not is_pow_ref_resolvable(value, must_resolve=must_resolve):
            return {"code": error_code, "message": error_message}

    return None


# ---------------------------------------------------------------------------
# Handler class
# ---------------------------------------------------------------------------

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

    operation_type = "validator"

    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> MechResult:
        """Execute validation checks."""
        try:
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

            validate_fields_config = config.get("validate_fields", [])
            errors = []

            for fc in validate_fields_config:
                error = validate_field(input_data, fc, config)
                if error:
                    errors.append(error)

            if errors:
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

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate validator configuration."""
        errors = []

        validate_fields = config.get("validate_fields")
        if validate_fields and not isinstance(validate_fields, list):
            errors.append("validate_fields must be a list")

        return errors
