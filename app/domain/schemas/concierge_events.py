"""
Concierge event schemas and enums.

Implements CONCIERGE_PROJECT_INGESTION_CONTRACT v1.0 sections 7 and 8
Pydantic models for type safety and validation.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


# =============================================================================
# ENUMS (Contract Section 7 and 8.1)
# =============================================================================

class IntentClass(str, Enum):
    """
    Stable intent classification enum.
    Contract section 7.1
    """
    EXPLORE_PROBLEM = "explore_problem"
    PLAN_WORK = "plan_work"
    CHANGE_EXISTING = "change_existing"
    INTEGRATE_SYSTEMS = "integrate_systems"
    PRODUCE_OUTPUT = "produce_output"
    UNKNOWN = "unknown"


class SessionState(str, Enum):
    """
    Session state machine states.
    Contract section 6.1
    """
    IDLE = "idle"
    ORIENTING = "orienting"
    CAPTURING_INTENT = "capturing_intent"
    CONFIRMING_INTENT = "confirming_intent"
    CLARIFYING = "clarifying"
    CONSENT_GATE = "consent_gate"
    HANDOFF_EMITTED = "handoff_emitted"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    SESSION_EXPIRED = "session_expired"


class EventType(str, Enum):
    """
    Event type enum for intake events.
    Contract section 8.1
    """
    SESSION_CREATED = "session_created"
    ORIENTATION_VIEWED = "orientation_viewed"
    USER_INTENT_SUBMITTED = "user_intent_submitted"
    INTENT_REFLECTION_PROPOSED = "intent_reflection_proposed"
    INTENT_CONFIRMED = "intent_confirmed"
    INTENT_REVISED = "intent_revised"
    CLARIFICATION_QUESTIONS_ISSUED = "clarification_questions_issued"
    CLARIFICATION_ANSWER_SUBMITTED = "clarification_answer_submitted"
    CLARIFICATION_COMPLETED = "clarification_completed"
    CONSENT_PRESENTED = "consent_presented"
    CONSENT_ACCEPTED = "consent_accepted"
    CONSENT_DECLINED = "consent_declined"
    HANDOFF_EMITTED = "handoff_emitted"
    SESSION_ABANDONED = "session_abandoned"
    SESSION_EXPIRED = "session_expired"


class AnswerType(str, Enum):
    """Answer type for clarification questions."""
    FREE_TEXT = "free_text"
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"
    BOOLEAN = "boolean"


class Confidence(str, Enum):
    """Confidence level enum."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# =============================================================================
# EVENT PAYLOAD SCHEMAS (Contract Section 8.2)
# =============================================================================

class AttachmentSchema(BaseModel):
    """Attachment reference in user intent."""
    name: str
    id: str


class UserIntentSubmitted(BaseModel):
    """
    Contract section 8.2.1
    User submits initial intent statement.
    """
    raw_text: str = Field(..., min_length=1)
    attachments: Optional[List[AttachmentSchema]] = None


class IntentReflectionProposed(BaseModel):
    """
    Contract section 8.2.2
    LLM-assisted intent reflection and classification.
    """
    reflection_text: str
    intent_class: IntentClass
    confidence: Confidence
    candidate_discovery_profile: Optional[str] = None
    known_unknowns: List[str] = []


class ClarificationQuestion(BaseModel):
    """Single clarification question."""
    id: str
    prompt: str
    reason: str
    answer_type: AnswerType
    required: bool
    options: Optional[List[str]] = None


class ClarificationQuestionsIssued(BaseModel):
    """
    Contract section 8.2.3
    System issues clarification questions (max 4).
    """
    questions: List[ClarificationQuestion] = Field(..., max_length=4)
    
    @field_validator('questions')
    def validate_max_questions(cls, v):
        if len(v) > 4:
            raise ValueError('Maximum 4 clarification questions allowed')
        return v


class ClarificationAnswerSubmitted(BaseModel):
    """
    Contract section 8.2.4
    User submits answer to clarification question.
    """
    question_id: str
    answer: Any  # Type depends on answer_type
    confidence: Optional[Confidence] = None


class WillCreate(BaseModel):
    """What will be created on consent."""
    project: bool = True


class WillGenerate(BaseModel):
    """What will be generated on consent."""
    artifact_type: str = "project_discovery"
    discovery_profile: str


class ConsentPresented(BaseModel):
    """
    Contract section 8.2.5
    System presents consent gate to user.
    """
    will_create: WillCreate
    will_generate: WillGenerate
    user_visible_summary: str


class ClarificationDetail(BaseModel):
    """Clarification answer detail."""
    answer: Any
    confidence: Optional[Confidence] = None


class GovernanceFlags(BaseModel):
    """Governance flags for handoff."""
    requires_security_review: bool = False
    contains_external_users: bool = False
    contains_sensitive_data: bool = False


class HandoffEmitted(BaseModel):
    """
    Contract section 8.2.6
    Final handoff contract emitted after consent.
    """
    handoff_version: str = "1.0"
    intent_summary: str
    intent_class: IntentClass
    discovery_profile: str
    proposed_first_artifact: str = "project_discovery"
    clarifications: Dict[str, ClarificationDetail]
    known_unknowns: List[str]
    governance_flags: GovernanceFlags


# =============================================================================
# SIMPLE EVENT PAYLOADS
# =============================================================================

class SessionCreated(BaseModel):
    """Session created event."""
    origin_route: Optional[str] = None


class OrientationViewed(BaseModel):
    """User viewed orientation phase."""
    pass


class IntentConfirmed(BaseModel):
    """User confirmed reflected intent."""
    pass


class IntentRevised(BaseModel):
    """User requested intent revision."""
    reason: Optional[str] = None


class ClarificationCompleted(BaseModel):
    """All clarifications answered."""
    answered_count: int


class ConsentAccepted(BaseModel):
    """User accepted consent."""
    pass


class ConsentDeclined(BaseModel):
    """User declined consent."""
    reason: Optional[str] = None


class SessionAbandoned(BaseModel):
    """Session abandoned by user."""
    phase: Optional[str] = None


class SessionExpired(BaseModel):
    """Session expired due to timeout."""
    pass


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================

class CreateSessionRequest(BaseModel):
    """Request to create new intake session."""
    origin_route: Optional[str] = "/start"


class CreateSessionResponse(BaseModel):
    """Response after creating session."""
    session_id: str
    state: SessionState
    expires_at: str


class SubmitIntentRequest(BaseModel):
    """Request to submit user intent."""
    raw_text: str = Field(..., min_length=1)
    attachments: Optional[List[AttachmentSchema]] = None


class SubmitIntentResponse(BaseModel):
    """Response after submitting intent."""
    reflection: IntentReflectionProposed
    state: SessionState


class ConfirmIntentResponse(BaseModel):
    """Response after confirming intent."""
    questions: List[ClarificationQuestion]
    state: SessionState


class SubmitAnswerRequest(BaseModel):
    """Request to submit clarification answer."""
    question_id: str
    answer: Any


class SubmitAnswerResponse(BaseModel):
    """Response after submitting answer."""
    remaining_questions: int
    state: SessionState


class ConsentRequest(BaseModel):
    """Request to accept/decline consent."""
    accept: bool


class ConsentResponse(BaseModel):
    """Response after consent decision."""
    project_id: Optional[str] = None
    state: SessionState


class SessionStatusResponse(BaseModel):
    """Response for session status query."""
    session: Dict[str, Any]
    events: List[Dict[str, Any]]
    current_state: SessionState
