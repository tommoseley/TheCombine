# workforce/mentor_dispatcher.py

"""Mentor invocation interface."""

from typing import Optional

from workforce.schemas.artifacts import (
    Epic,
    ArchitecturalNotes,
    BASpecification,
    ProposedChangeSet,
    QAResult,
    QAFeedback
)
from workforce.utils.errors import MentorInvocationError
from workforce.utils.logging import log_info


class MentorDispatcher:
    """
    Dispatches work to Mentors and validates artifacts.
    
    Orchestrator communicates ONLY with Mentors through this interface.
    """
    
    def invoke_pm_mentor(self, intent: str) -> Epic:
        """
        Invoke PM Mentor to produce Epic.
        
        Args:
            intent: Human intent/request
            
        Returns:
            Epic artifact
            
        Raises:
            MentorInvocationError: If invocation fails
        """
        log_info("Invoking PM Mentor")
        # TODO: Implement actual PM Mentor invocation
        raise NotImplementedError("PM Mentor invocation not yet implemented")
    
    def invoke_architect_mentor(self, epic: Epic) -> ArchitecturalNotes:
        """
        Invoke Architect Mentor to produce Architectural Notes.
        
        Args:
            epic: Epic from PM Phase
            
        Returns:
            Architectural Notes artifact
            
        Raises:
            MentorInvocationError: If invocation fails
        """
        log_info("Invoking Architect Mentor")
        # TODO: Implement actual Architect Mentor invocation
        raise NotImplementedError("Architect Mentor invocation not yet implemented")
    
    def invoke_ba_mentor(self, epic: Epic, arch_notes: ArchitecturalNotes) -> BASpecification:
        """
        Invoke BA Mentor to produce BA Specification.
        
        Args:
            epic: Epic from PM Phase
            arch_notes: Architectural Notes from Architect Phase
            
        Returns:
            BA Specification artifact
            
        Raises:
            MentorInvocationError: If invocation fails
        """
        log_info("Invoking BA Mentor")
        # TODO: Implement actual BA Mentor invocation
        raise NotImplementedError("BA Mentor invocation not yet implemented")
    
    def invoke_dev_mentor(self, ba_spec: BASpecification, 
                         qa_feedback: Optional[QAFeedback] = None) -> ProposedChangeSet:
        """
        Invoke Dev Mentor to produce Proposed Change Set.
        
        Args:
            ba_spec: BA Specification to implement
            qa_feedback: Optional QA feedback from previous rejection
            
        Returns:
            Proposed Change Set artifact
            
        Raises:
            MentorInvocationError: If invocation fails
        """
        log_info("Invoking Dev Mentor")
        
        if qa_feedback:
            log_info(f"Including QA feedback from attempt {qa_feedback.attempt}")
            # TODO: Pass feedback to Dev Mentor
        
        # TODO: Implement actual Dev Mentor invocation
        raise NotImplementedError("Dev Mentor invocation not yet implemented")
    
    def invoke_qa_mentor(self, change_set: ProposedChangeSet, 
                        ba_spec: BASpecification) -> QAResult:
        """
        Invoke QA Mentor to approve or reject.
        
        Args:
            change_set: Proposed Change Set from Dev Phase
            ba_spec: BA Specification for validation
            
        Returns:
            QA Result with approval or rejection
            
        Raises:
            MentorInvocationError: If invocation fails
        """
        log_info("Invoking QA Mentor")
        # TODO: Implement actual QA Mentor invocation
        raise NotImplementedError("QA Mentor invocation not yet implemented")