"""Tests for Concierge Service (WS-CONCIERGE-001)"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

def test_import_concierge_service():
    """Verify ConciergeService can be imported."""
    from app.domain.services.concierge_service import ConciergeService
    assert ConciergeService is not None

def test_import_schemas():
    """Verify concierge schemas can be imported."""
    from app.domain.schemas.concierge_events import IntentClass, SessionState, EventType
    assert IntentClass is not None
    assert SessionState is not None
    assert EventType is not None

def test_import_models():
    """Verify concierge models can be imported."""
    from app.api.models.concierge_intake import ConciergeIntakeSession, ConciergeIntakeEvent
    assert ConciergeIntakeSession is not None
    assert ConciergeIntakeEvent is not None

def test_service_initialization():
    """Verify service can be initialized with mocks."""
    from app.domain.services.concierge_service import ConciergeService
    
    mock_db = MagicMock()
    mock_llm = AsyncMock()
    
    service = ConciergeService(mock_db, mock_llm)
    assert service.db == mock_db
    assert service.llm_service == mock_llm

def test_question_packs_loaded():
    """Verify question packs are loaded on init."""
    from app.domain.services.concierge_service import ConciergeService
    
    service = ConciergeService(MagicMock(), AsyncMock())
    assert service._question_packs is not None
    assert "profiles" in service._question_packs

def test_max_4_questions_per_profile():
    """Verify no profile exceeds 4 questions."""
    from app.domain.services.concierge_service import ConciergeService
    
    service = ConciergeService(MagicMock(), AsyncMock())
    profiles = service._question_packs["profiles"]
    
    for profile_name, profile_data in profiles.items():
        questions = profile_data.get("questions", [])
        assert len(questions) <= 4, f"{profile_name} has {len(questions)} questions (max 4)"
