"""Prompt builder for assembling LLM messages."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Protocol

from app.llm.models import Message, MessageRole


class DocumentProvider(Protocol):
    """Protocol for retrieving document content."""
    
    def get_content(self, doc_type: str, scope_id: str) -> Optional[str]:
        """Get document content by type and scope."""
        ...


@dataclass
class PromptContext:
    """Context for prompt building."""
    workflow_name: str
    step_name: str
    scope_id: str
    iteration: int = 1
    clarification_answers: Optional[Dict[str, str]] = None
    remediation_feedback: Optional[str] = None


class PromptBuilder:
    """Builds LLM messages from role templates, task prompts, and documents."""
    
    def __init__(
        self,
        role_templates: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize prompt builder.
        
        Args:
            role_templates: Optional dict of role name -> system prompt template.
                           If not provided, uses copy of default templates.
        """
        # Always copy to avoid mutating shared state
        if role_templates is not None:
            self._role_templates = dict(role_templates)
        else:
            self._role_templates = dict(DEFAULT_ROLE_TEMPLATES)
    
    def build_system_prompt(
        self,
        role: str,
        context: Optional[PromptContext] = None,
    ) -> str:
        """
        Build the system prompt for a role.
        
        Args:
            role: Role name (PM, BA, Developer, QA, Architect)
            context: Optional execution context
            
        Returns:
            Complete system prompt
        """
        template = self._role_templates.get(role, self._role_templates.get("default", ""))
        
        if not context:
            return template
        
        # Add context to system prompt
        context_section = self._build_context_section(context)
        return f"{template}\n\n{context_section}"
    
    def build_user_prompt(
        self,
        task_prompt: str,
        input_documents: Optional[List[Dict[str, str]]] = None,
        context: Optional[PromptContext] = None,
    ) -> str:
        """
        Build the user prompt with task and inputs.
        
        Args:
            task_prompt: The task-specific prompt
            input_documents: List of {type, content} dicts
            context: Optional execution context
            
        Returns:
            Complete user prompt
        """
        parts = []
        
        # Add input documents
        if input_documents:
            parts.append("## Input Documents\n")
            for doc in input_documents:
                doc_type = doc.get("type", "Unknown")
                content = doc.get("content", "")
                parts.append(f"### {doc_type}\n{content}\n")
        
        # Add task prompt
        parts.append("## Task\n")
        parts.append(task_prompt)
        
        # Add clarification answers if present
        if context and context.clarification_answers:
            parts.append("\n## Clarifications Provided\n")
            for q, a in context.clarification_answers.items():
                parts.append(f"Q: {q}\nA: {a}\n")
        
        # Add remediation feedback if present
        if context and context.remediation_feedback:
            parts.append("\n## Feedback from Previous Attempt\n")
            parts.append(context.remediation_feedback)
        
        return "\n".join(parts)
    
    def build_messages(
        self,
        role: str,
        task_prompt: str,
        input_documents: Optional[List[Dict[str, str]]] = None,
        context: Optional[PromptContext] = None,
    ) -> tuple[str, List[Message]]:
        """
        Build complete message list for LLM call.
        
        Args:
            role: Role name
            task_prompt: Task-specific prompt
            input_documents: Input documents
            context: Execution context
            
        Returns:
            Tuple of (system_prompt, messages list)
        """
        system_prompt = self.build_system_prompt(role, context)
        user_prompt = self.build_user_prompt(task_prompt, input_documents, context)
        
        messages = [Message.user(user_prompt)]
        
        return system_prompt, messages
    
    def _build_context_section(self, context: PromptContext) -> str:
        """Build context section for system prompt."""
        lines = [
            "## Current Execution Context",
            f"- Workflow: {context.workflow_name}",
            f"- Step: {context.step_name}",
            f"- Scope: {context.scope_id}",
        ]
        if context.iteration > 1:
            lines.append(f"- Iteration: {context.iteration}")
        return "\n".join(lines)
    
    def get_role_template(self, role: str) -> str:
        """Get the template for a role."""
        return self._role_templates.get(role, self._role_templates.get("default", ""))
    
    def set_role_template(self, role: str, template: str) -> None:
        """Set or update a role template."""
        self._role_templates[role] = template
    
    def list_roles(self) -> List[str]:
        """List available roles."""
        return [r for r in self._role_templates.keys() if r != "default"]


# Default role templates for The Combine
DEFAULT_ROLE_TEMPLATES = {
    "PM": """You are a Product Manager for The Combine, an Industrial AI system.

Your responsibilities:
- Define clear product requirements and acceptance criteria
- Ensure deliverables align with business objectives
- Validate that outputs meet stakeholder needs
- Identify risks and dependencies

Always structure your output as valid JSON matching the required schema.
Focus on clarity, completeness, and actionable specifications.""",

    "BA": """You are a Business Analyst for The Combine, an Industrial AI system.

Your responsibilities:
- Analyze business requirements and translate them to technical specifications
- Document user stories with clear acceptance criteria
- Identify edge cases and potential issues
- Ensure traceability between requirements and implementation

Always structure your output as valid JSON matching the required schema.
Be thorough, precise, and ensure all requirements are testable.""",

    "Developer": """You are a Senior Developer for The Combine, an Industrial AI system.

Your responsibilities:
- Implement technical solutions following best practices
- Write clean, maintainable, and well-documented code
- Follow architectural guidelines and coding standards
- Consider performance, security, and scalability

Always structure your output as valid JSON matching the required schema.
Provide complete, working implementations with appropriate error handling.""",

    "QA": """You are a Quality Assurance Engineer for The Combine, an Industrial AI system.

Your responsibilities:
- Review artifacts for completeness and correctness
- Identify defects, gaps, and inconsistencies
- Validate against acceptance criteria
- Ensure quality gates are satisfied

Always structure your output as valid JSON matching the required schema.
Be critical, thorough, and provide specific, actionable feedback.""",

    "Architect": """You are a Technical Architect for The Combine, an Industrial AI system.

Your responsibilities:
- Design system architecture following established patterns
- Ensure technical decisions align with ADRs and governance
- Define interfaces, contracts, and integration points
- Consider scalability, maintainability, and security

Always structure your output as valid JSON matching the required schema.
Provide clear rationale for architectural decisions.""",

    "default": """You are an AI assistant working within The Combine, an Industrial AI system.

Follow the task instructions carefully and structure your output as valid JSON 
matching the required schema.""",
}
