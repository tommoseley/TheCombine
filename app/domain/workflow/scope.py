"""Scope hierarchy helper for workflow validation.

Implements ADR-011 scope relationships without hardcoding specific scopes.
All scope relationships are derived from workflow["scopes"].
"""

from typing import Dict, List, Optional


class ScopeHierarchyError(Exception):
    """Raised when scope hierarchy is invalid."""
    pass


class ScopeHierarchy:
    """
    Scope relationship helper built from workflow's declared scopes.
    
    Does NOT hardcode project/epic/story. Derives all relationships
    from the workflow's scopes declaration.
    """
    
    def __init__(self, scope_definitions: Dict[str, Dict]):
        """
        Initialize from scope definitions.
        
        Args:
            scope_definitions: workflow["scopes"] dict, e.g.:
                {
                    "project": {"parent": None},
                    "epic": {"parent": "project"},
                    "story": {"parent": "epic"}
                }
        
        Raises:
            ScopeHierarchyError: If scope graph contains cycles
        """
        self.scopes = scope_definitions
        self._validate_no_cycles()
    
    @classmethod
    def from_workflow(cls, workflow: dict) -> "ScopeHierarchy":
        """Build hierarchy from workflow definition."""
        return cls(workflow.get("scopes", {}))
    
    def is_valid_scope(self, scope: str) -> bool:
        """Check if scope is declared in the hierarchy."""
        return scope in self.scopes
    
    def get_parent(self, scope: str) -> Optional[str]:
        """
        Get immediate parent scope.
        
        Returns:
            Parent scope name, or None for root scopes.
            Returns None if scope is not declared.
        """
        if scope not in self.scopes:
            return None
        return self.scopes[scope].get("parent")
    
    def is_ancestor(self, maybe_ancestor: str, of_scope: str) -> bool:
        """
        Check if maybe_ancestor is an ancestor of of_scope.
        
        An ancestor is any scope in the parent chain, not including
        the scope itself.
        
        Args:
            maybe_ancestor: Scope to check as potential ancestor
            of_scope: Scope to check ancestry of
            
        Returns:
            True if maybe_ancestor is in the parent chain of of_scope
        """
        current = self.get_parent(of_scope)
        while current is not None:
            if current == maybe_ancestor:
                return True
            current = self.get_parent(current)
        return False
    
    def is_descendant(self, maybe_descendant: str, of_scope: str) -> bool:
        """
        Check if maybe_descendant is a descendant of of_scope.
        
        A descendant is any scope that has of_scope in its ancestor chain.
        """
        return self.is_ancestor(of_scope, maybe_descendant)
    
    def get_root_scopes(self) -> List[str]:
        """
        Get all scopes with no parent (root scopes).
        
        Returns:
            List of scope names that have parent=None
        """
        return [
            scope for scope, config in self.scopes.items()
            if config.get("parent") is None
        ]
    
    def get_all_scopes(self) -> List[str]:
        """Get all declared scope names."""
        return list(self.scopes.keys())
    
    def get_depth(self, scope: str) -> int:
        """
        Get the depth of a scope in the hierarchy.
        
        Root scopes have depth 0.
        
        Returns:
            Depth as integer, or -1 if scope is not declared
        """
        if scope not in self.scopes:
            return -1
        
        depth = 0
        current = self.get_parent(scope)
        while current is not None:
            depth += 1
            current = self.get_parent(current)
        return depth
    
    def _validate_no_cycles(self) -> None:
        """
        Validate that the scope graph has no cycles.
        
        Raises:
            ScopeHierarchyError: If a cycle is detected
        """
        for scope in self.scopes:
            visited = set()
            current = scope
            
            while current is not None:
                if current in visited:
                    raise ScopeHierarchyError(
                        f"Cycle detected in scope hierarchy involving '{current}'"
                    )
                visited.add(current)
                
                # Get parent, but check it exists in our scopes
                parent = self.scopes.get(current, {}).get("parent")
                if parent is not None and parent not in self.scopes:
                    raise ScopeHierarchyError(
                        f"Scope '{current}' references unknown parent '{parent}'"
                    )
                current = parent
