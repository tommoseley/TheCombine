"""QA gate - mechanical schema validation only.

Per MVP-Roadmap.md, QA is MECHANICAL ONLY:
- Schema validation
- Structural rules
- Required field presence
- NO domain intelligence
- NO probabilistic judgments

Intelligence creep is prohibited.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonschema

from app.domain.workflow.step_state import QAFinding, QAResult


class QAGate:
    """Mechanical QA - schema validation only.
    
    This gate enforces structural correctness of step outputs.
    It does NOT make domain judgments or probabilistic assessments.
    
    Usage:
        gate = QAGate()
        result = gate.check(output_document, doc_type="project_discovery")
        
        if not result.passed:
            for finding in result.findings:
                print(f"{finding.severity}: {finding.message}")
    """
    
    # Mapping of document types to their schemas
    # For MVP, most doc types don't have strict schemas yet
    DOC_TYPE_SCHEMAS: Dict[str, str] = {
        "clarification_questions": "clarification_question_set.v2.json",
        "intake_gate_result": "intake_gate_result.v1.json",
    }
    
    def __init__(self, schemas_dir: Optional[Path] = None):
        """Initialize gate.
        
        Args:
            schemas_dir: Directory containing JSON schemas.
                        Defaults to seed/schemas
        """
        self._schemas_dir = schemas_dir or Path("seed/schemas")
        self._schema_cache: Dict[str, Dict] = {}
    
    def check(
        self, 
        output: Any, 
        doc_type: str,
        strict: bool = True
    ) -> QAResult:
        """Check output against document type rules.
        
        Args:
            output: The document to validate (dict or JSON string)
            doc_type: Document type from workflow definition
            strict: If True, missing schema fails. If False, passes.
            
        Returns:
            QAResult with pass/fail and findings
        """
        findings: List[QAFinding] = []
        
        # Parse if string
        if isinstance(output, str):
            try:
                output = json.loads(output)
            except json.JSONDecodeError as e:
                findings.append(QAFinding(
                    path="$",
                    message=f"Invalid JSON: {e}",
                    severity="error",
                    rule="json_parse",
                ))
                return QAResult(passed=False, findings=findings)
        
        # Basic structural checks
        structural_findings = self._check_structure(output)
        findings.extend(structural_findings)
        
        # Schema validation if available
        schema = self._get_schema_for_doc_type(doc_type)
        schema_name = self.DOC_TYPE_SCHEMAS.get(doc_type)
        
        if schema:
            schema_findings = self._validate_against_schema(output, schema)
            findings.extend(schema_findings)
        elif strict and doc_type in self.DOC_TYPE_SCHEMAS:
            # Schema expected but not found
            findings.append(QAFinding(
                path="$",
                message=f"Schema file not found for {doc_type}",
                severity="warning",
                rule="schema_missing",
            ))
        
        # Determine pass/fail
        has_errors = any(f.severity == "error" for f in findings)
        
        return QAResult(
            passed=not has_errors,
            findings=findings,
            schema_used=schema_name,
        )
    
    def _check_structure(self, output: Any) -> List[QAFinding]:
        """Basic structural validation.
        
        Mechanical checks only:
        - Must be dict or list
        - Not empty
        """
        findings = []
        
        if output is None:
            findings.append(QAFinding(
                path="$",
                message="Output is null",
                severity="error",
                rule="not_null",
            ))
        elif not isinstance(output, (dict, list)):
            findings.append(QAFinding(
                path="$",
                message=f"Output must be object or array, got {type(output).__name__}",
                severity="error",
                rule="valid_type",
            ))
        elif isinstance(output, dict) and len(output) == 0:
            findings.append(QAFinding(
                path="$",
                message="Output object is empty",
                severity="warning",
                rule="not_empty",
            ))
        elif isinstance(output, list) and len(output) == 0:
            findings.append(QAFinding(
                path="$",
                message="Output array is empty",
                severity="warning",
                rule="not_empty",
            ))
        
        return findings
    
    def _get_schema_for_doc_type(self, doc_type: str) -> Optional[Dict]:
        """Get JSON schema for document type, if any."""
        # Check cache
        if doc_type in self._schema_cache:
            return self._schema_cache[doc_type]
        
        # Look up schema file
        schema_file = self.DOC_TYPE_SCHEMAS.get(doc_type)
        if not schema_file:
            return None
        
        schema_path = self._schemas_dir / schema_file
        if not schema_path.exists():
            return None
        
        try:
            with open(schema_path, "r", encoding="utf-8-sig") as f:
                schema = json.load(f)
            self._schema_cache[doc_type] = schema
            return schema
        except (json.JSONDecodeError, IOError):
            return None
    
    def _validate_against_schema(
        self, 
        output: Dict, 
        schema: Dict
    ) -> List[QAFinding]:
        """Validate output against JSON schema."""
        findings = []
        
        try:
            jsonschema.validate(output, schema)
        except jsonschema.ValidationError as e:
            # Convert path to string
            path = "/".join(str(p) for p in e.absolute_path) or "$"
            
            findings.append(QAFinding(
                path=path,
                message=e.message,
                severity="error",
                rule="schema_validation",
            ))
            
            # Collect all errors, not just first
            validator = jsonschema.Draft202012Validator(schema)
            for error in validator.iter_errors(output):
                if error.message != e.message:  # Avoid duplicate
                    path = "/".join(str(p) for p in error.absolute_path) or "$"
                    findings.append(QAFinding(
                        path=path,
                        message=error.message,
                        severity="error",
                        rule="schema_validation",
                    ))
        except jsonschema.SchemaError as e:
            findings.append(QAFinding(
                path="$",
                message=f"Invalid schema: {e.message}",
                severity="error",
                rule="schema_error",
            ))
        
        return findings
    
    def register_schema(self, doc_type: str, schema_file: str) -> None:
        """Register a schema for a document type.
        
        Useful for adding schemas dynamically.
        """
        self.DOC_TYPE_SCHEMAS[doc_type] = schema_file
        # Clear cache for this type
        self._schema_cache.pop(doc_type, None)
    
    def has_schema(self, doc_type: str) -> bool:
        """Check if a schema exists for document type."""
        return doc_type in self.DOC_TYPE_SCHEMAS
    
    def list_schemas(self) -> List[str]:
        """List all registered document types with schemas."""
        return list(self.DOC_TYPE_SCHEMAS.keys())