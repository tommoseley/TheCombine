from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class PipelineStage(str, Enum):
    NOT_STARTED = "not_started"
    PM_QUESTIONS = "pm_questions"
    AWAITING_USER_ANSWERS = "awaiting_user_answers"
    EPIC_APPROVAL = "epic_approval"
    ARCHITECTURE_START = "architecture_start"
    ARCHITECTURE_APPROVAL = "architecture_approval"
    BA_START = "ba_start"
    BACKLOG_APPROVAL = "backlog_approval"
    COMPLETED = "completed"


# Ordered transitions — define the canonical pipeline path.
LEGAL_TRANSITIONS: Dict[PipelineStage, set[PipelineStage]] = {
    PipelineStage.NOT_STARTED: {PipelineStage.PM_QUESTIONS},
    PipelineStage.PM_QUESTIONS: {PipelineStage.AWAITING_USER_ANSWERS},
    PipelineStage.AWAITING_USER_ANSWERS: {PipelineStage.EPIC_APPROVAL},
    PipelineStage.EPIC_APPROVAL: {PipelineStage.ARCHITECTURE_START},
    PipelineStage.ARCHITECTURE_START: {PipelineStage.ARCHITECTURE_APPROVAL},
    PipelineStage.ARCHITECTURE_APPROVAL: {PipelineStage.BA_START},
    PipelineStage.BA_START: {PipelineStage.BACKLOG_APPROVAL},
    PipelineStage.BACKLOG_APPROVAL: {PipelineStage.COMPLETED},
    PipelineStage.COMPLETED: set(),
}


@dataclass
class PipelineStateData:
    stage: PipelineStage
    # You can expand this later (context, orchestration status, etc.)


class InvalidPipelineTransition(Exception):
    pass


class PipelineStateMachine:
    """
    Very small helper for enforcing stage transitions.
    """

    def __init__(self, current_stage: str):
        try:
            self.stage = PipelineStage(current_stage)
        except ValueError:
            raise InvalidPipelineTransition(
                f"Unknown pipeline stage: {current_stage}"
            )

    def allowed_next(self):
        return LEGAL_TRANSITIONS[self.stage]

    def can_transition_to(self, next_stage: str) -> bool:
        try:
            next_enum = PipelineStage(next_stage)
        except ValueError:
            return False

        return next_enum in LEGAL_TRANSITIONS[self.stage]

    def transition(self, next_stage: str) -> PipelineStage:
        if not self.can_transition_to(next_stage):
            raise InvalidPipelineTransition(
                f"Illegal transition: {self.stage.value} → {next_stage}"
            )
        self.stage = PipelineStage(next_stage)
        return self.stage
