"""Intake Gate executor for Document Interaction Workflows.

The Intake Gate replaces the multi-turn Concierge with a single-pass
classification and extraction mechanism.

DESIGN PRINCIPLES:
- Zero LLM calls when request is obviously actionable (fast path)
- Maximum one LLM call for classification + extraction
- No conversation - each submission evaluated fresh
- Clear outcomes: qualified / insufficient / out_of_scope / redirect

TOKEN EFFICIENCY:
- Fast path: 0 tokens (heuristic classification)
- LLM path: ~3-5k tokens (single call)
- Compare to Concierge: 15-50k tokens (multi-turn)
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.domain.workflow.nodes.base import (
    DocumentWorkflowContext,
    LLMService,
    NodeExecutor,
    NodeResult,
    PromptLoader,
)

logger = logging.getLogger(__name__)

# Fast path thresholds
MIN_SUBSTANTIAL_LENGTH = 200  # Characters for fast path consideration
MIN_STRUCTURE_INDICATORS = 2  # Newlines, bullets, or numbered items


class IntakeGateExecutor(NodeExecutor):
    """Executor for intake gate nodes.

    The intake gate classifies user requests and extracts structured fields
    in a single pass, replacing multi-turn conversational clarification.

    OUTCOMES:
    - "qualified": Request is actionable, proceed to discovery
    - "insufficient": Request needs more information (returns what's missing)
    - "out_of_scope": Request is outside supported scope
    - "redirect": Request should be handled elsewhere

    FAST PATH:
    When a request is clearly substantial (length + structure), the gate
    can proceed without an LLM call, extracting basic fields heuristically.
    """

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        prompt_loader: Optional[PromptLoader] = None,
    ):
        """Initialize with optional LLM dependencies.

        Args:
            llm_service: LLM service for classification (None = fast path only)
            prompt_loader: Prompt loader for intake gate prompt
        """
        self.llm_service = llm_service
        self.prompt_loader = prompt_loader

    def get_supported_node_type(self) -> str:
        """Return the node type this executor handles."""
        return "intake_gate"

    async def execute(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        context: DocumentWorkflowContext,
        state_snapshot: Dict[str, Any],
    ) -> NodeResult:
        """Execute the intake gate.

        Args:
            node_id: The gate node ID
            node_config: Node configuration with task_ref for prompt
            context: Workflow context with user input
            state_snapshot: Read-only workflow state

        Returns:
            NodeResult with classification outcome and extracted fields
        """
        # Get user input
        user_input = context.extra.get("user_input", "")

        if not user_input or not user_input.strip():
            # No input - need user to provide request
            logger.info(f"Intake gate {node_id}: No user input, requesting")
            return NodeResult.needs_user_input(
                prompt="Please describe what you'd like to build or accomplish.",
                node_id=node_id,
            )

        # Try fast path first (zero LLM calls)
        fast_result = self._try_fast_path(user_input, node_id)
        if fast_result:
            logger.info(f"Intake gate {node_id}: Fast path -> {fast_result.outcome}")
            return fast_result

        # Need LLM classification
        if not self.llm_service:
            # No LLM available - can only use fast path
            logger.warning(f"Intake gate {node_id}: No LLM service, defaulting to qualified")
            return self._build_qualified_result(
                node_id=node_id,
                intake_summary=user_input[:500],
                project_type="unknown",
                source="no_llm_fallback",
            )

        # Single LLM call for classification + extraction
        return await self._classify_with_llm(user_input, node_id, node_config)

    def _try_fast_path(
        self,
        user_input: str,
        node_id: str,
    ) -> Optional[NodeResult]:
        """Attempt fast path classification without LLM.

        Fast path triggers when:
        - Input is substantial (>= MIN_SUBSTANTIAL_LENGTH chars)
        - Input has structure (newlines, bullets, numbered items)

        Args:
            user_input: The user's request
            node_id: The gate node ID

        Returns:
            NodeResult if fast path applies, None otherwise
        """
        # Check length
        if len(user_input) < MIN_SUBSTANTIAL_LENGTH:
            return None

        # Check for structure indicators
        structure_score = 0

        # Newlines indicate structure
        if "\n" in user_input:
            structure_score += user_input.count("\n")

        # Bullet points
        if re.search(r"^[\s]*[-*•]", user_input, re.MULTILINE):
            structure_score += 2

        # Numbered items
        if re.search(r"^[\s]*\d+[.)]\s", user_input, re.MULTILINE):
            structure_score += 2

        # Multiple sentences
        sentence_count = len(re.findall(r"[.!?]+", user_input))
        if sentence_count >= 3:
            structure_score += 1

        if structure_score < MIN_STRUCTURE_INDICATORS:
            return None

        # Fast path applies - extract basic fields heuristically
        project_type = self._infer_project_type(user_input)
        intake_summary = self._extract_summary(user_input)

        logger.info(
            f"Intake gate {node_id}: Fast path triggered "
            f"(len={len(user_input)}, structure={structure_score})"
        )

        return self._build_qualified_result(
            node_id=node_id,
            intake_summary=intake_summary,
            project_type=project_type,
            source="fast_path",
            user_input=user_input,
        )

    def _infer_project_type(self, user_input: str) -> str:
        """Infer project type from user input heuristically.

        Args:
            user_input: The user's request

        Returns:
            Inferred project type
        """
        input_lower = user_input.lower()

        # Check for explicit greenfield indicators first (highest priority)
        greenfield_indicators = [
            "from scratch", "brand new", "new project", "no existing",
            "start fresh", "build new", "create new", "building new",
        ]
        if any(ind in input_lower for ind in greenfield_indicators):
            return "greenfield"

        # Check for migration indicators
        migration_indicators = [
            "migrate", "migration", "move from", "convert",
            "transition", "replace existing", "legacy",
        ]
        if any(ind in input_lower for ind in migration_indicators):
            return "migration"

        # Check for enhancement indicators
        enhancement_indicators = [
            "add to", "extend", "improve", "update existing",
            "modify existing", "enhance existing", "existing system",
            "current system", "already have", "we have",
        ]
        if any(ind in input_lower for ind in enhancement_indicators):
            return "enhancement"

        # Default to greenfield
        return "greenfield"

    def _extract_summary(self, user_input: str, max_length: int = 500) -> str:
        """Extract a summary from user input.

        Args:
            user_input: The user's request
            max_length: Maximum summary length

        Returns:
            Extracted summary
        """
        # Take first paragraph or first N characters
        paragraphs = user_input.split("\n\n")
        if paragraphs:
            first_para = paragraphs[0].strip()
            if len(first_para) >= 50:
                return first_para[:max_length]

        return user_input[:max_length]

    async def _classify_with_llm(
        self,
        user_input: str,
        node_id: str,
        node_config: Dict[str, Any],
    ) -> NodeResult:
        """Classify request using single LLM call.

        Args:
            user_input: The user's request
            node_id: The gate node ID
            node_config: Node configuration with task_ref

        Returns:
            NodeResult with classification outcome
        """
        task_ref = node_config.get("task_ref")

        # Load prompt
        system_prompt = ""
        if task_ref and self.prompt_loader:
            try:
                system_prompt = self.prompt_loader.load_task_prompt(task_ref)
            except Exception as e:
                logger.warning(f"Failed to load intake gate prompt: {e}")
                system_prompt = self._get_default_prompt()
        else:
            system_prompt = self._get_default_prompt()

        # Single message - no conversation
        messages = [{"role": "user", "content": user_input}]

        try:
            response = await self.llm_service.complete(
                messages=messages,
                system_prompt=system_prompt,
                node_id=node_id,
                task_ref=task_ref or "intake_gate",
            )

            # Parse LLM response
            return self._parse_llm_response(response, node_id, user_input)

        except Exception as e:
            logger.exception(f"Intake gate {node_id} LLM call failed: {e}")
            # Fail open - let it through with warning
            return self._build_qualified_result(
                node_id=node_id,
                intake_summary=user_input[:500],
                project_type="unknown",
                source="llm_error_fallback",
                error=str(e),
            )

    def _parse_llm_response(
        self,
        response: str,
        node_id: str,
        user_input: str,
    ) -> NodeResult:
        """Parse LLM classification response.

        Expected JSON format:
        {
            "classification": "qualified|insufficient|out_of_scope|redirect",
            "project_type": "greenfield|enhancement|migration|...",
            "intake_summary": "...",
            "missing": ["question1", ...],  // if insufficient
            "reason": "..."  // if out_of_scope or redirect
        }

        Args:
            response: Raw LLM response
            node_id: The gate node ID
            user_input: Original user input

        Returns:
            NodeResult based on classification
        """
        # Try to extract JSON from response
        try:
            # Handle markdown code blocks
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON object directly
                json_match = re.search(r"\{[\s\S]*\}", response)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise ValueError("No JSON found in response")

            data = json.loads(json_str)

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Intake gate {node_id}: Failed to parse LLM response: {e}")
            # Fallback: try to infer from response text
            return self._infer_from_text_response(response, node_id, user_input)

        classification = data.get("classification", "qualified")
        project_type = data.get("project_type", "unknown")
        intake_summary = data.get("intake_summary", user_input[:500])

        if classification == "qualified":
            return self._build_qualified_result(
                node_id=node_id,
                intake_summary=intake_summary,
                project_type=project_type,
                source="llm",
                extracted_data=data,
            )

        elif classification == "insufficient":
            missing = data.get("missing", ["Please provide more details about your request."])
            # Format missing items as a single prompt
            if isinstance(missing, list):
                prompt = "To proceed, please provide:\n" + "\n".join(f"- {m}" for m in missing)
            else:
                prompt = str(missing)

            return NodeResult.needs_user_input(
                prompt=prompt,
                node_id=node_id,
                classification="insufficient",
                missing=missing,
            )

        elif classification == "out_of_scope":
            reason = data.get("reason", "This request is outside the scope of supported projects.")
            return NodeResult(
                outcome="out_of_scope",
                metadata={
                    "node_id": node_id,
                    "reason": reason,
                    "classification": classification,
                },
            )

        elif classification == "redirect":
            reason = data.get("reason", "This request should be handled by a different service.")
            return NodeResult(
                outcome="redirect",
                metadata={
                    "node_id": node_id,
                    "reason": reason,
                    "classification": classification,
                },
            )

        else:
            # Unknown classification - default to qualified
            logger.warning(f"Intake gate {node_id}: Unknown classification '{classification}'")
            return self._build_qualified_result(
                node_id=node_id,
                intake_summary=intake_summary,
                project_type=project_type,
                source="llm_unknown_classification",
            )

    def _infer_from_text_response(
        self,
        response: str,
        node_id: str,
        user_input: str,
    ) -> NodeResult:
        """Infer classification from non-JSON response text.

        Args:
            response: Raw LLM response (not JSON)
            node_id: The gate node ID
            user_input: Original user input

        Returns:
            NodeResult based on inferred classification
        """
        response_lower = response.lower()

        # Check for out-of-scope indicators
        if any(phrase in response_lower for phrase in [
            "out of scope", "cannot help", "not supported", "outside"
        ]):
            return NodeResult(
                outcome="out_of_scope",
                metadata={
                    "node_id": node_id,
                    "reason": response[:500],
                    "source": "text_inference",
                },
            )

        # Check for insufficient indicators
        if any(phrase in response_lower for phrase in [
            "need more", "please provide", "clarify", "what do you mean"
        ]):
            return NodeResult.needs_user_input(
                prompt=response,
                node_id=node_id,
                classification="insufficient",
                source="text_inference",
            )

        # Default to qualified
        return self._build_qualified_result(
            node_id=node_id,
            intake_summary=user_input[:500],
            project_type="unknown",
            source="text_inference_fallback",
        )

    def _build_qualified_result(
        self,
        node_id: str,
        intake_summary: str,
        project_type: str,
        source: str,
        **extra_metadata: Any,
    ) -> NodeResult:
        """Build a qualified (success) result.

        Args:
            node_id: The gate node ID
            intake_summary: Extracted summary
            project_type: Inferred project type
            source: How classification was determined
            **extra_metadata: Additional metadata

        Returns:
            NodeResult with qualified outcome
        """
        return NodeResult(
            outcome="qualified",
            metadata={
                "node_id": node_id,
                "classification": "qualified",
                "intake_summary": intake_summary,
                "project_type": project_type,
                "source": source,
                **extra_metadata,
            },
        )

    def _get_default_prompt(self) -> str:
        """Get default intake gate prompt when none configured.

        Returns:
            Default system prompt for intake classification
        """
        return """You are an intake classifier for a software development service.

Analyze the user's request and respond with a JSON object:

{
    "classification": "qualified|insufficient|out_of_scope|redirect",
    "project_type": "greenfield|enhancement|migration",
    "intake_summary": "Brief summary of what the user wants to build",
    "missing": ["list", "of", "missing", "info"],  // only if insufficient
    "reason": "explanation"  // only if out_of_scope or redirect
}

CLASSIFICATION RULES:
- "qualified": Request is clear and actionable. We understand what to build.
- "insufficient": Request is too vague. List specific missing information.
- "out_of_scope": Request is for something we don't support (e.g., illegal, harmful).
- "redirect": Request should go to a different service (e.g., support, sales).

PROJECT TYPES:
- "greenfield": Building something new from scratch
- "enhancement": Adding to or improving existing software
- "migration": Moving from one system/technology to another

Be concise. Respond only with the JSON object."""
