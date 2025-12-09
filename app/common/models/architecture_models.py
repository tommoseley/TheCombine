from typing import List, Literal
from pydantic import BaseModel, Field


# -----------------------------
# Core submodels / $defs
# -----------------------------

class ArchitectureSummary(BaseModel):
    title: str
    refined_description: str
    architectural_style: str
    key_decisions: List[str] = Field(default_factory=list)
    mvp_scope_notes: List[str] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class Component(BaseModel):
    id: str
    name: str
    purpose: str
    responsibilities: List[str] = Field(default_factory=list)
    layer: Literal[
        "presentation",
        "application",
        "domain",
        "infrastructure",
        "integration",
        "other",
    ]
    technology_choices: List[str] = Field(default_factory=list)
    depends_on_components: List[str] = Field(default_factory=list)
    mvp_phase: Literal["mvp", "later-phase"]

    class Config:
        extra = "forbid"


class DataField(BaseModel):
    name: str
    type: str
    required: bool
    validation_rules: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class DataEntity(BaseModel):
    name: str
    description: str
    fields: List[DataField] = Field(default_factory=list)
    primary_keys: List[str] = Field(default_factory=list)
    relationships: List[str] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class Endpoint(BaseModel):
    method: str
    path: str
    description: str
    request_schema: str
    response_schema: str
    error_cases: List[str] = Field(default_factory=list)
    idempotency: str
    authentication: str

    class Config:
        extra = "forbid"


class Interface(BaseModel):
    id: str
    name: str
    type: Literal[
        "internal_api",
        "external_api",
        "message_queue",
        "cli",
        "library",
        "other",
    ]
    description: str
    producer_components: List[str] = Field(default_factory=list)
    consumer_components: List[str] = Field(default_factory=list)
    protocol: str
    endpoints: List[Endpoint] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class WorkflowStep(BaseModel):
    order: int
    actor: str
    action: str
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class Workflow(BaseModel):
    id: str
    name: str
    trigger: str
    description: str
    steps: List[WorkflowStep] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class QualityAttribute(BaseModel):
    name: str
    target: str
    rationale: str
    acceptance_criteria: List[str] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class RiskItem(BaseModel):
    description: str
    impact: str
    likelihood: Literal["low", "medium", "high"]
    mitigation: str
    status: Literal["open", "mitigated", "accepted"]

    class Config:
        extra = "forbid"


class ArchitectureStory(BaseModel):
    id: str
    title: str
    description: str
    category: Literal[
        "design",
        "implementation",
        "infrastructure",
        "observability",
        "spike",
        "other",
    ]
    related_pm_story_ids: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    mvp_phase: Literal["mvp", "later-phase"]

    class Config:
        extra = "forbid"


# -----------------------------
# Context model
# -----------------------------

class ArchitectureContext(BaseModel):
    problem_statement: str
    constraints: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    non_goals: List[str] = Field(default_factory=list)

    class Config:
        extra = "forbid"


# -----------------------------
# Root document model
# -----------------------------

class ArchitectureDocument(BaseModel):
    """
    Root model matching ArchitectureSchema V1.
    This is what the Architect Mentor should return.
    """

    project_name: str
    epic_id: str
    architecture_summary: ArchitectureSummary
    context: ArchitectureContext

    components: List[Component] = Field(default_factory=list)
    data_model: List[DataEntity] = Field(default_factory=list)
    interfaces: List[Interface] = Field(default_factory=list)
    workflows: List[Workflow] = Field(default_factory=list)
    quality_attributes: List[QualityAttribute] = Field(default_factory=list)
    risks: List[RiskItem] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    stories: List[ArchitectureStory] = Field(default_factory=list)

    class Config:
        extra = "forbid"
