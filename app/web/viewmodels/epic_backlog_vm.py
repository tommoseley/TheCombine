"""
ViewModels for Epic Backlog view.

Per ADR-030: Templates consume ViewModels exclusively.
All formatting and presentation shaping occurs in the BFF.
"""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class OpenQuestionVM(BaseModel):
    """ViewModel for epic open question (aligned with OpenQuestionV1 schema)."""
    id: str = ""
    question: str = ""  # Maps to 'text' in canonical schema
    blocking: bool = False
    why_it_matters: str = ""
    priority: Optional[str] = None
    options: List[dict] = []
    notes: Optional[str] = None
    directed_to: Optional[str] = None  # Not in canonical schema, kept for display


class DependencyVM(BaseModel):
    """ViewModel for epic dependency."""
    depends_on_epic_id: str = ""
    reason: str = ""


class RelatedDiscoveryVM(BaseModel):
    """ViewModel for related discovery items."""
    risks: List[str] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    early_decision_points: List[str] = Field(default_factory=list)


class EpicCardVM(BaseModel):
    """ViewModel for a single epic card."""
    epic_id: str = ""
    name: str = "Untitled Epic"
    intent: str = ""
    
    # Display computed
    mvp_phase: str = "later"  # "mvp" | "later"
    
    # Content sections
    business_value: Optional[str] = None
    in_scope: List[str] = Field(default_factory=list)
    out_of_scope: List[str] = Field(default_factory=list)
    primary_outcomes: List[str] = Field(default_factory=list)
    open_questions: List[OpenQuestionVM] = Field(default_factory=list)
    dependencies: List[DependencyVM] = Field(default_factory=list)
    architecture_attention_points: List[str] = Field(default_factory=list)
    related_discovery_items: Optional[RelatedDiscoveryVM] = None
    
    # Navigation
    detail_href: str = ""


class EpicBacklogSectionVM(BaseModel):
    """ViewModel for a section of epics (MVP, Later, etc.)."""
    id: str = ""
    title: str = ""
    icon: str = "layers"
    description: Optional[str] = None
    empty_message: str = "No epics in this section."
    epics: List[EpicCardVM] = Field(default_factory=list)
    
    @property
    def count(self) -> int:
        return len(self.epics)


class EpicSetSummaryVM(BaseModel):
    """ViewModel for epic set summary."""
    overall_intent: Optional[str] = None
    mvp_definition: Optional[str] = None
    key_constraints: List[str] = Field(default_factory=list)
    out_of_scope: List[str] = Field(default_factory=list)


class RiskVM(BaseModel):
    """ViewModel for risk overview item."""
    description: str = ""
    impact: str = ""
    affected_epics: List[str] = Field(default_factory=list)


class EpicBacklogVM(BaseModel):
    """Top-level ViewModel for Epic Backlog view."""
    # Identity
    project_id: str = ""
    project_name: str = ""
    document_id: Optional[str] = None
    
    # Display
    title: str = "Epic Backlog"
    subtitle: Optional[str] = None
    last_updated_label: Optional[str] = None
    
    # Content
    epic_set_summary: Optional[EpicSetSummaryVM] = None
    sections: List[EpicBacklogSectionVM] = Field(default_factory=list)
    risks_overview: List[RiskVM] = Field(default_factory=list)
    recommendations_for_architecture: List[str] = Field(default_factory=list)
    
    # State
    exists: bool = True
    message: Optional[str] = None
    
    # Computed properties
    @property
    def mvp_count(self) -> int:
        for s in self.sections:
            if s.id == "mvp":
                return s.count
        return 0
    
    @property
    def later_count(self) -> int:
        for s in self.sections:
            if s.id == "later":
                return s.count
        return 0