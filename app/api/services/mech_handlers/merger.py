"""
Merger Handler - combines multiple inputs into a single output.

Per ADR-047, mergers combine multiple inputs using configurable
merge strategies.
"""

import copy
import logging
from typing import Any, Dict, List

from app.api.services.mech_handlers.base import (
    MechHandler,
    MechResult,
    ExecutionContext,
    InputMissingError,
)
from app.api.services.mech_handlers.registry import register_handler

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure functions (extracted for testability — WS-CRAP-004)
# ---------------------------------------------------------------------------

def merge_values(base: Any, override: Any) -> Any:
    """Recursively merge two values.

    Pure function — no I/O, no side effects.
    Deep-copies internally to avoid mutation.

    - dict + dict: recursive merge
    - list + list: concatenate
    - other: override wins
    """
    if isinstance(base, dict) and isinstance(override, dict):
        result = copy.deepcopy(base)
        for key, value in override.items():
            if key in result:
                result[key] = merge_values(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result
    elif isinstance(base, list) and isinstance(override, list):
        return base + override
    else:
        return copy.deepcopy(override)


def deep_merge_collected(collected: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Deep merge all collected inputs.

    Pure function — no I/O, no side effects.

    Args:
        collected: List of {"key": str, "value": Any} dicts

    Returns:
        Merged dict keyed by input keys
    """
    result = {}

    for item in collected:
        key = item["key"]
        value = item["value"]

        if key in result:
            result[key] = merge_values(result[key], value)
        else:
            result[key] = copy.deepcopy(value)

    return result


def shallow_merge_collected(collected: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Shallow merge all collected inputs (later values overwrite).

    Pure function — no I/O, no side effects.
    """
    result = {}
    for item in collected:
        result[item["key"]] = copy.deepcopy(item["value"])
    return result


def concatenate_collected(collected: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Concatenate all inputs into a dict keyed by their keys.

    Pure function — no I/O, no side effects.
    """
    result = {}
    for item in collected:
        result[item["key"]] = copy.deepcopy(item["value"])
    return result


MERGE_STRATEGIES = {
    "deep_merge": deep_merge_collected,
    "shallow_merge": shallow_merge_collected,
    "concatenate": concatenate_collected,
}


def merge_collected(collected: List[Dict[str, Any]], strategy: str) -> Dict[str, Any]:
    """Merge collected inputs using the specified strategy.

    Pure function — no I/O, no side effects.

    Args:
        collected: List of {"key": str, "value": Any} dicts
        strategy: One of "deep_merge", "shallow_merge", "concatenate"

    Returns:
        Merged dict

    Raises:
        ValueError: If strategy is unknown
    """
    merge_fn = MERGE_STRATEGIES.get(strategy)
    if not merge_fn:
        raise ValueError(f"Unknown merge strategy: {strategy}")
    return merge_fn(collected)


# ---------------------------------------------------------------------------
# Handler class
# ---------------------------------------------------------------------------

@register_handler
class MergerHandler(MechHandler):
    """Handler for merger operations.

    Combines multiple inputs into a single structured output using
    configurable merge strategies.
    """

    operation_type = "merger"

    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> MechResult:
        """Execute the merge."""
        try:
            inputs_config = config.get("inputs", [])
            if not inputs_config:
                return MechResult.fail(
                    error="No inputs configured",
                    error_code="transform_error",
                )

            collected = []
            for input_spec in inputs_config:
                ref = input_spec.get("ref")
                key = input_spec.get("key")

                if not ref or not key:
                    continue

                if not context.has_input(ref):
                    logger.warning(f"Input {ref} not found in context")
                    collected.append({"key": key, "value": {}})
                else:
                    value = context.get_input(ref)
                    collected.append({"key": key, "value": value})

            if not collected:
                return MechResult.fail(
                    error="No inputs could be collected",
                    error_code="input_missing",
                )

            strategy = config.get("merge_strategy", "deep_merge")

            try:
                merged = merge_collected(collected, strategy)
            except ValueError as e:
                return MechResult.fail(
                    error=str(e),
                    error_code="transform_error",
                )

            return MechResult.ok(output=merged)

        except InputMissingError as e:
            return MechResult.fail(
                error=str(e),
                error_code="input_missing",
            )
        except Exception as e:
            logger.exception(f"Merger failed: {e}")
            return MechResult.fail(
                error=str(e),
                error_code="transform_error",
            )

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate merger configuration."""
        errors = []

        inputs = config.get("inputs")
        if not inputs:
            errors.append("inputs is required")
        elif not isinstance(inputs, list):
            errors.append("inputs must be a list")
        else:
            for i, inp in enumerate(inputs):
                if not isinstance(inp, dict):
                    errors.append(f"inputs[{i}] must be an object")
                    continue
                if not inp.get("ref"):
                    errors.append(f"inputs[{i}].ref is required")
                if not inp.get("key"):
                    errors.append(f"inputs[{i}].key is required")

        strategy = config.get("merge_strategy")
        if strategy and strategy not in ("deep_merge", "shallow_merge", "concatenate"):
            errors.append(f"Invalid merge_strategy: {strategy}")

        return errors
