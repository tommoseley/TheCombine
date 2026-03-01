"""
Extractor Handler - extracts structured fields from documents.

Per ADR-047, extractors use JSONPath expressions to pull specific
fields from documents.
"""

import logging
from typing import Any, Dict, List

from jsonpath_ng import parse as jsonpath_parse
from jsonpath_ng.exceptions import JsonPathParserError

from app.api.services.mech_handlers.base import (
    MechHandler,
    MechResult,
    ExecutionContext,
    TransformError,
    InputMissingError,
)
from app.api.services.mech_handlers.registry import register_handler

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure functions (extracted for testability — WS-CRAP-004)
# ---------------------------------------------------------------------------

def extract_jsonpath(source: Dict[str, Any], path: str) -> Any:
    """Extract a value from a dict using JSONPath.

    Pure function — no I/O, no side effects.

    Args:
        source: Source document dict
        path: JSONPath expression

    Returns:
        Extracted value, list of values (for multiple matches), or None

    Raises:
        TransformError: If JSONPath expression is invalid
    """
    try:
        jsonpath_expr = jsonpath_parse(path)
    except JsonPathParserError as e:
        raise TransformError(f"Invalid JSONPath '{path}': {e}")

    matches = jsonpath_expr.find(source)

    if not matches:
        return None

    if len(matches) == 1:
        return matches[0].value

    return [match.value for match in matches]


def extract_fields(source: Dict[str, Any], field_paths: list) -> Dict[str, Any]:
    """Extract multiple fields from a document using JSONPath specs.

    Pure function — no I/O, no side effects.

    Args:
        source: Source document dict
        field_paths: List of {"path": str, "as": str} extraction specs

    Returns:
        Dict of extracted values keyed by output name
    """
    extracted = {}
    for field_spec in field_paths:
        path = field_spec.get("path")
        output_key = field_spec.get("as")

        if not path or not output_key:
            continue

        try:
            value = extract_jsonpath(source, path)
            extracted[output_key] = value
        except TransformError:
            extracted[output_key] = None

    return extracted


# ---------------------------------------------------------------------------
# Handler class
# ---------------------------------------------------------------------------

@register_handler
class ExtractorHandler(MechHandler):
    """
    Handler for extractor operations.

    Extracts structured fields from a document using JSONPath expressions.

    Config:
        source_type: Document type to extract from (informational)
        field_paths: List of {path, as} objects defining extractions
        output_shape: Schema for extracted structure (for validation)

    Example config:
        field_paths:
          - path: $.project_summary
            as: summary
          - path: $.identified_constraints
            as: constraints
    """

    operation_type = "extractor"

    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> MechResult:
        """Execute the extraction."""
        try:
            if not context.has_input("source_document"):
                return MechResult.fail(
                    error="No source_document in context",
                    error_code="input_missing",
                )

            source = context.get_input("source_document")

            if not isinstance(source, dict):
                return MechResult.fail(
                    error=f"source_document must be a dict, got {type(source).__name__}",
                    error_code="transform_error",
                )

            fp = config.get("field_paths", [])
            if not fp:
                return MechResult.fail(
                    error="No field_paths configured",
                    error_code="transform_error",
                )

            extracted = extract_fields(source, fp)
            return MechResult.ok(output=extracted)

        except InputMissingError as e:
            return MechResult.fail(
                error=str(e),
                error_code="input_missing",
            )
        except Exception as e:
            logger.exception(f"Extractor failed: {e}")
            return MechResult.fail(
                error=str(e),
                error_code="transform_error",
            )

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate extractor configuration."""
        errors = []

        field_paths = config.get("field_paths")
        if not field_paths:
            errors.append("field_paths is required")
        elif not isinstance(field_paths, list):
            errors.append("field_paths must be a list")
        else:
            for i, fp in enumerate(field_paths):
                if not isinstance(fp, dict):
                    errors.append(f"field_paths[{i}] must be an object")
                    continue
                if not fp.get("path"):
                    errors.append(f"field_paths[{i}].path is required")
                if not fp.get("as"):
                    errors.append(f"field_paths[{i}].as is required")

        return errors
