"""Clarification gate - enforce ADR-024 clarification protocol.

Validates that when an LLM needs clarification, it returns ONLY questions,
no work product or declarative statements.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonschema


@dataclass
class ClarificationQuestion:
    """A validated clarification question."""
    
    id: str
    text: str
    why_it_matters: str
    priority: str  # "must", "should", "could"
    answer_type: str
    required: bool
    blocking: bool = True
    choices: Optional[List[Dict[str, str]]] = None
    default: Any = None


@dataclass
class ClarificationResult:
    """Result of clarification gate check."""
    
    needs_clarification: bool
    questions: List[ClarificationQuestion]
    raw_question_set: Optional[Dict[str, Any]] = None
    validation_errors: List[str] = None
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []


class ClarificationGate:
    """Enforce ADR-024 clarification protocol.
    
    Responsibilities:
    1. Detect if LLM response contains clarification questions
    2. Validate questions conform to schema
    3. Enforce questions-only mode (no declarative content)
    
    Usage:
        gate = ClarificationGate()
        result = gate.check(llm_response)
        
        if result.needs_clarification:
            # Pause execution and get answers
            for q in result.questions:
                print(f"{q.id}: {q.text}")
    """
    
    # Markers that indicate clarification questions in response
    CLARIFICATION_MARKERS = [
        '"schema_version": "clarification_question_set.v1"',
        '"mode": "questions_only"',
        '"question_set_kind":',
    ]
    
    def __init__(self, schema_path: Optional[Path] = None):
        """Initialize gate.
        
        Args:
            schema_path: Path to clarification_question_set.v2.json schema.
                        Defaults to seed/schemas/clarification_question_set.v2.json
        """
        self._schema_path = schema_path or Path("seed/schemas/clarification_question_set.v2.json")
        self._schema: Optional[Dict] = None
    
    @property
    def schema(self) -> Dict:
        """Lazy-load the schema."""
        if self._schema is None:
            self._schema = self._load_schema()
        return self._schema
    
    def _load_schema(self) -> Dict:
        """Load the clarification question set schema."""
        if not self._schema_path.exists():
            raise FileNotFoundError(
                f"Clarification schema not found: {self._schema_path}"
            )
        
        with open(self._schema_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    
    def check(self, llm_response: str) -> ClarificationResult:
        """Check if LLM response contains clarification questions.
        
        Args:
            llm_response: Raw text response from LLM
            
        Returns:
            ClarificationResult with questions if found, otherwise empty
        """
        # First, check if response looks like it contains clarification
        if not self._looks_like_clarification(llm_response):
            return ClarificationResult(needs_clarification=False, questions=[])
        
        # Try to extract JSON from response
        question_set = self._extract_json(llm_response)
        if question_set is None:
            return ClarificationResult(
                needs_clarification=False,
                questions=[],
                validation_errors=["Could not extract JSON from response"]
            )
        
        # Validate against schema
        validation_errors = self._validate_schema(question_set)
        if validation_errors:
            return ClarificationResult(
                needs_clarification=True,  # It tried to clarify but failed
                questions=[],
                raw_question_set=question_set,
                validation_errors=validation_errors
            )
        
        # Parse questions
        questions = self._parse_questions(question_set)
        
        return ClarificationResult(
            needs_clarification=True,
            questions=questions,
            raw_question_set=question_set
        )
    
    def _looks_like_clarification(self, response: str) -> bool:
        """Quick check if response might contain clarification questions."""
        return any(marker in response for marker in self.CLARIFICATION_MARKERS)
    
    def _extract_json(self, response: str) -> Optional[Dict]:
        """Extract JSON object from response text.
        
        Handles responses that might have markdown code blocks or
        surrounding text.
        """
        # Try direct parse first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON in code blocks
        patterns = [
            r'```json\s*([\s\S]*?)\s*```',
            r'```\s*([\s\S]*?)\s*```',
            r'\{[\s\S]*\}',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response)
            for match in matches:
                try:
                    # If it's from a code block, use the captured group
                    text = match if isinstance(match, str) else match[0]
                    obj = json.loads(text)
                    if isinstance(obj, dict):
                        return obj
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def _validate_schema(self, question_set: Dict) -> List[str]:
        """Validate question set against schema.
        
        Returns list of validation error messages (empty if valid).
        """
        errors = []
        
        try:
            jsonschema.validate(question_set, self.schema)
        except jsonschema.ValidationError as e:
            errors.append(f"Schema validation failed: {e.message}")
            if e.path:
                errors[-1] += f" at {'/'.join(str(p) for p in e.path)}"
        except jsonschema.SchemaError as e:
            errors.append(f"Invalid schema: {e.message}")
        
        return errors
    
    def _parse_questions(self, question_set: Dict) -> List[ClarificationQuestion]:
        """Parse validated question set into ClarificationQuestion objects."""
        questions = []
        
        for q in question_set.get("questions", []):
            questions.append(ClarificationQuestion(
                id=q["id"],
                text=q["text"],
                why_it_matters=q["why_it_matters"],
                priority=q["priority"],
                answer_type=q["answer_type"],
                required=q["required"],
                blocking=q.get("blocking", True),
                choices=q.get("choices"),
                default=q.get("default"),
            ))
        
        return questions
    
    def validate_questions_only(self, question_set: Dict) -> List[str]:
        """Validate that response is ONLY questions, no work product.
        
        This is the hard gate per ADR-024 - prevents declarative output drift.
        
        Returns list of violations (empty if compliant).
        """
        violations = []
        
        # Check mode
        if question_set.get("mode") != "questions_only":
            violations.append(
                f"Mode must be 'questions_only', got '{question_set.get('mode')}'"
            )
        
        # Check QA section (self-reported by LLM)
        qa = question_set.get("qa", {})
        
        if qa.get("non_question_line_count", -1) != 0:
            violations.append(
                f"non_question_line_count must be 0, got {qa.get('non_question_line_count')}"
            )
        
        if qa.get("declarative_sentence_count", -1) != 0:
            violations.append(
                f"declarative_sentence_count must be 0, got {qa.get('declarative_sentence_count')}"
            )
        
        if qa.get("answer_leadin_count", -1) != 0:
            violations.append(
                f"answer_leadin_count must be 0, got {qa.get('answer_leadin_count')}"
            )
        
        if qa.get("all_questions_end_with_qmark") is not True:
            violations.append("all_questions_end_with_qmark must be true")
        
        # Double-check question texts end with ?
        for i, q in enumerate(question_set.get("questions", [])):
            text = q.get("text", "")
            if not text.endswith("?"):
                violations.append(
                    f"Question {i} text must end with '?': {text[:50]}..."
                )
        
        return violations
    
    def get_blocking_questions(
        self, 
        questions: List[ClarificationQuestion]
    ) -> List[ClarificationQuestion]:
        """Get questions that must be answered before proceeding."""
        return [q for q in questions if q.blocking and q.required]
    
    def get_must_answer_ids(self, question_set: Dict) -> List[str]:
        """Get question IDs that must be answered before proceeding."""
        return question_set.get("must_answer_before_proceeding_ids") or []