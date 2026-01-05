"""Remediation loop - bounded retry when QA fails.

Per ADR-012: max 3 attempts, then escalate.
"""

from dataclasses import dataclass
from typing import List, Optional

from app.domain.workflow.step_state import QAFinding, QAResult, StepState


@dataclass
class RemediationContext:
    """Context for building remediation prompt."""
    
    original_prompt: str
    findings: List[QAFinding]
    attempt: int
    max_attempts: int
    previous_output: Optional[str] = None


class RemediationLoop:
    """Bounded retry when QA fails.
    
    When QA gate fails, we can retry with feedback about what went wrong.
    This is bounded to prevent infinite loops.
    
    Usage:
        loop = RemediationLoop(max_attempts=3)
        
        if loop.should_retry(state, qa_result):
            prompt = loop.build_remediation_prompt(context)
            # Re-execute LLM with enhanced prompt
    """
    
    DEFAULT_MAX_ATTEMPTS = 3
    
    def __init__(self, max_attempts: int = DEFAULT_MAX_ATTEMPTS):
        """Initialize remediation loop.
        
        Args:
            max_attempts: Maximum total attempts (including initial).
                         Default is 3.
        """
        self.max_attempts = max_attempts
    
    def should_retry(self, state: StepState, qa_result: QAResult) -> bool:
        """Check if retry is allowed and worthwhile.
        
        Args:
            state: Current step state
            qa_result: Result from QA gate
            
        Returns:
            True if should retry, False if should fail
        """
        # Already passed - no retry needed
        if qa_result.passed:
            return False
        
        # Check attempt count
        if state.attempt >= self.max_attempts:
            return False
        
        # Check if there are actionable errors
        # (warnings alone don't warrant retry)
        if qa_result.error_count == 0:
            return False
        
        return True
    
    def build_remediation_prompt(self, context: RemediationContext) -> str:
        """Build prompt that includes QA findings for retry.
        
        The remediation prompt:
        1. Includes the original task prompt
        2. Adds the previous output (if any)
        3. Lists specific QA failures to address
        4. Requests correction
        
        Args:
            context: Remediation context with prompt and findings
            
        Returns:
            Enhanced prompt for retry attempt
        """
        sections = []
        
        # Original prompt
        sections.append("## Original Task")
        sections.append(context.original_prompt)
        sections.append("")
        
        # Previous attempt info
        sections.append("## Previous Attempt")
        sections.append(f"This is attempt {context.attempt + 1} of {context.max_attempts}.")
        sections.append("")
        
        if context.previous_output:
            sections.append("Your previous output was:")
            sections.append("```")
            # Truncate if very long
            output = context.previous_output
            if len(output) > 2000:
                output = output[:2000] + "\n... [truncated]"
            sections.append(output)
            sections.append("```")
            sections.append("")
        
        # QA findings
        sections.append("## Quality Issues to Address")
        sections.append("The previous output failed quality checks. Please address these issues:")
        sections.append("")
        
        for i, finding in enumerate(context.findings, 1):
            severity_marker = "🔴" if finding.severity == "error" else "🟡"
            sections.append(f"{i}. {severity_marker} **{finding.severity.upper()}** at `{finding.path}`:")
            sections.append(f"   {finding.message}")
            if finding.rule:
                sections.append(f"   (Rule: {finding.rule})")
            sections.append("")
        
        # Instructions
        sections.append("## Instructions")
        sections.append("Please regenerate your output, ensuring all quality issues above are resolved.")
        sections.append("Focus especially on ERROR items - these must be fixed for the output to pass.")
        
        return "\n".join(sections)
    
    def build_context(
        self,
        original_prompt: str,
        state: StepState,
        qa_result: QAResult,
    ) -> RemediationContext:
        """Build remediation context from current state.
        
        Args:
            original_prompt: The original task prompt
            state: Current step state
            qa_result: Latest QA result
            
        Returns:
            RemediationContext for building prompt
        """
        return RemediationContext(
            original_prompt=original_prompt,
            findings=qa_result.findings,
            attempt=state.attempt,
            max_attempts=self.max_attempts,
            previous_output=state.raw_llm_response,
        )
    
    def get_error_summary(self, findings: List[QAFinding]) -> str:
        """Get a brief summary of errors for logging.
        
        Args:
            findings: List of QA findings
            
        Returns:
            Brief summary string
        """
        errors = [f for f in findings if f.severity == "error"]
        warnings = [f for f in findings if f.severity == "warning"]
        
        parts = []
        if errors:
            parts.append(f"{len(errors)} error(s)")
        if warnings:
            parts.append(f"{len(warnings)} warning(s)")
        
        return ", ".join(parts) if parts else "no issues"