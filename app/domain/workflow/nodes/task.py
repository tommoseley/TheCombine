"""Task node executor for Document Interaction Workflow Plans (ADR-039).

Task nodes generate documents via LLM completion.
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


class TaskNodeExecutor(NodeExecutor):
    """Executor for task nodes.

    Task nodes:
    - Load a task prompt (task_ref)
    - Execute LLM completion with input context
    - Produce a document artifact (produces)

    BOUNDARY CONSTRAINTS:
    - Returns outcome "success" or "failed"
    - Does NOT inspect edges or make routing decisions
    - Does NOT mutate workflow control state
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
        return "task"

    async def execute(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        context: DocumentWorkflowContext,
        state_snapshot: Dict[str, Any],
    ) -> NodeResult:
        """Execute a task node.

        Args:
            node_id: The task node ID
            node_config: Node configuration including task_ref and produces
            context: Workflow context with input documents
            state_snapshot: Read-only workflow state

        Returns:
            NodeResult with outcome "success" or "failed"
        """
        task_ref = node_config.get("task_ref")
        produces = node_config.get("produces")

        if not task_ref:
            logger.error(f"Task node {node_id} missing task_ref")
            return NodeResult.failed(
                reason=f"Task node {node_id} missing task_ref configuration"
            )

        try:
            # Load task prompt
            task_prompt = self.prompt_loader.load_task_prompt(task_ref)

            # Build messages from context
            messages = self._build_messages(task_prompt, context)

            # Execute LLM completion
            response = await self.llm_service.complete(messages)

            # Parse and store produced document
            produced_document = self._parse_response(response, produces)

            # Update context with produced document
            if produces:
                context.document_content[produces] = produced_document

            logger.info(f"Task node {node_id} completed successfully")

            return NodeResult.success(
                produced_document=produced_document,
                task_ref=task_ref,
                produces=produces,
            )

        except Exception as e:
            logger.exception(f"Task node {node_id} failed: {e}")
            return NodeResult.failed(
                reason=str(e),
                task_ref=task_ref,
            )

    def _build_messages(
        self,
        task_prompt: str,
        context: DocumentWorkflowContext,
    ) -> List[Dict[str, str]]:
        """Build LLM messages from task prompt and context.

        Args:
            task_prompt: The task prompt template
            context: Workflow context with conversation history

        Returns:
            List of message dicts for LLM
        """
        messages = []

        # Include conversation history if present
        for msg in context.conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        # Add input documents as context
        if context.input_documents:
            input_context = self._format_input_documents(context.input_documents)
            messages.append({
                "role": "user",
                "content": f"Input Context:\n{input_context}",
            })

        # Add task prompt
        messages.append({
            "role": "user",
            "content": task_prompt,
        })

        return messages

    def _format_input_documents(
        self,
        input_documents: Dict[str, Dict[str, Any]],
    ) -> str:
        """Format input documents as context string.

        Args:
            input_documents: Dict of document_type -> document content

        Returns:
            Formatted string representation
        """
        parts = []
        for doc_type, content in input_documents.items():
            parts.append(f"## {doc_type}\n{self._serialize_document(content)}")
        return "\n\n".join(parts)

    def _serialize_document(self, content: Dict[str, Any]) -> str:
        """Serialize document content to string.

        Args:
            content: Document content dict

        Returns:
            String representation
        """
        import json
        return json.dumps(content, indent=2, default=str)

    def _parse_response(
        self,
        response: str,
        produces: Optional[str],
    ) -> Dict[str, Any]:
        """Parse LLM response into document content.

        Args:
            response: Raw LLM response
            produces: Document type being produced

        Returns:
            Parsed document content
        """
        import json

        # Try to parse as JSON
        try:
            # Look for JSON block in response
            if "```json" in response:
                start = response.index("```json") + 7
                end = response.index("```", start)
                json_str = response[start:end].strip()
                return json.loads(json_str)
            elif response.strip().startswith("{"):
                return json.loads(response)
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: return as raw content
        return {
            "type": produces or "unknown",
            "content": response,
            "raw": True,
        }
