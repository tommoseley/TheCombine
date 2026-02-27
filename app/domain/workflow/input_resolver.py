"""Input resolver - resolve step inputs per ADR-011 reference rules.

Resolves document and entity references for workflow steps,
enforcing scope-based access rules.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

from app.domain.workflow.models import InputReference, Workflow, WorkflowStep
from app.domain.workflow.scope import ScopeHierarchy


class DocumentStore(Protocol):
    """Protocol for document storage.
    
    Implementations provide access to documents by type and scope.
    """
    
    def get_document(
        self, 
        doc_type: str, 
        scope: str, 
        scope_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get a document by type and scope.
        
        Args:
            doc_type: Document type identifier
            scope: Scope level (e.g., "project")
            scope_id: Optional scope instance ID (for non-root scopes)
            
        Returns:
            Document dict if found, None otherwise
        """
        ...
    
    def get_entity(
        self,
        entity_type: str,
        scope: str,
        scope_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get an entity by type and scope.
        
        Args:
            entity_type: Entity type identifier
            scope: Scope level
            scope_id: Scope instance ID
            
        Returns:
            Entity dict if found, None otherwise
        """
        ...


@dataclass
class ResolvedInput:
    """A resolved input reference."""
    
    ref: InputReference
    value: Any
    found: bool
    error: Optional[str] = None


@dataclass
class InputResolutionResult:
    """Result of resolving all inputs for a step."""
    
    inputs: Dict[str, ResolvedInput] = field(default_factory=dict)
    success: bool = True
    errors: List[str] = field(default_factory=list)
    
    def get_value(self, key: str) -> Optional[Any]:
        """Get resolved value by input key."""
        resolved = self.inputs.get(key)
        return resolved.value if resolved and resolved.found else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert resolved inputs to simple dict for prompt injection."""
        return {
            key: resolved.value
            for key, resolved in self.inputs.items()
            if resolved.found
        }


class InputResolver:
    """Resolve step inputs per ADR-011 reference rules.
    
    Reference rules:
    - Ancestor references: PERMITTED
    - Same-scope with context=true: PERMITTED (iteration context)
    - Same-scope at root (no parent): PERMITTED (only one instance)
    - Same-scope without context at non-root: FORBIDDEN
    - Descendant references: FORBIDDEN
    - Cross-branch references: FORBIDDEN
    
    Usage:
        resolver = InputResolver(workflow, document_store)
        result = resolver.resolve(step, current_scope_id="wp_123")
        
        if result.success:
            inputs = result.to_dict()
    """
    
    def __init__(
        self, 
        workflow: Workflow,
        store: DocumentStore,
    ):
        """Initialize resolver.
        
        Args:
            workflow: The workflow definition
            store: Document/entity storage
        """
        self.workflow = workflow
        self.store = store
        self.scope_hierarchy = ScopeHierarchy.from_workflow({
            "scopes": {
                scope_id: {"parent": config.parent}
                for scope_id, config in workflow.scopes.items()
            }
        })
    
    def resolve(
        self,
        step: WorkflowStep,
        scope_id: Optional[str] = None,
        parent_scope_ids: Optional[Dict[str, str]] = None,
    ) -> InputResolutionResult:
        """Resolve all inputs for a step.
        
        Args:
            step: The workflow step
            scope_id: Current scope instance ID (for non-root scopes)
            parent_scope_ids: Map of scope level -> scope ID for ancestor scopes
            
        Returns:
            InputResolutionResult with resolved values
        """
        result = InputResolutionResult()
        parent_scope_ids = parent_scope_ids or {}
        
        for i, ref in enumerate(step.inputs):
            key = self._make_input_key(ref, i)
            resolved = self._resolve_single(ref, step.scope, scope_id, parent_scope_ids)
            result.inputs[key] = resolved
            
            if not resolved.found:
                if ref.required:
                    result.success = False
                    result.errors.append(
                        f"Required input '{key}' not found: {resolved.error or 'unknown'}"
                    )
                else:
                    # Optional input not found is OK
                    pass
        
        return result
    
    def _make_input_key(self, ref: InputReference, index: int) -> str:
        """Generate a key for the input reference."""
        if ref.doc_type:
            return ref.doc_type
        elif ref.entity_type:
            return ref.entity_type
        else:
            return f"input_{index}"
    
    def _resolve_single(
        self,
        ref: InputReference,
        step_scope: str,
        scope_id: Optional[str],
        parent_scope_ids: Dict[str, str],
    ) -> ResolvedInput:
        """Resolve a single input reference."""
        # Validate reference rules first
        rule_error = self._check_reference_rules(ref, step_scope)
        if rule_error:
            return ResolvedInput(
                ref=ref,
                value=None,
                found=False,
                error=rule_error,
            )
        
        # Determine the scope ID to use for lookup
        lookup_scope_id = self._get_lookup_scope_id(
            ref.scope, step_scope, scope_id, parent_scope_ids
        )
        
        # Fetch the document or entity
        if ref.doc_type:
            value = self.store.get_document(
                ref.doc_type, 
                ref.scope, 
                lookup_scope_id
            )
            if value is None:
                return ResolvedInput(
                    ref=ref,
                    value=None,
                    found=False,
                    error=f"Document '{ref.doc_type}' not found at scope '{ref.scope}'"
                )
        elif ref.entity_type:
            value = self.store.get_entity(
                ref.entity_type,
                ref.scope,
                lookup_scope_id
            )
            if value is None:
                return ResolvedInput(
                    ref=ref,
                    value=None,
                    found=False,
                    error=f"Entity '{ref.entity_type}' not found at scope '{ref.scope}'"
                )
        else:
            return ResolvedInput(
                ref=ref,
                value=None,
                found=False,
                error="Reference has neither doc_type nor entity_type",
            )
        
        return ResolvedInput(
            ref=ref,
            value=value,
            found=True,
        )
    
    def _check_reference_rules(
        self, 
        ref: InputReference, 
        step_scope: str
    ) -> Optional[str]:
        """Check ADR-011 reference rules.
        
        Returns error message if rule violated, None if OK.
        """
        ref_scope = ref.scope
        
        # Rule 1: Ancestor reference - always OK
        if self.scope_hierarchy.is_ancestor(ref_scope, step_scope):
            return None
        
        # Rule 2: Same scope
        if ref_scope == step_scope:
            # Context reference is OK (iteration item)
            if ref.context:
                return None
            # Root scope (no parent) is OK - only one instance
            if self.scope_hierarchy.get_parent(ref_scope) is None:
                return None
            # Non-root same-scope without context is forbidden
            return f"Same-scope reference to '{ref.doc_type or ref.entity_type}' at non-root scope '{ref_scope}' forbidden without context=true"
        
        # Rule 3: Descendant reference - forbidden
        if self.scope_hierarchy.is_descendant(ref_scope, step_scope):
            return f"Descendant reference to scope '{ref_scope}' from '{step_scope}' forbidden"
        
        # Rule 4: Cross-branch - forbidden (neither ancestor, same, nor descendant)
        return f"Cross-branch reference to scope '{ref_scope}' from '{step_scope}' forbidden"
    
    def _get_lookup_scope_id(
        self,
        ref_scope: str,
        step_scope: str,
        current_scope_id: Optional[str],
        parent_scope_ids: Dict[str, str],
    ) -> Optional[str]:
        """Determine which scope ID to use for lookup.
        
        For same-scope: use current scope ID
        For ancestor scope: use parent scope ID from chain
        For root scope: no scope ID needed
        """
        # Root scope (no parent) - no ID needed
        if self.scope_hierarchy.get_parent(ref_scope) is None:
            return None
        
        # Same scope - use current
        if ref_scope == step_scope:
            return current_scope_id
        
        # Ancestor scope - look up in parent chain
        return parent_scope_ids.get(ref_scope)