# workforce/canon/prompt_builder.py

"""System prompt builder with canon injection."""

from workforce.canon.loader import CanonDocument


class PromptBuilder:
    """Build system prompts with canon content."""
    
    def build_orchestrator_prompt(self, canon_doc: CanonDocument) -> str:
        """
        Build Orchestrator system prompt with injected canon.
        
        Args:
            canon_doc: Loaded canon document
            
        Returns:
            Complete system prompt with canon content
        """
        prompt = f"""ORCHESTRATOR SYSTEM PROMPT

PIPELINE_FLOW_VERSION={canon_doc.version}

{canon_doc.content}

[Orchestrator role-specific instructions active]
[State management instructions active]
[Mentor communication boundaries enforced]
"""
        return prompt
    
    def build_mentor_prompt(self, canon_doc: CanonDocument, mentor_role: str) -> str:
        """
        Build Mentor system prompt with canon content.
        
        Args:
            canon_doc: Loaded canon document
            mentor_role: Mentor role name (e.g., "PM Mentor")
            
        Returns:
            Complete system prompt for mentor
        """
        prompt = f"""{mentor_role.upper()} SYSTEM PROMPT

PIPELINE_FLOW_VERSION={canon_doc.version}

{canon_doc.content}

[{mentor_role} role-specific instructions active]
[Worker coordination instructions active]
"""
        return prompt