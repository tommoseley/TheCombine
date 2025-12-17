"""
Document Handlers - Document-type-specific processing logic.

Handlers know how to:
- Parse raw LLM output into structured data
- Validate against schemas
- Transform/enrich data
- Render to HTML

Usage:
    from app.domain.handlers import get_handler, BaseDocumentHandler
    
    # Get a handler by ID
    handler = get_handler("project_discovery")
    
    # Process raw LLM output
    result = handler.process(raw_content, schema)
    
    # Render to HTML
    html = handler.render(result["data"], context)

Adding a new handler:
    1. Create handler class inheriting from BaseDocumentHandler
    2. Implement required methods (render, render_summary)
    3. Register in handlers/registry.py
"""

from app.domain.handlers.base_handler import BaseDocumentHandler
from app.domain.handlers.registry import (
    get_handler,
    list_handlers,
    handler_exists,
    register_handler,
    unregister_handler,
)
from app.domain.handlers.exceptions import (
    DocumentHandlerError,
    DocumentParseError,
    DocumentValidationError,
    DocumentTransformError,
    DocumentRenderError,
    DependencyNotMetError,
    HandlerNotFoundError,
)

__all__ = [
    # Base class
    "BaseDocumentHandler",
    
    # Registry functions
    "get_handler",
    "list_handlers",
    "handler_exists",
    "register_handler",
    "unregister_handler",
    
    # Exceptions
    "DocumentHandlerError",
    "DocumentParseError",
    "DocumentValidationError",
    "DocumentTransformError",
    "DocumentRenderError",
    "DependencyNotMetError",
    "HandlerNotFoundError",
]