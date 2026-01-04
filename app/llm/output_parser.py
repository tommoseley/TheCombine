"""Output parsing and validation for LLM responses."""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.domain.services.llm_response_parser import (
    LLMResponseParser,
    ParseResult,
)


@dataclass
class ValidationError:
    """A single validation error."""
    field: str
    message: str
    value: Any = None


@dataclass 
class ValidationResult:
    """Result of output validation."""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, field: str, message: str, value: Any = None) -> None:
        """Add a validation error."""
        self.errors.append(ValidationError(field=field, message=message, value=value))
        self.valid = False
    
    def add_warning(self, message: str) -> None:
        """Add a warning (doesn't affect validity)."""
        self.warnings.append(message)


@dataclass
class ClarificationQuestion:
    """A question needing human clarification."""
    question: str
    context: Optional[str] = None
    options: Optional[List[str]] = None


@dataclass
class ClarificationResult:
    """Result of clarification detection."""
    needs_clarification: bool
    questions: List[ClarificationQuestion] = field(default_factory=list)
    raw_text: Optional[str] = None


class OutputValidator:
    """Validates parsed output against schemas and rules."""
    
    def validate(
        self,
        data: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None,
        required_fields: Optional[List[str]] = None,
    ) -> ValidationResult:
        """
        Validate parsed data against schema and rules.
        
        Args:
            data: Parsed JSON data
            schema: Optional JSON schema for validation
            required_fields: Optional list of required field names
            
        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult(valid=True)
        
        # Check required fields
        if required_fields:
            for field_name in required_fields:
                if field_name not in data:
                    result.add_error(field_name, f"Required field '{field_name}' is missing")
                elif data[field_name] is None:
                    result.add_error(field_name, f"Required field '{field_name}' is null")
                elif isinstance(data[field_name], str) and not data[field_name].strip():
                    result.add_error(field_name, f"Required field '{field_name}' is empty")
        
        # Basic schema validation if provided
        if schema:
            self._validate_schema(data, schema, result)
        
        return result
    
    def _validate_schema(
        self, 
        data: Dict[str, Any], 
        schema: Dict[str, Any],
        result: ValidationResult,
    ) -> None:
        """Validate data against JSON schema (basic validation)."""
        schema_type = schema.get("type")
        
        if schema_type == "object":
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            
            # Check required properties
            for prop in required:
                if prop not in data:
                    result.add_error(prop, f"Required property '{prop}' missing")
            
            # Validate property types
            for prop, prop_schema in properties.items():
                if prop in data:
                    self._validate_type(prop, data[prop], prop_schema, result)
    
    def _validate_type(
        self,
        field: str,
        value: Any,
        schema: Dict[str, Any],
        result: ValidationResult,
    ) -> None:
        """Validate a single field's type."""
        expected_type = schema.get("type")
        
        if expected_type is None:
            return
        
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        
        python_type = type_map.get(expected_type)
        if python_type and not isinstance(value, python_type):
            result.add_error(
                field,
                f"Expected {expected_type}, got {type(value).__name__}",
                value,
            )
        
        # Check string constraints
        if expected_type == "string" and isinstance(value, str):
            min_len = schema.get("minLength")
            max_len = schema.get("maxLength")
            if min_len and len(value) < min_len:
                result.add_error(field, f"String too short (min {min_len})", value)
            if max_len and len(value) > max_len:
                result.add_error(field, f"String too long (max {max_len})", value)
        
        # Check array constraints
        if expected_type == "array" and isinstance(value, list):
            min_items = schema.get("minItems")
            max_items = schema.get("maxItems")
            if min_items and len(value) < min_items:
                result.add_error(field, f"Array too short (min {min_items} items)", value)
            if max_items and len(value) > max_items:
                result.add_error(field, f"Array too long (max {max_items} items)", value)


