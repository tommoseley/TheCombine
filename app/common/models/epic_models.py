"""
Epic Models - PM Mentor Schema V1

Pydantic models for PM Epic output validation.
These models match the canonical Epic schema stored in the database.
"""

from typing import List, Literal
from pydantic import BaseModel, Field


# ============================================================================
# EPIC MODELS - PM MENTOR OUTPUT
# ============================================================================

class EpicSummary(BaseModel):
    """Epic summary metadata"""
    title: str
    refined_description: str
    business_value: str
    primary_users: List[str] = Field(default_factory=list)
    success_metrics: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "forbid"


class EpicScope(BaseModel):
    """Scope boundaries"""
    in_scope: List[str] = Field(default_factory=list)
    out_of_scope: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "forbid"


class PMPerspective(BaseModel):
    """Individual PM perspective - all fields are lists, never null"""
    key_concerns: List[str] = Field(default_factory=list)
    suggested_slices: List[str] = Field(default_factory=list)
    usage_flows: List[str] = Field(default_factory=list)
    required_controls: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "forbid"


class PMPerspectives(BaseModel):
    """All three PM perspectives"""
    delivery_pm: PMPerspective
    experience_pm: PMPerspective
    risk_compliance_pm: PMPerspective
    
    class Config:
        extra = "forbid"


class Story(BaseModel):
    """Individual story within the Epic"""
    id: str
    title: str
    description: str
    type: Literal["feature", "spike", "chore"]
    acceptance_criteria: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "forbid"


class EpicSchema(BaseModel):
    """
    Canonical Epic Schema V1
    
    This is what PM Mentor returns based on the current prompt.
    All list fields use empty arrays [] as defaults, never null.
    """
    project_name: str
    epic_id: str
    epic_summary: EpicSummary
    goals: List[str] = Field(default_factory=list)
    non_goals: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    scope: EpicScope
    business_goals: List[str] = Field(default_factory=list)
    known_unknowns: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    pm_perspectives: PMPerspectives
    stories: List[Story] = Field(default_factory=list)
    
    class Config:
        extra = "forbid"
        json_schema_extra = {
            "example": {
                "project_name": "user-auth",
                "epic_id": "AUTH-100",
                "epic_summary": {
                    "title": "User Authentication System",
                    "refined_description": "Implement secure authentication...",
                    "business_value": "Enable personalized user experience",
                    "primary_users": ["end users", "developers"],
                    "success_metrics": ["99% uptime", "sub-100ms response"]
                },
                "goals": ["Secure login", "Password reset"],
                "non_goals": ["OAuth", "2FA"],
                "constraints": ["JSON-only API"],
                "acceptance_criteria": ["Users can login", "Sessions expire"],
                "scope": {
                    "in_scope": ["Email/password auth", "JWT tokens"],
                    "out_of_scope": ["Social login", "Biometrics"]
                },
                "business_goals": ["Reduce support burden", "Enable personalization"],
                "known_unknowns": ["Peak concurrent users"],
                "open_questions": ["Password complexity rules?"],
                "risks": ["Brute force attacks"],
                "pm_perspectives": {
                    "delivery_pm": {
                        "key_concerns": ["Incremental delivery"],
                        "suggested_slices": ["Core auth first", "Add reset later"],
                        "usage_flows": [],
                        "required_controls": []
                    },
                    "experience_pm": {
                        "key_concerns": ["Clear error messages"],
                        "suggested_slices": [],
                        "usage_flows": ["User enters credentials"],
                        "required_controls": []
                    },
                    "risk_compliance_pm": {
                        "key_concerns": ["Password security"],
                        "suggested_slices": [],
                        "usage_flows": [],
                        "required_controls": ["Rate limiting", "Audit logs"]
                    }
                },
                "stories": [
                    {
                        "id": "AUTH-100-001",
                        "title": "Implement login endpoint",
                        "description": "Create POST /login endpoint",
                        "type": "feature",
                        "acceptance_criteria": ["Accepts email/password", "Returns JWT"],
                        "notes": ["Use bcrypt for passwords"]
                    }
                ]
            }
        }