"""
Document handler exceptions.

These exceptions are raised during document processing
and provide clear, actionable error information.
"""

from typing import List, Dict, Any, Optional


class DocumentHandlerError(Exception):
    """Base exception for all document handler errors."""
    
    def __init__(self, message: str, doc_type_id: Optional[str] = None):
        self.doc_type_id = doc_type_id
        self.message = message
        super().__init__(message)


class DocumentParseError(DocumentHandlerError):
    """
    Raised when raw LLM output cannot be parsed.
    
    This typically means:
    - No JSON found in response
    - Malformed JSON
    - Unexpected response format
    """
    
    def __init__(
        self, 
        doc_type_id: str, 
        raw_content: str,
        parse_error: Optional[str] = None
    ):
        self.raw_content = raw_content
        self.parse_error = parse_error
        
        message = f"Failed to parse {doc_type_id} response"
        if parse_error:
            message += f": {parse_error}"
        
        super().__init__(message, doc_type_id)


class DocumentValidationError(DocumentHandlerError):
    """
    Raised when parsed content fails schema validation.
    
    Contains detailed information about what failed validation
    to support debugging and retry logic.
    """
    
    def __init__(
        self, 
        doc_type_id: str, 
        errors: List[str],
        parsed_content: Optional[Dict[str, Any]] = None
    ):
        self.errors = errors
        self.parsed_content = parsed_content
        
        error_summary = "; ".join(errors[:3])  # First 3 errors
        if len(errors) > 3:
            error_summary += f" (+{len(errors) - 3} more)"
        
        message = f"Validation failed for {doc_type_id}: {error_summary}"
        
        super().__init__(message, doc_type_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "error": "validation_failed",
            "doc_type_id": self.doc_type_id,
            "errors": self.errors,
            "error_count": len(self.errors),
        }


class DocumentTransformError(DocumentHandlerError):
    """
    Raised when document transformation fails.
    
    Transformation includes normalization, enrichment,
    and business logic application.
    """
    
    def __init__(
        self, 
        doc_type_id: str, 
        transform_step: str,
        original_error: Optional[Exception] = None
    ):
        self.transform_step = transform_step
        self.original_error = original_error
        
        message = f"Transform failed for {doc_type_id} at step '{transform_step}'"
        if original_error:
            message += f": {str(original_error)}"
        
        super().__init__(message, doc_type_id)


class DocumentRenderError(DocumentHandlerError):
    """
    Raised when document rendering fails.
    
    Rendering converts structured data to HTML for display.
    """
    
    def __init__(
        self, 
        doc_type_id: str,
        render_type: str = "full",  # 'full' or 'summary'
        original_error: Optional[Exception] = None
    ):
        self.render_type = render_type
        self.original_error = original_error
        
        message = f"Render ({render_type}) failed for {doc_type_id}"
        if original_error:
            message += f": {str(original_error)}"
        
        super().__init__(message, doc_type_id)


class DependencyNotMetError(DocumentHandlerError):
    """
    Raised when required input documents are missing.
    
    This is a pre-build check failure, not a processing error.
    """
    
    def __init__(
        self, 
        doc_type_id: str, 
        missing_dependencies: List[str]
    ):
        self.missing_dependencies = missing_dependencies
        
        deps = ", ".join(missing_dependencies)
        message = f"Cannot build {doc_type_id}: missing required documents [{deps}]"
        
        super().__init__(message, doc_type_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "error": "dependencies_not_met",
            "doc_type_id": self.doc_type_id,
            "missing": self.missing_dependencies,
        }


class HandlerNotFoundError(DocumentHandlerError):
    """
    Raised when no handler is registered for a document type.
    
    This indicates a configuration error — the document type
    exists in the registry but no handler is available.
    """
    
    def __init__(self, handler_id: str):
        self.handler_id = handler_id
        message = f"No handler registered for '{handler_id}'"
        super().__init__(message, doc_type_id=None)