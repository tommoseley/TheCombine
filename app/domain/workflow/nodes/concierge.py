"""Concierge node executor for Document Interaction Workflow Plans (ADR-039).

Concierge nodes manage conversational clarification via LLM.

STRICT BOUNDARY CONSTRAINTS (WS-INTAKE-ENGINE-001):

ConciergeNodeExecutor MAY:
- Ask clarification questions
- Accept user responses
- Update workflow-local context (conversation state)
- Append messages to the owned thread

ConciergeNodeExecutor MUST NOT:
- Choose workflow routing options
- Infer next steps or suggest paths
- Bypass EdgeRouter constraints
- Make autonomous decisions about workflow progression

The Concierge asks questions; it does not decide what happens next.
"""

import logging
from typing import Any, Dict, List, Optional

from app.domain.workflow.nodes.base import (
    DocumentWorkflowContext,
    LLMService,
    NodeExecutor,
    NodeResult,
    PromptLoader,
)

logger = logging.getLogger(__name__)


class ConciergeNodeExecutor(NodeExecutor):
    """Executor for concierge nodes.

    Concierge nodes:
    - Manage conversational clarification
    - Collect information through questions
    - Build conversation context for downstream tasks

    INVARIANT: This executor does NOT make routing decisions.
    It reports outcomes; EdgeRouter decides what happens next.
    """

    def __init__(
        self,
        llm_service: LLMService,
        prompt_loader: PromptLoader,
    ):
        """Initialize with dependencies.

        Args:
            llm_service: Service for LLM completions
            prompt_loader: Service for loading prompts
        """
        self.llm_service = llm_service
        self.prompt_loader = prompt_loader

    def get_supported_node_type(self) -> str:
        """Return the node type this executor handles."""
        return "concierge"

    async def execute(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        context: DocumentWorkflowContext,
        state_snapshot: Dict[str, Any],
    ) -> NodeResult:
        """Execute a concierge node.

        Args:
            node_id: The concierge node ID
            node_config: Node configuration with task_ref
            context: Workflow context with conversation history
            state_snapshot: Read-only workflow state

        Returns:
            NodeResult with outcome:
            - "success": Ready to proceed (user indicated completion)
            - "needs_user_input": Awaiting user response
            - "out_of_scope": Request is out of scope
            - "redirect": Request should be redirected
        """
        task_ref = node_config.get("task_ref")

        # Check for user's latest response
        response_key = f"concierge_{node_id}_response"
        user_response = context.get_user_response(response_key)

        # Check if user wants to proceed
        proceed_key = f"concierge_{node_id}_proceed"
        wants_to_proceed = context.get_user_response(proceed_key)

        if wants_to_proceed:
            # User explicitly indicated they're ready to proceed
            logger.info(f"Concierge {node_id}: User ready to proceed")
            return NodeResult(
                outcome="success",
                metadata={
                    "node_id": node_id,
                    "conversation_turns": len(context.conversation_history),
                },
            )

        try:
            # Load concierge prompt
            system_prompt = None
            if task_ref:
                system_prompt = self.prompt_loader.load_task_prompt(task_ref)

            # Build messages
            messages = self._build_messages(context, user_response)

            # Get LLM response
            assistant_response = await self.llm_service.complete(
                messages=messages,
                system_prompt=system_prompt,
            )

            # Add assistant response to conversation history
            context.add_message("assistant", assistant_response)

            # Analyze response for special outcomes
            outcome, metadata = self._analyze_response(assistant_response, node_id)

            if outcome in ("out_of_scope", "redirect"):
                # These are terminal-path outcomes
                return NodeResult(
                    outcome=outcome,
                    metadata=metadata,
                )

            # Default: waiting for more user input
            return NodeResult.needs_user_input(
                prompt=assistant_response,
                node_id=node_id,
                awaiting_clarification=True,
            )

        except Exception as e:
            logger.exception(f"Concierge node {node_id} failed: {e}")
            return NodeResult.failed(
                reason=str(e),
                node_id=node_id,
            )

    def _build_messages(
        self,
        context: DocumentWorkflowContext,
        user_response: Optional[str],
    ) -> List[Dict[str, str]]:
        """Build messages for LLM from conversation context.

        Args:
            context: Workflow context with conversation history
            user_response: Latest user response (if any)

        Returns:
            List of message dicts for LLM
        """
        messages = []

        # Include existing conversation history
        for msg in context.conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        # Add new user response if provided
        if user_response:
            messages.append({
                "role": "user",
                "content": user_response,
            })
            # Also add to context for persistence
            context.add_message("user", user_response)

        # If no messages, start with a greeting/initial question
        if not messages:
            messages.append({
                "role": "user",
                "content": "Hello, I'd like to start a new project.",
            })
            context.add_message("user", "Hello, I'd like to start a new project.")

        return messages

    def _analyze_response(
        self,
        response: str,
        node_id: str,
    ) -> tuple[str, Dict[str, Any]]:
        """Analyze assistant response for special outcomes.

        This is a simple heuristic analysis. It does NOT make routing decisions;
        it only identifies when the conversation indicates special outcomes.

        Args:
            response: The assistant's response
            node_id: The node ID for metadata

        Returns:
            Tuple of (outcome, metadata)
        """
        response_lower = response.lower()
        metadata = {"node_id": node_id}

        # Check for out-of-scope indicators
        out_of_scope_phrases = [
            "out of scope",
            "outside the scope",
            "cannot help with",
            "not something we can assist",
            "beyond our capabilities",
        ]
        if any(phrase in response_lower for phrase in out_of_scope_phrases):
            metadata["detected_outcome"] = "out_of_scope"
            return "out_of_scope", metadata

        # Check for redirect indicators
        redirect_phrases = [
            "redirect you to",
            "better suited for",
            "recommend contacting",
            "different service",
            "another team",
        ]
        if any(phrase in response_lower for phrase in redirect_phrases):
            metadata["detected_outcome"] = "redirect"
            return "redirect", metadata

        # Default: continue conversation
        return "needs_user_input", metadata
