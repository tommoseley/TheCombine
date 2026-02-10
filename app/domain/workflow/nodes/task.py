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
            # Check if node has includes (ADR-041 template assembly)
            includes = node_config.get("includes")
            prompt_sources = None  # Track source files for debugging
            if includes:
                # Use PromptAssemblyService for template assembly
                from app.domain.services.prompt_assembly_service import PromptAssemblyService
                from uuid import uuid4

                assembly_service = PromptAssemblyService()
                assembled = assembly_service.assemble(
                    task_ref=task_ref,
                    includes=includes,
                    correlation_id=str(uuid4()),
                )
                task_prompt = assembled.content
                prompt_sources = assembled.includes_resolved  # Capture source files
                logger.info(f"Task node {node_id} assembled prompt via ADR-041 ({len(task_prompt)} chars)")
            else:
                # Legacy: load task prompt directly
                task_prompt = self.prompt_loader.load_task_prompt(task_ref)

            # Build messages from context
            messages = self._build_messages(task_prompt, context)

            # Execute LLM completion with execution tracking
            execution_id = context.extra.get("execution_id")
            node_type = node_config.get("type", "task")
            
            # Determine role based on node type
            if node_type == "pgc":
                role = "PGC Generator"
            elif node_type == "generation" or produces:
                role = "Document Generator"
            else:
                role = f"Task: {node_id}"
            
            response = await self.llm_service.complete(
                messages,
                workflow_execution_id=execution_id,
                role=role,
                task_ref=task_ref,
                artifact_type=context.document_type,
                node_id=node_id,
                project_id=context.project_id,
                prompt_sources=prompt_sources,
            )

            # Parse and store produced document
            produced_document = self._parse_response(response, produces)

            # Debug: log what we got back
            logger.debug(f"Task node {node_id}: Response length={len(response)}, keys={list(produced_document.keys()) if isinstance(produced_document, dict) else 'not-dict'}")

            # Update context with produced document
            if produces:
                context.document_content[produces] = produced_document

            # PGC nodes return needs_user_input to pause for user answers
            node_type = node_config.get("type", "task")
            if node_type == "pgc":
                # Extract schema version for reference
                schema_version = produced_document.get("schema_version", "clarification_question_set.v2")
                schema_ref = f"schema://{schema_version}"
                
                # Payload is the structured object; prompt is optional human-readable rendering
                questions_prompt = self._format_pgc_questions(produced_document)
                logger.info(f"PGC node {node_id} completed - pausing for user input ({len(produced_document.get('questions', []))} questions), schema_ref={schema_ref}")
                return NodeResult(
                    outcome="needs_user_input",
                    produced_document=produced_document,
                    requires_user_input=True,
                    user_prompt=questions_prompt,  # Optional human-readable
                    user_input_payload=produced_document,  # Structured object
                    user_input_schema_ref=schema_ref,  # Schema reference
                    metadata={"task_ref": task_ref, "produces": produces},
                )
            
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
            context: Workflow context

        Returns:
            List of message dicts for LLM
        """
        messages = []

        # Build context from multiple sources (ADR-040 compliant)
        context_parts = []

        # 1. User's original request - check extra first, then context_state
        user_input = context.extra.get("user_input") or context.context_state.get("user_input")
        if user_input:
            context_parts.append(f"## User Request\n{user_input}")

        # 2. Bound constraints summary (ADR-042) - BEFORE JSON for prominence
        bound_summary = self._render_bound_constraints_summary(context.context_state)
        if bound_summary:
            context_parts.append(bound_summary)

        # 2b. QA feedback from previous failed attempt (if any)
        qa_feedback = context.context_state.get("qa_feedback")
        if qa_feedback:
            feedback_text = self._render_qa_feedback(qa_feedback)
            if feedback_text:
                context_parts.append(feedback_text)

        # 3. Structured context state (intake summary, project type, etc.)
        if context.context_state:
            relevant_state = {k: v for k, v in context.context_state.items()
                           if not k.startswith("document_") and k != "last_produced_document"}
            if relevant_state:
                import json
                context_parts.append(f"## Extracted Context\n{json.dumps(relevant_state, indent=2)}")

        # 4. Input documents from project (loaded via requires_inputs)
        if context.input_documents:
            input_context = self._format_input_documents(context.input_documents)
            context_parts.append(f"## Input Documents\n{input_context}")

        # 5. Produced documents from earlier nodes in this workflow
        if context.document_content:
            doc_context = self._format_input_documents(context.document_content)
            context_parts.append(f"## Previous Documents\n{doc_context}")

        # Add context as first message if we have any
        if context_parts:
            messages.append({
                "role": "user",
                "content": "\n\n".join(context_parts),
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

    def _render_bound_constraints_summary(
        self,
        context_state: Dict[str, Any],
    ) -> Optional[str]:
        """Render prominent human-readable summary of binding constraints.

        Per ADR-042: Bound constraints must be presented prominently so the LLM
        cannot miss them. This renders a natural-language summary BEFORE the
        JSON context dump to ensure the model sees settled decisions first.

        Args:
            context_state: The workflow context state

        Returns:
            Formatted summary string, or None if no invariants
        """
        invariants = context_state.get("pgc_invariants", [])
        if not invariants:
            return None

        lines = [
            "## Bound Constraints (FINAL â€” DO NOT REOPEN)",
            "These decisions are settled. Do not present alternatives or questions about them.",
            "",
        ]

        for inv in invariants:
            label = inv.get("user_answer_label") or str(inv.get("user_answer", ""))
            constraint_id = inv.get("id", "UNKNOWN")
            binding_source = inv.get("binding_source", "")

            # Add source annotation for exclusions
            if binding_source == "exclusion":
                lines.append(f"- {constraint_id}: {label} (EXCLUDED â€” do not suggest)")
            else:
                lines.append(f"- {constraint_id}: {label}")

        logger.info(
            f"ADR-042: Rendered {len(invariants)} bound constraints for LLM context"
        )

        return "\n".join(lines)

    def _render_qa_feedback(self, qa_feedback: Dict[str, Any]) -> Optional[str]:
        """Render QA feedback for remediation context.
        
        Makes previous QA failures prominent so the LLM can learn from them.
        
        Args:
            qa_feedback: Dict with issues, summary, source
            
        Returns:
            Formatted feedback string, or None if empty
        """
        issues = qa_feedback.get("issues", [])
        if not issues:
            return None
            
        lines = [
            "## Previous QA Feedback (MUST ADDRESS)",
            "The previous generation attempt failed QA. Fix these issues:",
            "",
        ]
        
        for i, issue in enumerate(issues, 1):
            issue_type = issue.get("type", "unknown")
            message = issue.get("message", "No details")
            remediation = issue.get("remediation")
            section = issue.get("section")
            check_id = issue.get("check_id")
            
            # Build issue line
            prefix = f"{i}. "
            if check_id:
                prefix += f"[{check_id}] "
            if section:
                prefix += f"({section}) "
                
            lines.append(f"{prefix}{message}")
            
            if remediation:
                lines.append(f"   → Fix: {remediation}")
        
        # Add summary if present
        summary = qa_feedback.get("summary")
        if summary and len(summary) > 10:
            lines.append("")
            lines.append(f"Summary: {summary[:500]}")
        
        logger.info(f"Rendered {len(issues)} QA feedback issues for remediation")
        
        return "\n".join(lines)

    def _format_pgc_questions(self, produced_document: Dict[str, Any]) -> str:
        """Return human-readable text for PGC questions (optional rendering).
        
        Args:
            produced_document: The clarification questions document
            
        Returns:
            Human-readable formatted questions (NOT JSON)
        """
        questions = produced_document.get("questions", [])
        if not questions:
            return "No clarification questions needed."
        
        lines = ["Please answer the following questions:\n"]
        for i, q in enumerate(questions, 1):
            if isinstance(q, dict):
                qid = q.get("id", f"Q{i}")
                text = q.get("text", "")
                priority = q.get("priority", "")
                answer_type = q.get("answer_type", "")
                choices = q.get("choices", [])
                
                priority_marker = {"must": "[REQUIRED]", "should": "[Recommended]", "could": "[Optional]"}.get(priority, "")
                lines.append(f"{i}. {priority_marker} {text}")
                
                if answer_type == "yes_no":
                    lines.append("   Answer: Yes / No")
                elif answer_type == "free_text":
                    lines.append("   Answer: (free text)")
                elif choices:
                    lines.append("   Options:")
                    for c in choices:
                        label = c.get("label", c.get("value", "")) if isinstance(c, dict) else c
                        lines.append(f"     - {label}")
            lines.append("")
        
        lines.append("Note: Use pending_user_input_payload for structured data.")
        return "\n".join(lines)

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
                logger.debug(f"Parsing JSON block: {json_str[:200]}...")
                return json.loads(json_str)
            elif response.strip().startswith("{"):
                logger.debug(f"Parsing raw JSON: {response[:200]}...")
                return json.loads(response)
            else:
                logger.warning(f"Response doesn't contain JSON. First 200 chars: {response[:200]}...")
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"JSON parse failed: {e}. Response snippet: {response[:300]}...")

        # Fallback: return as raw content
        logger.warning(f"Falling back to raw content for produces={produces}")
        return {
            "type": produces or "unknown",
            "content": response,
            "raw": True,
        }
