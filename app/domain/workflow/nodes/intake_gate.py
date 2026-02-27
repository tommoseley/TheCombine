"""Intake Gate Node - Mechanical Sufficiency Check.

Implements the Intake Sufficiency Rule:
- Intake is complete once: audience, artifact_type, project_category are known
- One question at a time for missing fields only
- Never re-ask about filled fields
- No LLM-based "readiness" checks

This replaces prompt-based conversational logic with a hard checklist.
"""

import logging
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional, List

from app.domain.workflow.nodes.base import NodeExecutor, NodeResult, DocumentWorkflowContext

logger = logging.getLogger(__name__)

# Minimum length for fast-path (substantial input)
MIN_SUBSTANTIAL_LENGTH = 100


@dataclass
class IntakeFrame:
    """Mechanical intake sufficiency frame.
    
    Intake is COMPLETE when all three fields are non-null.
    No other criteria. No "understanding". No "readiness".
    """
    audience: Optional[str] = None        # Who is this for?
    artifact_type: Optional[str] = None   # What is being built? (web app, mobile app, API, etc.)
    project_category: str = "greenfield"  # greenfield/enhancement/migration/integration
    
    # Accumulated raw input for context
    raw_inputs: List[str] = field(default_factory=list)
    
    def is_complete(self) -> bool:
        """Mechanical check: all required fields present."""
        return self.audience is not None and self.artifact_type is not None
    
    def missing_field(self) -> Optional[str]:
        """Return first missing field name, or None if complete."""
        if self.artifact_type is None:
            return "artifact_type"
        if self.audience is None:
            return "audience"
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Questions for each missing field - ONE question only, no lists
FIELD_QUESTIONS = {
    "artifact_type": "What type of software do you want to build? (e.g., web app, mobile app, API, desktop application)",
    "audience": "Who will use this? (e.g., internal team, customers, children, general public)",
}


