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


@register_handler
class MergerHandler(MechHandler):
    """
    Handler for merger operations.

    Combines multiple inputs into a single structured output.

    Config:
        inputs: List of {ref, key} objects defining inputs to merge
        merge_strategy: deep_merge | shallow_merge | concatenate
        output_shape: Schema for merged output (for validation)

    Example config:
        inputs:
          - ref: pass_a_output
            key: questions
          - ref: entry_output
            key: answers
        merge_strategy: deep_merge

    Merge strategies:
        - deep_merge: Recursively merge dicts, concatenate lists
        - shallow_merge: Top-level merge only, later values overwrite
        - concatenate: Combine all inputs into a single dict keyed by 'key'
    """

    operation_type = "merger"

    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> MechResult:
        """
        Execute the merge.

        Args:
            config: Merger configuration with inputs and strategy
            context: Execution context with input data

        Returns:
            MechResult with merged output
        """
        try:
            # Get inputs configuration
            inputs_config = config.get("inputs", [])
            if not inputs_config:
                return MechResult.fail(
                    error="No inputs configured",
                    error_code="transform_error",
                )

            # Collect inputs
            collected = []
            for input_spec in inputs_config:
                ref = input_spec.get("ref")
                key = input_spec.get("key")

                if not ref or not key:
                    continue

                if not context.has_input(ref):
                    logger.warning(f"Input {ref} not found in context")
                    # Use empty dict for missing inputs
                    collected.append({"key": key, "value": {}})
                else:
                    value = context.get_input(ref)
                    collected.append({"key": key, "value": value})

            if not collected:
                return MechResult.fail(
                    error="No inputs could be collected",
                    error_code="input_missing",
                )

            # Apply merge strategy
            strategy = config.get("merge_strategy", "deep_merge")

            if strategy == "deep_merge":
                merged = self._deep_merge(collected)
            elif strategy == "shallow_merge":
                merged = self._shallow_merge(collected)
            elif strategy == "concatenate":
                merged = self._concatenate(collected)
            else:
                return MechResult.fail(
                    error=f"Unknown merge strategy: {strategy}",
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

    def _deep_merge(self, collected: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Deep merge all collected inputs.

        For dict values: recursively merge
        For list values: concatenate
        For other values: later values overwrite
        """
        result = {}

        for item in collected:
            key = item["key"]
            value = item["value"]

            if key in result:
                # Merge with existing
                result[key] = self._merge_values(result[key], value)
            else:
                # Copy to avoid mutation
                result[key] = copy.deepcopy(value)

        return result

    def _merge_values(self, base: Any, override: Any) -> Any:
        """Recursively merge two values."""
        if isinstance(base, dict) and isinstance(override, dict):
            result = copy.deepcopy(base)
            for key, value in override.items():
                if key in result:
                    result[key] = self._merge_values(result[key], value)
                else:
                    result[key] = copy.deepcopy(value)
            return result
        elif isinstance(base, list) and isinstance(override, list):
            return base + override
        else:
            # Override wins
            return copy.deepcopy(override)

    def _shallow_merge(self, collected: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Shallow merge all collected inputs.

        Later values overwrite earlier ones at the top level.
        """
        result = {}

        for item in collected:
            key = item["key"]
            value = item["value"]
            result[key] = copy.deepcopy(value)

        return result

    def _concatenate(self, collected: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Concatenate all inputs into a dict keyed by their keys.

        This is the simplest strategy - just puts each input
        under its configured key.
        """
        result = {}

        for item in collected:
            key = item["key"]
            value = item["value"]
            result[key] = copy.deepcopy(value)

        return result

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
