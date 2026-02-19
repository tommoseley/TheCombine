"""
Handler Registry - Maps handler IDs to handler instances.

This is the code-side registry that complements the database
document_types table. The database says "use handler X",
this module provides handler X.

Adding a new handler:
1. Create the handler class in app/domain/handlers/
2. Import it here
3. Add it to HANDLERS dict

The handler_id in the database must match a key in HANDLERS.
"""

from typing import Dict, Optional
import logging

from app.domain.handlers.base_handler import BaseDocumentHandler
from app.domain.handlers.exceptions import HandlerNotFoundError

# Import concrete handlers as they are created
from app.domain.handlers.project_discovery_handler import ProjectDiscoveryHandler
from app.domain.handlers.architecture_spec_handler import ArchitectureSpecHandler
from app.domain.handlers.story_backlog_handler import StoryBacklogHandler
from app.domain.handlers.implementation_plan_primary_handler import ImplementationPlanPrimaryHandler
from app.domain.handlers.implementation_plan_handler import ImplementationPlanHandler
from app.domain.handlers.intent_packet_handler import IntentPacketHandler
from app.domain.handlers.backlog_item_handler import BacklogItemHandler
from app.domain.handlers.execution_plan_handler import ExecutionPlanHandler
from app.domain.handlers.plan_explanation_handler import PlanExplanationHandler
from app.domain.handlers.pipeline_run_handler import PipelineRunHandler
from app.domain.handlers.work_package_handler import WorkPackageHandler
from app.domain.handlers.work_statement_handler import WorkStatementHandler
from app.domain.handlers.project_logbook_handler import ProjectLogbookHandler

logger = logging.getLogger(__name__)


# =============================================================================
# HANDLER REGISTRY
# =============================================================================

# Handler instances keyed by handler_id
# The handler_id must match the handler_id column in document_types table
HANDLERS: Dict[str, BaseDocumentHandler] = {
    # Registered handlers:
    "project_discovery": ProjectDiscoveryHandler(),
    "technical_architecture": ArchitectureSpecHandler(),
    "story_backlog": StoryBacklogHandler(),
    "implementation_plan_primary": ImplementationPlanPrimaryHandler(),
    "implementation_plan": ImplementationPlanHandler(),
    # WS-BCP-001: Backlog Compilation Pipeline
    "intent_packet": IntentPacketHandler(),
    "backlog_item": BacklogItemHandler(),
    # WS-BCP-002: ExecutionPlan (mechanically derived)
    "execution_plan": ExecutionPlanHandler(),
    # WS-BCP-003: Plan Explanation (LLM explains, never computes)
    "plan_explanation": PlanExplanationHandler(),
    # WS-BCP-004: Pipeline Run metadata
    "pipeline_run": PipelineRunHandler(),
    # WS-ONTOLOGY-001: Work Package
    "work_package": WorkPackageHandler(),
    # WS-ONTOLOGY-002: Work Statement
    "work_statement": WorkStatementHandler(),
    # WS-ONTOLOGY-003: Project Logbook
    "project_logbook": ProjectLogbookHandler(),
}


def get_handler(handler_id: str) -> BaseDocumentHandler:
    """
    Get a handler by its ID.
    
    Args:
        handler_id: The handler ID from document_types.handler_id
        
    Returns:
        The handler instance
        
    Raises:
        HandlerNotFoundError: If no handler registered for this ID
    """
    handler = HANDLERS.get(handler_id)
    
    if handler is None:
        logger.error(f"No handler registered for '{handler_id}'")
        raise HandlerNotFoundError(handler_id)
    
    return handler


def list_handlers() -> Dict[str, str]:
    """
    List all registered handlers.
    
    Returns:
        Dictionary mapping handler_id to handler class name
    """
    return {
        handler_id: handler.__class__.__name__
        for handler_id, handler in HANDLERS.items()
    }


def handler_exists(handler_id: str) -> bool:
    """
    Check if a handler is registered.
    
    Args:
        handler_id: The handler ID to check
        
    Returns:
        True if handler exists, False otherwise
    """
    return handler_id in HANDLERS


def register_handler(handler_id: str, handler: BaseDocumentHandler) -> None:
    """
    Register a handler dynamically.
    
    This is useful for testing or plugin systems.
    
    Args:
        handler_id: The ID to register under
        handler: The handler instance
    """
    if handler_id in HANDLERS:
        logger.warning(f"Overwriting existing handler for '{handler_id}'")
    
    HANDLERS[handler_id] = handler
    logger.info(f"Registered handler '{handler_id}': {handler.__class__.__name__}")


def unregister_handler(handler_id: str) -> Optional[BaseDocumentHandler]:
    """
    Unregister a handler.
    
    Args:
        handler_id: The ID to unregister
        
    Returns:
        The removed handler, or None if not found
    """
    return HANDLERS.pop(handler_id, None)