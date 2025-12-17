"""
Base Document Handler - Abstract base class for all document handlers.

Handlers are the document-type-specific processing logic.
They know how to:
- Parse raw LLM output into structured data
- Validate against schema
- Transform/enrich the data
- Render to HTML (full view and summary)

The handler does NOT:
- Call LLMs (that's the Builder's job)
- Manage persistence (that's the Repository's job)
- Handle HTTP concerns (that's the Route's job)

Handlers receive data and return data. Pure domain logic.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import json
import re
import logging

from app.domain.handlers.exceptions import (
    DocumentParseError,
    DocumentValidationError,
    DocumentTransformError,
    DocumentRenderError,
)

logger = logging.getLogger(__name__)


class BaseDocumentHandler(ABC):
    """
    Abstract base class for document handlers.
    
    Each document type has one handler that knows how to
    process that specific type of document.
    
    Subclasses must implement:
    - doc_type_id: The document type this handler processes
    - render(): Produce HTML for full document view
    - render_summary(): Produce HTML for card/list view
    
    Subclasses may override:
    - parse(): Custom parsing logic (default extracts JSON)
    - validate(): Custom validation (default uses schema)
    - transform(): Custom enrichment/normalization
    - extract_title(): How to get the document title
    """
    
    # =========================================================================
    # ABSTRACT PROPERTIES - Subclasses MUST define
    # =========================================================================
    
    @property
    @abstractmethod
    def doc_type_id(self) -> str:
        """
        The document type this handler processes.
        
        Must match the doc_type_id in the document_types table.
        Example: 'project_discovery', 'architecture_spec'
        """
        ...
    
    # =========================================================================
    # PARSING - Extract structured data from raw LLM output
    # =========================================================================
    
    def parse(self, raw_content: str) -> Dict[str, Any]:
        """
        Parse raw LLM response into structured data.
        
        Default implementation:
        1. Strips markdown code fences
        2. Finds JSON object/array
        3. Parses and returns
        
        Override for custom parsing needs.
        
        Args:
            raw_content: Raw text from LLM
            
        Returns:
            Parsed dictionary
            
        Raises:
            DocumentParseError: If parsing fails
        """
        try:
            # Strip markdown code fences
            content = raw_content.strip()
            content = re.sub(r'^```(?:json)?\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
            content = content.strip()
            
            # Try to find JSON object or array
            # Look for outermost { } or [ ]
            json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', content)
            
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # If no JSON found, try parsing the whole thing
            return json.loads(content)
            
        except json.JSONDecodeError as e:
            raise DocumentParseError(
                doc_type_id=self.doc_type_id,
                raw_content=raw_content[:500],  # Truncate for logging
                parse_error=str(e)
            )
    
    # =========================================================================
    # VALIDATION - Verify parsed content against schema
    # =========================================================================
    
    def validate(
        self, 
        data: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate parsed data against schema.
        
        Default implementation checks:
        1. Required fields from schema exist
        2. Basic type checking
        
        Override for custom validation rules.
        
        Args:
            data: Parsed document data
            schema: JSON schema (optional, from registry)
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if not schema:
            # No schema = valid by default
            return True, []
        
        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: '{field}'")
            elif data[field] is None:
                errors.append(f"Required field '{field}' is null")
        
        # Check properties if defined
        properties = schema.get("properties", {})
        for field, field_schema in properties.items():
            if field in data and data[field] is not None:
                field_type = field_schema.get("type")
                value = data[field]
                
                # Basic type validation
                if field_type == "string" and not isinstance(value, str):
                    errors.append(f"Field '{field}' must be a string")
                elif field_type == "array" and not isinstance(value, list):
                    errors.append(f"Field '{field}' must be an array")
                elif field_type == "object" and not isinstance(value, dict):
                    errors.append(f"Field '{field}' must be an object")
                elif field_type == "integer" and not isinstance(value, int):
                    errors.append(f"Field '{field}' must be an integer")
                elif field_type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"Field '{field}' must be a number")
                elif field_type == "boolean" and not isinstance(value, bool):
                    errors.append(f"Field '{field}' must be a boolean")
        
        return len(errors) == 0, errors
    
    def validate_or_raise(
        self, 
        data: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Validate and raise exception if invalid.
        
        Convenience method for when you want exception-based flow.
        
        Args:
            data: Parsed document data
            schema: JSON schema
            
        Raises:
            DocumentValidationError: If validation fails
        """
        is_valid, errors = self.validate(data, schema)
        if not is_valid:
            raise DocumentValidationError(
                doc_type_id=self.doc_type_id,
                errors=errors,
                parsed_content=data
            )
    
    # =========================================================================
    # TRANSFORMATION - Normalize and enrich data
    # =========================================================================
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform validated data.
        
        Default implementation returns data unchanged.
        
        Override to:
        - Normalize formats (dates, strings)
        - Compute derived fields
        - Add default values
        - Cross-reference other data
        
        Args:
            data: Validated document data
            
        Returns:
            Transformed data
        """
        return data
    
    # =========================================================================
    # RENDERING - Convert to HTML for display
    # =========================================================================
    
    @abstractmethod
    def render(
        self, 
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render document to HTML for full view.
        
        This produces the complete document visualization
        shown when a user views the document detail.
        
        Args:
            data: Document content
            context: Optional context (project info, etc.)
            
        Returns:
            HTML string
        """
        ...
    
    @abstractmethod
    def render_summary(
        self, 
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render document to HTML for summary view.
        
        This produces a compact representation for:
        - Cards in a list
        - Tree navigation items
        - Dashboard widgets
        
        Args:
            data: Document content
            context: Optional context
            
        Returns:
            HTML string
        """
        ...
    
    # =========================================================================
    # TITLE EXTRACTION
    # =========================================================================
    
    def extract_title(
        self, 
        data: Dict[str, Any],
        fallback: str = "Untitled"
    ) -> str:
        """
        Extract document title from parsed data.
        
        Default looks for common title fields.
        Override for document-specific logic.
        
        Args:
            data: Parsed document data
            fallback: Default if no title found
            
        Returns:
            Document title
        """
        # Try common title field names
        for field in ["title", "name", "project_name", "epic_title", "story_title"]:
            if field in data and data[field]:
                return str(data[field])
        
        # Try nested summary objects
        for summary_field in ["architecture_summary", "preliminary_summary", "summary"]:
            if summary_field in data and isinstance(data[summary_field], dict):
                summary = data[summary_field]
                if "title" in summary:
                    return str(summary["title"])
        
        return fallback
    
    # =========================================================================
    # FULL PROCESSING PIPELINE
    # =========================================================================
    
    def process(
        self,
        raw_content: str,
        schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Full processing pipeline: parse → validate → transform.
        
        This is the main entry point for processing LLM output.
        
        Args:
            raw_content: Raw LLM response
            schema: JSON schema for validation (optional)
            
        Returns:
            Dictionary with:
            - data: Processed document data
            - title: Extracted title
            - is_valid: Validation status
            
        Raises:
            DocumentParseError: If parsing fails
            DocumentValidationError: If validation fails
        """
        # Parse
        data = self.parse(raw_content)
        
        # Validate
        self.validate_or_raise(data, schema)
        
        # Transform
        data = self.transform(data)
        
        # Extract title
        title = self.extract_title(data)
        
        return {
            "data": data,
            "title": title,
            "doc_type_id": self.doc_type_id,
        }
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def safe_render(
        self,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        render_type: str = "full"
    ) -> str:
        """
        Render with error handling.
        
        Returns error HTML instead of raising on failure.
        Useful for UI rendering where you want graceful degradation.
        
        Args:
            data: Document data
            context: Optional context
            render_type: 'full' or 'summary'
            
        Returns:
            HTML string (or error HTML on failure)
        """
        try:
            if render_type == "summary":
                return self.render_summary(data, context)
            else:
                return self.render(data, context)
        except Exception as e:
            logger.error(f"Render failed for {self.doc_type_id}: {e}")
            return f"""
            <div class="p-4 bg-red-50 border border-red-200 rounded-lg">
                <p class="text-red-700 font-medium">Render Error</p>
                <p class="text-red-600 text-sm">{str(e)}</p>
            </div>
            """
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(doc_type_id='{self.doc_type_id}')>"