class ClarificationDetector:
    """Detects when LLM response indicates need for clarification."""
    
    # Patterns that indicate clarification is needed
    CLARIFICATION_PATTERNS = [
        r"(?:I |we |it )?(?:need|require)s?\s+(?:more\s+)?(?:information|clarification|details)",
        r"(?:could|can|would)\s+you\s+(?:please\s+)?(?:clarify|specify|provide|explain)",
        r"(?:before\s+(?:I|we)\s+can\s+proceed|to\s+proceed)",
        r"(?:unclear|ambiguous|not\s+(?:clear|specified))",
        r"(?:which|what)\s+(?:of\s+the\s+following|option)",
        r"\?\s*$",  # Ends with question mark
    ]
    
    # Patterns for extracting questions
    QUESTION_PATTERNS = [
        r"(?:^|\n)\s*(?:\d+[\.\)]\s*)?([^.!]+\?)",  # Numbered or plain questions
        r"(?:^|\n)\s*[-•]\s*([^.!]+\?)",  # Bulleted questions
    ]
    
    def detect(self, response_text: str) -> ClarificationResult:
        """
        Detect if response indicates need for clarification.
        
        Args:
            response_text: Raw LLM response text
            
        Returns:
            ClarificationResult with detected questions
        """
        text_lower = response_text.lower()
        
        # Check for clarification patterns
        needs_clarification = any(
            re.search(pattern, text_lower, re.IGNORECASE)
            for pattern in self.CLARIFICATION_PATTERNS
        )
        
        if not needs_clarification:
            return ClarificationResult(
                needs_clarification=False,
                questions=[],
                raw_text=response_text,
            )
        
        # Extract questions
        questions = self._extract_questions(response_text)
        
        return ClarificationResult(
            needs_clarification=True,
            questions=questions,
            raw_text=response_text,
        )
    
    def _extract_questions(self, text: str) -> List[ClarificationQuestion]:
        """Extract individual questions from text."""
        questions = []
        seen = set()
        
        for pattern in self.QUESTION_PATTERNS:
            matches = re.findall(pattern, text, re.MULTILINE)
            for match in matches:
                question = match.strip()
                if question and question not in seen:
                    seen.add(question)
                    questions.append(ClarificationQuestion(question=question))
        
        return questions


class OutputParser:
    """Combined parser with validation and clarification detection."""
    
    def __init__(
        self,
        json_parser: Optional[LLMResponseParser] = None,
        validator: Optional[OutputValidator] = None,
        clarification_detector: Optional[ClarificationDetector] = None,
    ):
        """
        Initialize output parser.
        
        Args:
            json_parser: JSON extraction parser
            validator: Output validator
            clarification_detector: Clarification detector
        """
        self._json_parser = json_parser or LLMResponseParser()
        self._validator = validator or OutputValidator()
        self._clarification_detector = clarification_detector or ClarificationDetector()
    
    def parse(
        self,
        response_text: str,
        schema: Optional[Dict[str, Any]] = None,
        required_fields: Optional[List[str]] = None,
        check_clarification: bool = True,
    ) -> tuple[ParseResult, ValidationResult, Optional[ClarificationResult]]:
        """
        Parse, validate, and check for clarifications.
        
        Args:
            response_text: Raw LLM response
            schema: Optional JSON schema
            required_fields: Optional required fields
            check_clarification: Whether to check for clarification needs
            
        Returns:
            Tuple of (ParseResult, ValidationResult, ClarificationResult or None)
        """
        # Check for clarification first
        clarification = None
        if check_clarification:
            clarification = self._clarification_detector.detect(response_text)
            if clarification.needs_clarification:
                # Return early - don't try to parse if clarification needed
                return (
                    ParseResult(success=False, data=None, strategy_used=None, 
                               error_messages=["Clarification needed"]),
                    ValidationResult(valid=False),
                    clarification,
                )
        
        # Parse JSON
        parse_result = self._json_parser.parse(response_text)
        
        # Validate if parsing succeeded
        if parse_result.success and parse_result.data:
            validation = self._validator.validate(
                parse_result.data,
                schema=schema,
                required_fields=required_fields,
            )
        else:
            validation = ValidationResult(valid=False)
            validation.add_error("_parse", "Failed to parse JSON from response")
        
        return parse_result, validation, clarification
