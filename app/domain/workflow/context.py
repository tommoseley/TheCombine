"""Workflow context - scope-aware document and entity storage.

Implements the DocumentStore protocol from Phase 1, providing
storage that respects scope hierarchy during workflow execution.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.domain.workflow.models import Workflow


@dataclass
class ScopeInstance:
    """A specific instance of a scope level."""
    scope: str
    scope_id: str
    entity: Dict[str, Any]


class WorkflowContext:
    """Scope-aware document and entity storage.
    
    Implements the DocumentStore protocol required by InputResolver.
    """
    
    def __init__(self, workflow: Workflow, project_id: str):
        self.workflow = workflow
        self.project_id = project_id
        self._documents: Dict[str, Dict[str, Any]] = {}
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._scope_stack: List[ScopeInstance] = []
    
    # DocumentStore Protocol
    def get_document(
        self,
        doc_type: str,
        scope: str,
        scope_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if scope_id is None:
            scope_id = self._get_scope_id_for_level(scope)
        scope_key = self._make_scope_key(scope, scope_id)
        return self._documents.get(doc_type, {}).get(scope_key)
    
    def get_entity(
        self,
        entity_type: str,
        scope: str,
        scope_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if scope_id is None:
            scope_id = self._get_scope_id_for_level(scope)
        if scope_id is None:
            return None
        return self._entities.get(entity_type, {}).get(scope_id)
    
    # Storage Operations
    def store_document(
        self,
        doc_type: str,
        content: Dict[str, Any],
        scope_id: Optional[str] = None,
    ) -> None:
        doc_config = self.workflow.document_types.get(doc_type)
        if doc_config is None:
            raise ValueError(f"Unknown document type: {doc_type}")
        scope = doc_config.scope
        if scope_id is None:
            scope_id = self._get_scope_id_for_level(scope)
        scope_key = self._make_scope_key(scope, scope_id)
        if doc_type not in self._documents:
            self._documents[doc_type] = {}
        self._documents[doc_type][scope_key] = content
    
    def store_entity(
        self,
        entity_type: str,
        entity_id: str,
        content: Dict[str, Any],
    ) -> None:
        if entity_type not in self._entities:
            self._entities[entity_type] = {}
        self._entities[entity_type][entity_id] = content
    
    def has_document(self, doc_type: str, scope: str, scope_id: Optional[str] = None) -> bool:
        return self.get_document(doc_type, scope, scope_id) is not None
    
    def list_entities(self, entity_type: str) -> List[str]:
        return list(self._entities.get(entity_type, {}).keys())
    
    # Scope Management
    def push_scope(self, scope: str, scope_id: str, entity: Dict[str, Any]) -> None:
        instance = ScopeInstance(scope=scope, scope_id=scope_id, entity=entity)
        self._scope_stack.append(instance)
        entity_type = self._get_entity_type_for_scope(scope)
        if entity_type:
            self.store_entity(entity_type, scope_id, entity)
    
    def pop_scope(self) -> ScopeInstance:
        if not self._scope_stack:
            raise IndexError("Cannot pop from empty scope stack")
        return self._scope_stack.pop()
    
    def current_scope(self) -> Optional[ScopeInstance]:
        return self._scope_stack[-1] if self._scope_stack else None
    
    def get_scope_chain(self) -> Dict[str, str]:
        chain = {}
        for instance in self._scope_stack:
            chain[instance.scope] = instance.scope_id
        return chain
    
    def scope_depth(self) -> int:
        return len(self._scope_stack)
    
    # Internal helpers
    def _make_scope_key(self, scope: str, scope_id: Optional[str]) -> str:
        return f"{scope}:{scope_id or 'root'}"
    
    def _get_scope_id_for_level(self, scope: str) -> Optional[str]:
        scope_config = self.workflow.scopes.get(scope)
        if scope_config and scope_config.parent is None:
            return None
        for instance in reversed(self._scope_stack):
            if instance.scope == scope:
                return instance.scope_id
        return None
    
    def _get_entity_type_for_scope(self, scope: str) -> Optional[str]:
        for et_id, et_config in self.workflow.entity_types.items():
            if et_config.creates_scope == scope:
                return et_id
        return None
    
    # Serialization
    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "documents": self._documents,
            "entities": self._entities,
            "scope_stack": [
                {"scope": s.scope, "scope_id": s.scope_id, "entity": s.entity}
                for s in self._scope_stack
            ],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], workflow: Workflow) -> "WorkflowContext":
        ctx = cls(workflow, data["project_id"])
        ctx._documents = data.get("documents", {})
        ctx._entities = data.get("entities", {})
        ctx._scope_stack = [
            ScopeInstance(scope=s["scope"], scope_id=s["scope_id"], entity=s["entity"])
            for s in data.get("scope_stack", [])
        ]
        return ctx
