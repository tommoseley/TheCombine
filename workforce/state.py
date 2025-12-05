# workforce/state.py

"""Pipeline state definitions and transitions."""

from enum import Enum
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List


class PipelineState(Enum):
    """Pipeline execution states."""
    IDLE = "idle"
    PM_PHASE = "pm_phase"
    ARCH_PHASE = "arch_phase"
    BA_PHASE = "ba_phase"
    DEV_PHASE = "dev_phase"
    QA_PHASE = "qa_phase"
    COMMIT_PHASE = "commit_phase"
    COMPLETE = "complete"
    FAILED = "failed"
    RELOADING_CANON = "reloading_canon"


@dataclass
class StateTransition:
    """Represents a state transition with metadata."""
    from_state: PipelineState
    to_state: PipelineState
    timestamp: datetime
    reason: str


# Valid transitions (enforces canonical flow)
VALID_TRANSITIONS: Dict[PipelineState, List[PipelineState]] = {
    PipelineState.IDLE: [PipelineState.PM_PHASE, PipelineState.RELOADING_CANON, PipelineState.FAILED],
    PipelineState.PM_PHASE: [PipelineState.ARCH_PHASE, PipelineState.FAILED],
    PipelineState.ARCH_PHASE: [PipelineState.BA_PHASE, PipelineState.FAILED],
    PipelineState.BA_PHASE: [PipelineState.DEV_PHASE, PipelineState.FAILED],
    PipelineState.DEV_PHASE: [PipelineState.QA_PHASE, PipelineState.FAILED],
    PipelineState.QA_PHASE: [PipelineState.COMMIT_PHASE, PipelineState.DEV_PHASE, PipelineState.FAILED],
    PipelineState.COMMIT_PHASE: [PipelineState.COMPLETE, PipelineState.FAILED],
    PipelineState.COMPLETE: [PipelineState.IDLE],
    PipelineState.FAILED: [PipelineState.IDLE, PipelineState.RELOADING_CANON],
    PipelineState.RELOADING_CANON: [PipelineState.IDLE, PipelineState.FAILED],
}


def validate_transition(from_state: PipelineState, to_state: PipelineState) -> bool:
    """
    Validate state transition is allowed.
    
    Args:
        from_state: Current state
        to_state: Target state
        
    Returns:
        True if transition is valid, False otherwise
    """
    return to_state in VALID_TRANSITIONS.get(from_state, [])