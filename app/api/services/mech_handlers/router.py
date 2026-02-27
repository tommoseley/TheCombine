"""
Router Handler - maps intake classification to POW reference.

Per ADR-048, the router evaluates routing rules against intake
classification fields and produces a routing_decision with the
selected POW and all candidates considered.
"""

import logging
import uuid
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
class RouterHandler(MechHandler):
    """
    Handler for router operations.

    Maps intake classification to a follow-on POW reference using
    config-driven routing rules.

    Config:
        classification_fields: Fields to extract from intake for matching
        min_confidence_to_auto_route: Threshold for auto-routing (low/medium/high)
        routes: List of routing rules with match conditions and POW refs
        output_schema: Schema for routing_decision output

    Example config:
        routes:
          - name: "Software Product"
            match:
              project_type: ["greenfield", "enhancement"]
            pow_ref: "pow:software_product_development@1.0.0"
            confidence: high
            reason: "Standard software delivery"
    """

    operation_type = "router"

    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
    ) -> MechResult:
        """
        Execute the routing decision.

        Args:
            config: Router configuration with routes
            context: Execution context with intake_record input

        Returns:
            MechResult with routing_decision
        """
        try:
            # Get intake record - try multiple input names
            intake = None
            for input_name in ["concierge_intake", "intake_record", "source_document"]:
                if context.has_input(input_name):
                    intake = context.get_input(input_name)
                    break

            if not intake:
                return MechResult.fail(
                    error="No intake_record or source_document in context",
                    error_code="input_missing",
                )

            if not isinstance(intake, dict):
                return MechResult.fail(
                    error=f"intake must be a dict, got {type(intake).__name__}",
                    error_code="transform_error",
                )

            # Extract classification fields
            classification = self._extract_classification(intake, config)
            logger.info(f"Router: extracted classification = {classification}")

            # Evaluate all routes and score candidates
            routes = config.get("routes", [])
            candidates = []

            for route in routes:
                score = self._score_route(route, classification)
                candidates.append({
                    "pow_ref": route.get("pow_ref"),
                    "score": score,
                    "why": route.get("reason", route.get("name", "No reason provided")),
                    "name": route.get("name"),
                    "configured_confidence": route.get("confidence", "medium"),
                })

            # Sort by score descending
            candidates.sort(key=lambda c: c["score"], reverse=True)

            if not candidates:
                return MechResult.fail(
                    error="No routing rules configured",
                    error_code="transform_error",
                )

            # Winner is highest scoring candidate
            winner = candidates[0]

            # Determine confidence based on score and configured confidence
            confidence = self._determine_confidence(winner, candidates)

            # Build routing decision
            # Get intake ref if available (optional)
            intake_ref = "unknown"
            if context.has_input("intake_ref"):
                intake_ref = context.get_input("intake_ref")

            routing_decision = {
                "schema_version": "routing_decision.v1",
                "correlation_id": str(uuid.uuid4()),
                "source_intake_ref": intake_ref,
                "decision": {
                    "next_pow_ref": winner["pow_ref"],
                    "confidence": confidence,
                    "reason": winner["why"],
                    "operator_confirmed": False,
                    "confirmation_note": None,
                },
                "candidates": [
                    {
                        "pow_ref": c["pow_ref"],
                        "score": c["score"],
                        "why": c["why"],
                    }
                    for c in candidates
                ],
                "qa": {
                    "has_winner": True,
                    "winner_in_candidates": True,
                },
            }

            logger.info(
                f"Router: selected {winner['pow_ref']} with confidence={confidence}"
            )

            return MechResult.ok(output=routing_decision)

        except Exception as e:
            logger.exception(f"Router failed: {e}")
            return MechResult.fail(
                error=str(e),
                error_code="transform_error",
            )

    def _extract_classification(
        self,
        intake: Dict[str, Any],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract classification fields from intake."""
        classification = {}

        # Use configured field paths if provided
        field_paths = config.get("classification_fields", [])
        if field_paths:
            for field_spec in field_paths:
                path = field_spec.get("path")
                output_key = field_spec.get("as")
                if path and output_key:
                    try:
                        jsonpath_expr = jsonpath_parse(path)
                        matches = jsonpath_expr.find(intake)
                        if matches:
                            classification[output_key] = matches[0].value
                    except JsonPathParserError:
                        pass
        else:
            # Default: extract common classification fields directly
            for key in ["project_type", "artifact_type", "audience", "classification", "confidence"]:
                if key in intake:
                    classification[key] = intake[key]

        return classification

    def _score_route(
        self,
        route: Dict[str, Any],
        classification: Dict[str, Any],
    ) -> float:
        """
        Score how well a route matches the classification.

        Returns 0.0-1.0 score based on match conditions.
        """
        match_conditions = route.get("match", {})

        if not match_conditions:
            # Empty match = fallback, low score
            return 0.1

        matches = 0
        total_conditions = len(match_conditions)

        for field, expected_values in match_conditions.items():
            actual_value = classification.get(field)

            if actual_value is None:
                continue

            # Normalize expected to list
            if not isinstance(expected_values, list):
                expected_values = [expected_values]

            if actual_value in expected_values:
                matches += 1

        if total_conditions == 0:
            return 0.1

        # Base score from match ratio
        match_ratio = matches / total_conditions

        # Bonus for configured confidence
        confidence_bonus = {
            "high": 0.1,
            "medium": 0.05,
            "low": 0.0,
        }.get(route.get("confidence", "medium"), 0.05)

        return min(1.0, match_ratio * 0.9 + confidence_bonus)

    def _determine_confidence(
        self,
        winner: Dict[str, Any],
        candidates: List[Dict[str, Any]],
    ) -> str:
        """
        Determine final confidence level.

        Considers:
        - Winner's score
        - Gap between winner and runner-up
        - Configured confidence
        """
        winner_score = winner["score"]
        configured = winner.get("configured_confidence", "medium")

        # If score is very low, confidence is low regardless of config
        if winner_score < 0.3:
            return "low"

        # If there's a close runner-up, reduce confidence
        if len(candidates) > 1:
            runner_up_score = candidates[1]["score"]
            gap = winner_score - runner_up_score
            if gap < 0.1:
                # Very close, reduce confidence
                if configured == "high":
                    return "medium"
                return "low"

        # If score is high and gap is clear, use configured confidence
        if winner_score > 0.7:
            return configured

        # Medium score = medium confidence at best
        if configured == "high":
            return "medium"

        return configured

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate router configuration."""
        errors = []

        routes = config.get("routes")
        if not routes:
            errors.append("routes is required")
        elif not isinstance(routes, list):
            errors.append("routes must be a list")
        else:
            for i, route in enumerate(routes):
                if not isinstance(route, dict):
                    errors.append(f"routes[{i}] must be an object")
                    continue
                if not route.get("pow_ref"):
                    errors.append(f"routes[{i}].pow_ref is required")

        return errors
