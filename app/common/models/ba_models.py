"""
BA Mentor Output Schema Models

Pydantic models for validating BA Mentor output.
BA stories are implementation-ready stories derived from PM Epic and Architecture.
"""

from typing import List, Literal
from pydantic import BaseModel, Field, field_validator
import re


class BAStory(BaseModel):
    """
    Single BA story with implementation details.
    
    BA stories are atomic, testable units of work that can be assigned to developers.
    Each story maps to specific architectural components and references PM stories.
    """
    
    id: str = Field(
        ...,
        description="BA story ID in format {epic_id}-{NNN} (e.g., MATH-001-001, AUTH-200-015)",
        min_length=1
    )
    
    title: str = Field(
        ...,
        description="Concise, action-oriented title (e.g., 'Implement user registration API')",
        min_length=1,
        max_length=200
    )
    
    description: str = Field(
        ...,
        description="2-4 sentences explaining what needs to be built and why",
        min_length=1
    )
    
    related_pm_story_ids: List[str] = Field(
        default_factory=list,
        description="Array of PM story IDs this BA story implements"
    )
    
    related_arch_components: List[str] = Field(
        ...,
        description="Array of architecture component IDs (must be non-empty)",
        min_length=1
    )
    
    acceptance_criteria: List[str] = Field(
        ...,
        description="Testable acceptance criteria (minimum 3 required)",
        min_length=3
    )
    
    notes: List[str] = Field(
        default_factory=list,
        description="Implementation hints, technical considerations, dependencies"
    )
    
    mvp_phase: Literal["mvp", "later-phase"] = Field(
        ...,
        description="Delivery phase, should align with related architecture components"
    )
    
    @field_validator("id")
    @classmethod
    def validate_ba_story_id(cls, v: str) -> str:
        """Validate BA story ID format: {epic_id}-{NNN}"""
        pattern = r"^[A-Z0-9]+-[0-9]{3}-[0-9]{3}$"
        if not re.match(pattern, v):
            raise ValueError(
                f"BA story ID must match pattern {pattern}. "
                f"Expected format: EPIC-NNN-NNN (e.g., MATH-001-001, AUTH-200-015). "
                f"Got: {v}"
            )
        return v
    
    @field_validator("related_pm_story_ids")
    @classmethod
    def validate_pm_story_ids(cls, v: List[str]) -> List[str]:
        """Validate PM story ID format if provided"""
        if not v:
            return v
        
        pattern = r"^[A-Z0-9]+-[0-9]{3}-[0-9]{3}$"
        for story_id in v:
            if not re.match(pattern, story_id):
                raise ValueError(
                    f"PM story ID must match pattern {pattern}. "
                    f"Expected format: EPIC-NNN-NNN. "
                    f"Got: {story_id}"
                )
        return v
    
    @field_validator("acceptance_criteria")
    @classmethod
    def validate_acceptance_criteria(cls, v: List[str]) -> List[str]:
        """Ensure all acceptance criteria are non-empty"""
        for idx, criterion in enumerate(v):
            if not criterion.strip():
                raise ValueError(f"Acceptance criterion at index {idx} is empty")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "id": "MATH-001-001",
                "title": "Implement addition question generation API",
                "description": "Build POST /api/questions/generate endpoint that accepts grade level and returns random addition problems with multiple choice options. Integrate with question-generation-service component.",
                "related_pm_story_ids": ["MATH-001-001"],
                "related_arch_components": ["question-generation-service", "api-gateway"],
                "acceptance_criteria": [
                    "Endpoint validates grade level parameter (K-6)",
                    "Generates problems with operands appropriate for grade level",
                    "Returns 4 multiple choice options including correct answer",
                    "Validates mathematical correctness of all options",
                    "Returns 201 Created with problem data on success",
                    "Returns 400 Bad Request for invalid grade level"
                ],
                "notes": [
                    "Use existing random number generator from question-generation-service",
                    "Consider caching problem templates for performance"
                ],
                "mvp_phase": "mvp"
            }
        }