class IntakeGateExecutor(NodeExecutor):
    """Intake gate with mechanical sufficiency check.
    
    Rules:
    1. Extract fields from user input
    2. If frame complete -> qualified -> review phase
    3. If frame incomplete -> ask ONE question about first missing field
    4. Never re-ask about filled fields
    5. No multi-question prompts
    """
    
    def __init__(
        self,
        llm_service=None,
        prompt_loader=None,
    ):
        self.llm_service = llm_service
        self.prompt_loader = prompt_loader
    
    def get_supported_node_type(self) -> str:
        """Return the node type this executor handles."""
        return "intake_gate"
    
    async def execute(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        context: DocumentWorkflowContext,
        state_snapshot: Dict[str, Any],
    ) -> NodeResult:
        """Execute intake gate with mechanical sufficiency check."""
        
        user_input = context.extra.get("user_input", "")
        
        # Load existing frame from last execution's metadata (persists across calls)
        frame_data = {}
        node_history = state_snapshot.get("node_history", [])
        for execution in reversed(node_history):
            if "intake_frame" in execution.get("metadata", {}):
                frame_data = execution["metadata"]["intake_frame"]
                break
        
        frame = IntakeFrame(
            audience=frame_data.get("audience"),
            artifact_type=frame_data.get("artifact_type"),
            project_category=frame_data.get("project_category", "greenfield"),
            raw_inputs=frame_data.get("raw_inputs", []),
        )
        
        # No input yet - ask for initial description
        if not user_input or not user_input.strip():
            logger.info(f"Intake gate {node_id}: No input, requesting initial description")
            return NodeResult.needs_user_input(
                prompt="Please describe what you'd like to build or accomplish.",
                node_id=node_id,
            )
        
        # Accumulate input
        frame.raw_inputs.append(user_input)
        all_input = " ".join(frame.raw_inputs)
        
        # Extract fields from accumulated input
        frame = self._extract_fields(frame, all_input)
        
        logger.info(f"Intake gate {node_id}: Frame state - audience={frame.audience}, artifact_type={frame.artifact_type}")
        
        # Check mechanical sufficiency
        if frame.is_complete():
            logger.info(f"Intake gate {node_id}: Frame COMPLETE - proceeding to review")
            return self._build_qualified_result(node_id, frame)
        
        # Frame incomplete - ask ONE question for first missing field
        missing = frame.missing_field()
        question = FIELD_QUESTIONS.get(missing, "Please provide more details.")
        
        logger.info(f"Intake gate {node_id}: Missing '{missing}', asking single question")
        
        return NodeResult.needs_user_input(
            prompt=question,
            node_id=node_id,
            intake_frame=frame.to_dict(),
            user_input=user_input,
        )
    
    def _extract_fields(self, frame: IntakeFrame, text: str) -> IntakeFrame:
        """Extract intake fields from text. Simple pattern matching."""
        text_lower = text.lower()
        
        # Extract artifact_type
        if frame.artifact_type is None:
            frame.artifact_type = self._extract_artifact_type(text_lower)
        
        # Extract audience
        if frame.audience is None:
            frame.audience = self._extract_audience(text_lower)
        
        # Extract project_category
        frame.project_category = self._extract_category(text_lower)
        
        return frame
    
    def _extract_artifact_type(self, text: str) -> Optional[str]:
        """Extract what is being built."""
        patterns = [
            (r"\bweb\s*app(?:lication)?\b", "web_application"),
            (r"\bwebsite\b", "website"),
            (r"\bmobile\s*app(?:lication)?\b", "mobile_application"),
            (r"\bios\s*app\b", "mobile_application"),
            (r"\bandroid\s*app\b", "mobile_application"),
            (r"\bdesktop\s*app(?:lication)?\b", "desktop_application"),
            (r"\bapi\b", "api"),
            (r"\bbackend\b", "backend_service"),
            (r"\bservice\b", "backend_service"),
            (r"\btool\b", "tool"),
            (r"\bplatform\b", "platform"),
            (r"\bsystem\b", "system"),
            (r"\bdashboard\b", "dashboard"),
            (r"\bportal\b", "portal"),
            (r"\bapp\b", "application"),  # Generic fallback
            (r"\bapplication\b", "application"),
            (r"\bsoftware\b", "software"),
        ]
        
        for pattern, artifact_type in patterns:
            if re.search(pattern, text):
                return artifact_type
        
        return None
    
    def _extract_audience(self, text: str) -> Optional[str]:
        """Extract who the artifact is for."""
        patterns = [
            # Age-based
            (r"\b(?:kids?|children)\b.*?(\d+[-–]\d+|\d+\s*(?:to|and)\s*\d+)", lambda m: f"children_{m.group(1).replace(' ', '').replace('to', '-').replace('and', '-')}"),
            (r"\b(\d+[-–]\d+)\s*year\s*olds?\b", lambda m: f"children_{m.group(1)}"),
            (r"\bkids?\b|\bchildren\b", lambda m: "children"),
            (r"\bteenagers?\b|\bteens?\b", lambda m: "teenagers"),
            (r"\badults?\b", lambda m: "adults"),
            (r"\bstudents?\b", lambda m: "students"),
            (r"\blearners?\b", lambda m: "learners"),
            # Role-based
            (r"\bteachers?\b", lambda m: "teachers"),
            (r"\bparents?\b", lambda m: "parents"),
            (r"\bdevelopers?\b", lambda m: "developers"),
            (r"\bemployees?\b", lambda m: "employees"),
            (r"\bcustomers?\b", lambda m: "customers"),
            (r"\busers?\b", lambda m: "users"),
            (r"\bteam\b", lambda m: "internal_team"),
            (r"\binternal\b", lambda m: "internal_team"),
            (r"\bpublic\b", lambda m: "general_public"),
        ]
        
        for pattern, extractor in patterns:
            match = re.search(pattern, text)
            if match:
                if callable(extractor):
                    return extractor(match)
                return extractor
        
        return None
    
    def _extract_category(self, text: str) -> str:
        """Extract project category."""
        if any(word in text for word in ["existing", "current", "upgrade", "improve", "enhance", "add to", "extend"]):
            return "enhancement"
        if any(word in text for word in ["migrate", "migration", "move", "convert", "port"]):
            return "migration"
        if any(word in text for word in ["integrate", "integration", "connect", "api"]):
            return "integration"
        return "greenfield"
    
    def _build_qualified_result(self, node_id: str, frame: IntakeFrame) -> NodeResult:
        """Build qualified result with interpretation for review phase."""
        
        # Build project name from inputs
        first_input = frame.raw_inputs[0] if frame.raw_inputs else ""
        project_name = self._extract_project_name(first_input)
        
        # Build problem statement from all inputs
        problem_statement = " ".join(frame.raw_inputs)
        if len(problem_statement) > 500:
            problem_statement = problem_statement[:500] + "..."
        
        interpretation = {
            "project_name": {"value": project_name, "source": "llm", "locked": False},
            "problem_statement": {"value": problem_statement, "source": "llm", "locked": False},
            "project_type": {"value": frame.project_category, "source": "llm", "locked": False},
        }
        
        return NodeResult(
            outcome="qualified",
            metadata={
                "node_id": node_id,
                "classification": "qualified",
                "intake_frame": frame.to_dict(),
                "intake_summary": problem_statement,
                "project_type": frame.project_category,
                "artifact_type": frame.artifact_type,
                "audience": frame.audience,
                "source": "mechanical_sufficiency",
                "user_input": " ".join(frame.raw_inputs),
                "intent_canon": " ".join(frame.raw_inputs),
                "interpretation": interpretation,
                "phase": "review",
            },
        )
    
    def _extract_project_name(self, text: str) -> str:
        """Extract a concise project name."""
        # Take first line or first sentence
        first_line = text.split('\n')[0].strip()
        if len(first_line) <= 50:
            return first_line
        
        # Try first sentence
        sentences = re.split(r'[.!?]', text)
        if sentences and len(sentences[0]) <= 50:
            return sentences[0].strip()
        
        # Truncate
        return text[:47] + "..."