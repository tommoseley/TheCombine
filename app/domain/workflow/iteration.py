"""Iteration handler - expand iterate_over blocks.

Transforms iteration steps into concrete instances for execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, TYPE_CHECKING
import uuid

from app.domain.workflow.models import Workflow, WorkflowStep

if TYPE_CHECKING:
    from app.domain.workflow.context import WorkflowContext


@dataclass
class IterationInstance:
    """A single iteration instance to process."""
    entity_type: str
    entity_id: str
    entity_data: Dict[str, Any]
    scope: str
    scope_id: str
    steps: List[WorkflowStep]


class IterationHandler:
    """Handle iterate_over blocks in workflow steps.

    Given a step with:
        iterate_over:
            doc_type: source_document
            collection_field: items
            entity_type: work_package

    Expands to one IterationInstance per item in source_document.items[]
    """
    
    def __init__(self, workflow: Workflow):
        self.workflow = workflow
    
    def expand(
        self,
        step: WorkflowStep,
        context: "WorkflowContext",
    ) -> List[IterationInstance]:
        """Expand iteration step into concrete instances.
        
        Args:
            step: Step with iterate_over configuration
            context: Current workflow context
            
        Returns:
            List of IterationInstance to process
        """
        if not step.is_iteration or step.iterate_over is None:
            return []
        
        iter_config = step.iterate_over
        
        # Get the collection to iterate over
        items = self.get_collection(
            iter_config.doc_type,
            iter_config.collection_field,
            context,
        )
        
        if not items:
            return []
        
        # Determine the scope this iteration creates
        entity_config = self.workflow.entity_types.get(iter_config.entity_type)
        iteration_scope = entity_config.creates_scope if entity_config else iter_config.entity_type
        
        # Create instances
        instances = []
        for i, item in enumerate(items):
            entity_id = self._get_or_generate_id(item, iter_config.entity_type, i)
            
            instances.append(IterationInstance(
                entity_type=iter_config.entity_type,
                entity_id=entity_id,
                entity_data=item,
                scope=iteration_scope,
                scope_id=entity_id,
                steps=step.steps or [],
            ))
        
        return instances
    
    def get_collection(
        self,
        doc_type: str,
        collection_field: str,
        context: "WorkflowContext",
    ) -> List[Dict[str, Any]]:
        """Get items from a document's collection field.
        
        Args:
            doc_type: Document containing the collection
            collection_field: Field name holding the array
            context: Current workflow context
            
        Returns:
            List of items to iterate over
        """
        # Get document type config to find its scope
        doc_config = self.workflow.document_types.get(doc_type)
        if doc_config is None:
            return []
        
        # Get the document
        doc = context.get_document(doc_type, doc_config.scope)
        if doc is None:
            return []
        
        # Extract collection field
        collection = doc.get(collection_field)
        if not isinstance(collection, list):
            return []
        
        return collection
    
    def _get_or_generate_id(
        self,
        item: Dict[str, Any],
        entity_type: str,
        index: int,
    ) -> str:
        """Get ID from item or generate one.
        
        Looks for 'id', 'entity_id', or '{entity_type}_id' fields.
        Falls back to generating a unique ID.
        """
        # Try common ID field names
        for field in ["id", "entity_id", f"{entity_type}_id"]:
            if field in item and item[field]:
                return str(item[field])
        
        # Generate ID
        return f"{entity_type}_{index}_{uuid.uuid4().hex[:8]}"
    
    def count_iterations(
        self,
        step: WorkflowStep,
        context: "WorkflowContext",
    ) -> int:
        """Count how many iterations a step will produce."""
        if not step.is_iteration or step.iterate_over is None:
            return 0
        
        iter_config = step.iterate_over
        items = self.get_collection(
            iter_config.doc_type,
            iter_config.collection_field,
            context,
        )
        return len(items)


# Import here to avoid circular dependency
from app.domain.workflow.context import WorkflowContext