class BAStorySet(BaseModel):
    """
    Complete set of BA stories for an Epic.
    
    Output from BA Mentor containing all implementation-ready stories
    derived from PM Epic and Architecture specification.
    """
    
    project_name: str = Field(
        ...,
        description="Project name, echoed from PM Epic",
        min_length=1
    )
    
    epic_id: str = Field(
        ...,
        description="Epic identifier, echoed from PM Epic (e.g., MATH-001, AUTH-200)",
        min_length=1
    )
    
    ba_stories: List[BAStory] = Field(
        ...,
        description="Array of implementation-ready BA stories",
        min_length=1
    )
    
    @field_validator("epic_id")
    @classmethod
    def validate_epic_id(cls, v: str) -> str:
        """Validate Epic ID format: {PREFIX}-{NNN}"""
        pattern = r"^[A-Z0-9]+-[0-9]{3}$"
        if not re.match(pattern, v):
            raise ValueError(
                f"Epic ID must match pattern {pattern}. "
                f"Expected format: PREFIX-NNN (e.g., MATH-001, AUTH-200). "
                f"Got: {v}"
            )
        return v
    
    @field_validator("ba_stories")
    @classmethod
    def validate_story_ids_match_epic(cls, v: List[BAStory], info) -> List[BAStory]:
        """Validate all BA story IDs start with the epic_id"""
        if not info.data:
            return v
            
        epic_id = info.data.get("epic_id")
        if not epic_id:
            return v
        
        for story in v:
            if not story.id.startswith(f"{epic_id}-"):
                raise ValueError(
                    f"BA story ID '{story.id}' does not start with epic_id '{epic_id}'. "
                    f"Expected format: {epic_id}-NNN"
                )
        return v
    
    @field_validator("ba_stories")
    @classmethod
    def validate_story_ids_sequential(cls, v: List[BAStory]) -> List[BAStory]:
        """Validate BA story IDs are sequential with no gaps"""
        if len(v) <= 1:
            return v
        
        # Extract sequence numbers from story IDs
        sequence_numbers = []
        for story in v:
            # ID format: EPIC-NNN-NNN, extract last NNN
            parts = story.id.split("-")
            if len(parts) >= 3:
                try:
                    seq_num = int(parts[-1])
                    sequence_numbers.append(seq_num)
                except ValueError:
                    raise ValueError(f"Invalid sequence number in story ID: {story.id}")
        
        # Check for sequential ordering
        sorted_seqs = sorted(sequence_numbers)
        expected = list(range(sorted_seqs[0], sorted_seqs[0] + len(sorted_seqs)))
        
        if sorted_seqs != expected:
            raise ValueError(
                f"BA story IDs must be sequential with no gaps. "
                f"Found: {sorted_seqs}, Expected: {expected}"
            )
        
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "project_name": "Math Testing Platform",
                "epic_id": "MATH-001",
                "ba_stories": [
                    {
                        "id": "MATH-001-001",
                        "title": "Implement addition question generation API",
                        "description": "Build POST /api/questions/generate endpoint for addition problems.",
                        "related_pm_story_ids": ["MATH-001-001"],
                        "related_arch_components": ["question-generation-service"],
                        "acceptance_criteria": [
                            "Endpoint validates grade level parameter",
                            "Generates age-appropriate problems",
                            "Returns correct answer with distractors"
                        ],
                        "notes": [],
                        "mvp_phase": "mvp"
                    },
                    {
                        "id": "MATH-001-002",
                        "title": "Build question validation service",
                        "description": "Create service to validate mathematical correctness of generated problems.",
                        "related_pm_story_ids": ["MATH-001-001"],
                        "related_arch_components": ["question-generation-service"],
                        "acceptance_criteria": [
                            "Validates correct answer matches operands",
                            "Ensures distractors are incorrect",
                            "Checks for duplicate answer choices"
                        ],
                        "notes": ["Run validation before returning to API"],
                        "mvp_phase": "mvp"
                    }
                ]
            }
        }


# Type aliases for convenience
BAStorySetDict = dict
BAStoryDict = dict