"""
Concierge Service - orchestrates intake sessions and state machine.

Implements CONCIERGE_PROJECT_INGESTION_CONTRACT v1.0
Manages user intake from curiosity to governed work context.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta
import jsonschema

from sqlalchemy.orm import Session

from app.api.models.concierge_intake import ConciergeIntakeSession, ConciergeIntakeEvent
from app.api.models.project import Project
from app.domain.schemas.concierge_events import (
    IntentClass,
    SessionState,
    EventType,
    Confidence,
    UserIntentSubmitted,
    IntentReflectionProposed,
    ClarificationQuestionsIssued,
    ClarificationAnswerSubmitted,
    ConsentPresented,
    HandoffEmitted,
    SessionCreated,
    OrientationViewed,
    IntentConfirmed,
    IntentRevised,
    ClarificationCompleted,
    ConsentAccepted,
    ConsentDeclined,
    SessionAbandoned,
    SessionExpired,
    WillCreate,
    WillGenerate,
    ClarificationDetail,
    GovernanceFlags,
)

logger = logging.getLogger(__name__)


class SessionExpiredException(Exception):
    """Raised when attempting to use an expired session."""
    pass


class InvalidStateTransitionException(Exception):
    """Raised when attempting an invalid state transition."""
    pass


class ConciergeService:
    """
    Concierge Service - manages intake sessions and state machine.
    
    Responsibilities:
    - Load and validate question packs from JSON
    - Create and manage intake sessions
    - Enforce state machine transitions
    - Append events with monotonic sequence numbers
    - Integrate with LLM for intent reflection
    - Build and emit handoff contracts
    - Trigger Project Discovery generation
    """
    
    def __init__(self, db: Session, llm_service=None):
        """
        Initialize service and load question packs.
        
        Args:
            db: SQLAlchemy database session
            llm_service: Optional LLM service for intent reflection
        """
        self.db = db
        self.llm_service = llm_service
        self._question_packs = self._load_question_packs()
        logger.info("ConciergeService initialized with %d question profiles", 
                   len(self._question_packs.get("profiles", {})))
    
    def _load_question_packs(self) -> Dict:
        """
        Load and validate question packs from JSON.
        
        Returns:
            Validated question pack data
            
        Raises:
            FileNotFoundError: If pack file missing
            jsonschema.ValidationError: If pack fails validation
        """
        pack_path = Path("seed/question_packs/discovery_question_packs.json")
        schema_path = Path("seed/question_packs/schema.json")
        
        if not pack_path.exists():
            raise FileNotFoundError(f"Question packs not found: {pack_path}")
        
        if not schema_path.exists():
            raise FileNotFoundError(f"Question pack schema not found: {schema_path}")
        
        # Load data
        with open(pack_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Load and validate schema
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        
        jsonschema.validate(data, schema)
        
        logger.info("Question packs loaded and validated: version %s", data.get("version"))
        return data
    
    # =========================================================================
    # SESSION LIFECYCLE
    # =========================================================================
    
    def create_session(
        self,
        user_id: UUID,
        origin_route: str = "/start"
    ) -> ConciergeIntakeSession:
        """
        Create new intake session.
        
        Args:
            user_id: User creating the session
            origin_route: Route where session was initiated
            
        Returns:
            New session in 'idle' state
        """
        session = ConciergeIntakeSession(
            user_id=user_id,
            state=SessionState.IDLE.value,
            origin_route=origin_route,
            version="1.0"
        )
        
        self.db.add(session)
        self.db.flush()  # Get ID
        
        # Append session_created event
        self.append_event(
            session.id,
            EventType.SESSION_CREATED,
            SessionCreated(origin_route=origin_route).dict()
        )
        
        self.db.commit()
        
        logger.info("Created intake session %s for user %s", session.id, user_id)
        return session
    
    def get_session_with_events(
        self,
        session_id: UUID
    ) -> Tuple[ConciergeIntakeSession, List[ConciergeIntakeEvent]]:
        """
        Retrieve session with all events, checking expiry.
        
        Args:
            session_id: Session ID
            
        Returns:
            Tuple of (session, events)
            
        Raises:
            SessionExpiredException: If session expired
        """
        session = self.db.query(ConciergeIntakeSession).filter_by(id=session_id).first()
        
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Check expiry
        if session.is_expired() and session.state != SessionState.SESSION_EXPIRED.value:
            # Transition to expired state
            session.state = SessionState.SESSION_EXPIRED.value
            session.updated_at = datetime.utcnow()
            
            self.append_event(
                session_id,
                EventType.SESSION_EXPIRED,
                SessionExpired().dict()
            )
            
            self.db.commit()
            
            raise SessionExpiredException(
                f"Session {session_id} expired at {session.expires_at}"
            )
        
        # Get events in sequence order
        events = self.db.query(ConciergeIntakeEvent)\
            .filter_by(session_id=session_id)\
            .order_by(ConciergeIntakeEvent.seq)\
            .all()
        
        return session, events
    
    def abandon_session(self, session_id: UUID, phase: Optional[str] = None) -> None:
        """
        Mark session as abandoned.
        
        Args:
            session_id: Session to abandon
            phase: Optional phase where abandonment occurred
        """
        session, _ = self.get_session_with_events(session_id)
        
        if session.state not in [
            SessionState.COMPLETED.value,
            SessionState.ABANDONED.value,
            SessionState.SESSION_EXPIRED.value
        ]:
            self.transition_state(session_id, SessionState.ABANDONED)
            
            self.append_event(
                session_id,
                EventType.SESSION_ABANDONED,
                SessionAbandoned(phase=phase).dict()
            )
            
            self.db.commit()
            
            logger.info("Session %s abandoned at phase %s", session_id, phase)
    
    # =========================================================================
    # STATE MACHINE
    # =========================================================================
    
    # Valid state transitions per contract section 6.2
    VALID_TRANSITIONS = {
        SessionState.IDLE: [SessionState.ORIENTING],
        SessionState.ORIENTING: [SessionState.CAPTURING_INTENT],
        SessionState.CAPTURING_INTENT: [SessionState.CONFIRMING_INTENT],
        SessionState.CONFIRMING_INTENT: [SessionState.CLARIFYING, SessionState.CAPTURING_INTENT],
        SessionState.CLARIFYING: [SessionState.CONSENT_GATE, SessionState.CAPTURING_INTENT],
        SessionState.CONSENT_GATE: [SessionState.HANDOFF_EMITTED, SessionState.ABANDONED],
        SessionState.HANDOFF_EMITTED: [SessionState.COMPLETED],
        SessionState.COMPLETED: [],
        SessionState.ABANDONED: [],
        SessionState.SESSION_EXPIRED: [],
    }
    
    def transition_state(
        self,
        session_id: UUID,
        new_state: SessionState
    ) -> ConciergeIntakeSession:
        """
        Transition session to new state with validation.
        
        Args:
            session_id: Session to transition
            new_state: Target state
            
        Returns:
            Updated session
            
        Raises:
            InvalidStateTransitionException: If transition invalid
        """
        session, _ = self.get_session_with_events(session_id)
        
        current = SessionState(session.state)
        
        # Check if transition is valid
        valid_next = self.VALID_TRANSITIONS.get(current, [])
        if new_state not in valid_next:
            raise InvalidStateTransitionException(
                f"Cannot transition from {current.value} to {new_state.value}. "
                f"Valid transitions: {[s.value for s in valid_next]}"
            )
        
        session.state = new_state.value
        session.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info("Session %s: %s -> %s", session_id, current.value, new_state.value)
        return session
    
    # =========================================================================
    # EVENT HANDLING
    # =========================================================================
    
    def append_event(
        self,
        session_id: UUID,
        event_type: EventType,
        payload: Dict
    ) -> ConciergeIntakeEvent:
        """
        Append event with monotonic sequence number.
        
        Args:
            session_id: Session ID
            event_type: Type of event
            payload: Event payload (must match schema)
            
        Returns:
            Created event
        """
        # Get max sequence number for this session
        max_seq = self.db.query(ConciergeIntakeEvent.seq)\
            .filter_by(session_id=session_id)\
            .order_by(ConciergeIntakeEvent.seq.desc())\
            .first()
        
        next_seq = (max_seq[0] + 1) if max_seq else 1
        
        event = ConciergeIntakeEvent(
            session_id=session_id,
            seq=next_seq,
            event_type=event_type.value,
            payload_json=payload
        )
        
        self.db.add(event)
        self.db.flush()
        
        logger.debug("Event %s appended to session %s (seq %d)", 
                    event_type.value, session_id, next_seq)
        
        return event
    
    # =========================================================================
    # QUESTION PACKS & PROFILES
    # =========================================================================
    
    def get_profile_for_intent(self, intent_class: IntentClass) -> str:
        """
        Map intent class to discovery profile.
        
        Args:
            intent_class: Classified intent
            
        Returns:
            Discovery profile name
        """
        mapping = self._question_packs.get("intent_mapping", {})
        profile = mapping.get(intent_class.value, self._question_packs.get("default_profile", "general"))
        
        logger.debug("Mapped intent %s to profile %s", intent_class.value, profile)
        return profile
    
    def get_questions_for_profile(self, profile: str) -> List[Dict]:
        """
        Get clarification questions for discovery profile.
        
        Args:
            profile: Discovery profile name
            
        Returns:
            List of questions (max 4)
        """
        profiles = self._question_packs.get("profiles", {})
        
        # Use default if profile not found
        if profile not in profiles:
            logger.warning("Profile %s not found, using default", profile)
            profile = self._question_packs.get("default_profile", "general")
        
        profile_data = profiles.get(profile, {})
        questions = profile_data.get("questions", [])
        
        # Enforce max 4 questions
        questions = questions[:4]
        
        logger.info("Retrieved %d questions for profile %s", len(questions), profile)
        return questions
    
    # =========================================================================
    # LLM INTEGRATION
    # =========================================================================
    
    async def reflect_intent(
        self,
        raw_text: str,
        session_id: UUID
    ) -> IntentReflectionProposed:
        """
        Use LLM to reflect and classify user intent.
        
        This integrates with existing LLM logging (ADR-010).
        
        Args:
            raw_text: User's raw intent statement
            session_id: Session ID for correlation
            
        Returns:
            Intent reflection with classification
            
        Note:
            If LLM fails, returns intent_class="unknown" with low confidence
        """
        if not self.llm_service:
            # Fallback if no LLM service
            logger.warning("No LLM service available, returning unknown classification")
            return IntentReflectionProposed(
                reflection_text=raw_text,
                intent_class=IntentClass.UNKNOWN,
                confidence=Confidence.LOW,
                known_unknowns=["LLM service not available for classification"]
            )
        
        try:
            # TODO: Implement actual LLM call
            # This should:
            # 1. Load prompt from seed/prompts/tasks/Concierge Intent Reflection v1.0.txt
            # 2. Call LLM service with prompt + raw_text
            # 3. Log execution via LLMExecutionLogger
            # 4. Parse response into IntentReflectionProposed
            # 5. Validate against schema
            
            # Placeholder for v1
            logger.info("LLM reflection called for session %s", session_id)
            
            # Return mock response for now
            return IntentReflectionProposed(
                reflection_text=f"You want to {raw_text[:100]}",
                intent_class=IntentClass.UNKNOWN,
                confidence=Confidence.MEDIUM,
                candidate_discovery_profile="general",
                known_unknowns=[]
            )
            
        except Exception as e:
            logger.error("LLM reflection failed: %s", e)
            return IntentReflectionProposed(
                reflection_text=raw_text,
                intent_class=IntentClass.UNKNOWN,
                confidence=Confidence.LOW,
                known_unknowns=[f"LLM reflection failed: {str(e)}"]
            )
    
    # =========================================================================
    # HANDOFF CONTRACT
    # =========================================================================
    
    def validate_handoff_ready(
        self,
        session_id: UUID
    ) -> Tuple[bool, List[str]]:
        """
        Validate if session is ready for handoff.
        
        Args:
            session_id: Session to validate
            
        Returns:
            Tuple of (is_ready, error_messages)
        """
        session, events = self.get_session_with_events(session_id)
        
        errors = []
        
        # Check state
        if session.state != SessionState.CONSENT_GATE.value:
            errors.append(f"Session not at consent gate (current: {session.state})")
        
        # Check for intent reflection
        has_reflection = any(
            e.event_type == EventType.INTENT_REFLECTION_PROPOSED.value
            for e in events
        )
        if not has_reflection:
            errors.append("No intent reflection found")
        
        # Check for consent presentation
        has_consent = any(
            e.event_type == EventType.CONSENT_PRESENTED.value
            for e in events
        )
        if not has_consent:
            errors.append("Consent not presented")
        
        return len(errors) == 0, errors
    
    def emit_handoff(
        self,
        session_id: UUID,
        user_id: UUID
    ) -> Tuple[HandoffEmitted, UUID]:
        """
        Build and emit handoff contract, create project.
        
        This is called after consent_accepted.
        
        Args:
            session_id: Session ID
            user_id: User ID
            
        Returns:
            Tuple of (handoff_contract, project_id)
        """
        session, events = self.get_session_with_events(session_id)
        
        # Validate ready
        is_ready, errors = self.validate_handoff_ready(session_id)
        if not is_ready:
            raise ValueError(f"Session not ready for handoff: {errors}")
        
        # Extract data from events
        intent_summary = ""
        intent_class = IntentClass.UNKNOWN
        discovery_profile = "general"
        clarifications = {}
        known_unknowns = []
        
        for event in events:
            if event.event_type == EventType.INTENT_REFLECTION_PROPOSED.value:
                reflection = IntentReflectionProposed(**event.payload_json)
                intent_summary = reflection.reflection_text
                intent_class = reflection.intent_class
                discovery_profile = self.get_profile_for_intent(intent_class)
                known_unknowns.extend(reflection.known_unknowns)
            
            elif event.event_type == EventType.CLARIFICATION_ANSWER_SUBMITTED.value:
                answer = ClarificationAnswerSubmitted(**event.payload_json)
                clarifications[answer.question_id] = ClarificationDetail(
                    answer=answer.answer,
                    confidence=answer.confidence
                ).dict()
        
        # Create project
        project = Project(
            name=f"Project from Concierge {session_id}",
            description=intent_summary,
            owner_id=user_id
        )
        self.db.add(project)
        self.db.flush()
        
        # Update session with project_id
        session.project_id = project.id
        
        # Build handoff contract
        handoff = HandoffEmitted(
            handoff_version="1.0",
            intent_summary=intent_summary,
            intent_class=intent_class,
            discovery_profile=discovery_profile,
            proposed_first_artifact="project_discovery",
            clarifications=clarifications,
            known_unknowns=known_unknowns,
            governance_flags=GovernanceFlags()
        )
        
        # Append event
        self.append_event(
            session_id,
            EventType.HANDOFF_EMITTED,
            handoff.dict()
        )
        
        # Transition state
        self.transition_state(session_id, SessionState.HANDOFF_EMITTED)
        
        self.db.commit()
        
        logger.info("Handoff emitted for session %s, project %s created", 
                   session_id, project.id)
        
        return handoff, project.id
    
    def trigger_discovery_generation(
        self,
        project_id: UUID,
        user_id: UUID,
        handoff: HandoffEmitted
    ) -> None:
        """
        Trigger Project Discovery generation with handoff context.
        
        Args:
            project_id: Project ID
            user_id: User ID
            handoff: Handoff contract
        """
        from app.domain.handlers.project_discovery_handler import ProjectDiscoveryHandler
        
        handler = ProjectDiscoveryHandler()
        
        # Generate discovery document with profile and context
        discovery_data = handler.generate_with_profile(
            project_id=str(project_id),
            user_id=str(user_id),
            discovery_profile=handoff.discovery_profile,
            handoff_context=handoff.dict()
        )
        
        logger.info("Discovery generation completed for project %s with profile %s",
                   project_id, handoff.discovery_profile)
        
        # TODO: Persist the discovery_data to database (Document record)
        # For v1, logging only - persistence will be added when full LLM integration is complete
