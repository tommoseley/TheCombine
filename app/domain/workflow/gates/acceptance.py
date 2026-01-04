"""Acceptance gate - human approval flow for documents.

MVP scope per ADR-021:
- Boolean accept/reject
- Optional comment
- No versioning
- No multi-party approval
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.domain.workflow.models import Workflow
from app.domain.workflow.workflow_state import AcceptanceDecision


class AcceptanceGate:
    """Human approval flow for documents requiring acceptance.
    
    Documents can be configured to require acceptance before
    the workflow proceeds. This gate checks requirements and
    records decisions.
    """
    
    def __init__(self, workflow: Workflow):
        self.workflow = workflow
    
    def requires_acceptance(self, doc_type: str) -> bool:
        """Check if document type requires acceptance.
        
        Args:
            doc_type: Document type identifier
            
        Returns:
            True if acceptance is required
        """
        doc_config = self.workflow.document_types.get(doc_type)
        if doc_config is None:
            return False
        return doc_config.acceptance_required or False
    
    def get_acceptors(self, doc_type: str) -> List[str]:
        """Get list of roles that can accept this document.
        
        Args:
            doc_type: Document type identifier
            
        Returns:
            List of role identifiers that can accept
        """
        doc_config = self.workflow.document_types.get(doc_type)
        if doc_config is None:
            return []
        return doc_config.accepted_by or []
    
    def can_accept(self, doc_type: str, user_role: str) -> bool:
        """Check if a user with given role can accept this document.
        
        Args:
            doc_type: Document type identifier
            user_role: Role of the user attempting to accept
            
        Returns:
            True if user can accept
        """
        acceptors = self.get_acceptors(doc_type)
        if not acceptors:
            # If no acceptors specified, anyone can accept
            return True
        return user_role in acceptors
    
    def record_decision(
        self,
        doc_type: str,
        scope_id: Optional[str],
        accepted: bool,
        decided_by: str,
        comment: Optional[str] = None,
    ) -> AcceptanceDecision:
        """Create an acceptance decision record.
        
        Args:
            doc_type: Document type being accepted/rejected
            scope_id: Scope instance ID (for scoped documents)
            accepted: True if accepted, False if rejected
            decided_by: Identifier of who made the decision
            comment: Optional comment explaining decision
            
        Returns:
            AcceptanceDecision record
        """
        return AcceptanceDecision(
            doc_type=doc_type,
            scope_id=scope_id,
            accepted=accepted,
            comment=comment,
            decided_by=decided_by,
            decided_at=datetime.now(timezone.utc),
        )
    
    def make_decision_key(self, doc_type: str, scope_id: Optional[str]) -> str:
        """Create unique key for a decision.
        
        Args:
            doc_type: Document type
            scope_id: Scope instance ID
            
        Returns:
            Unique key string
        """
        return f"{doc_type}:{scope_id or 'root'}"
    
    def get_decision(
        self,
        doc_type: str,
        scope_id: Optional[str],
        decisions: Dict[str, AcceptanceDecision],
    ) -> Optional[AcceptanceDecision]:
        """Get decision for a specific document.
        
        Args:
            doc_type: Document type
            scope_id: Scope instance ID
            decisions: Dictionary of recorded decisions
            
        Returns:
            AcceptanceDecision if found
        """
        key = self.make_decision_key(doc_type, scope_id)
        return decisions.get(key)
    
    def can_proceed(
        self,
        doc_type: str,
        scope_id: Optional[str],
        decisions: Dict[str, AcceptanceDecision],
    ) -> bool:
        """Check if workflow can proceed past this acceptance point.
        
        Args:
            doc_type: Document type requiring acceptance
            scope_id: Scope instance ID
            decisions: Dictionary of recorded decisions
            
        Returns:
            True if accepted and can proceed
        """
        if not self.requires_acceptance(doc_type):
            return True
        
        decision = self.get_decision(doc_type, scope_id, decisions)
        if decision is None:
            return False
        
        return decision.accepted
    
    def is_rejected(
        self,
        doc_type: str,
        scope_id: Optional[str],
        decisions: Dict[str, AcceptanceDecision],
    ) -> bool:
        """Check if document was rejected.
        
        Args:
            doc_type: Document type
            scope_id: Scope instance ID
            decisions: Dictionary of recorded decisions
            
        Returns:
            True if explicitly rejected
        """
        decision = self.get_decision(doc_type, scope_id, decisions)
        if decision is None:
            return False
        return not decision.accepted
    
    def is_pending(
        self,
        doc_type: str,
        scope_id: Optional[str],
        decisions: Dict[str, AcceptanceDecision],
    ) -> bool:
        """Check if document is pending acceptance.
        
        Args:
            doc_type: Document type
            scope_id: Scope instance ID
            decisions: Dictionary of recorded decisions
            
        Returns:
            True if requires acceptance but no decision recorded
        """
        if not self.requires_acceptance(doc_type):
            return False
        
        decision = self.get_decision(doc_type, scope_id, decisions)
        return decision is None
