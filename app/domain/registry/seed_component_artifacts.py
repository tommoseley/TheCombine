"""
Seed data for component_artifacts and document_definitions tables.

Per ADR-034: Canonical components and document definitions are seeded as governed artifacts.

Usage:
    python -m app.domain.registry.seed_component_artifacts
    
Or call seed_component_artifacts(db) from your migration/startup.
"""

from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.api.models.schema_artifact import SchemaArtifact
from app.api.services.component_registry_service import ComponentRegistryService
from app.api.services.document_definition_service import DocumentDefinitionService


logger = logging.getLogger(__name__)


# =============================================================================
# CANONICAL COMPONENT SPECIFICATIONS - ADR-034
# =============================================================================

OPEN_QUESTION_V1_COMPONENT = {
    "component_id": "component:OpenQuestionV1:1.0.0",
    "schema_id": "schema:OpenQuestionV1",
    "generation_guidance": {
        "bullets": [
            "Provide a stable question id (e.g., Q-001).",
            "Write a clear, specific question that requires human decision.",
            "Set blocking=true only if work cannot proceed responsibly without an answer.",
            "Explain why_it_matters in one sentence.",
            "Include options only if there are meaningful discrete choices.",
            "If options exist, default_response SHOULD match one option.",
            "Use notes for assumptions, context, or follow-up suggestions."
        ]
    },
    "view_bindings": {
        "web": {
            "fragment_id": "fragment:OpenQuestionV1:web:1.0.0"
        }
    },
    "status": "accepted"
}


# ADR-034-EXP: Container block component
OPEN_QUESTIONS_BLOCK_V1_COMPONENT = {
    "component_id": "component:OpenQuestionsBlockV1:1.0.0",
    "schema_id": "schema:OpenQuestionsBlockV1",
    "generation_guidance": {
        "bullets": [
            "This is a container block for rendering; generation guidance is minimal.",
            "Item-level guidance is provided by OpenQuestionV1."
        ]
    },
    "view_bindings": {
        "web": {
            "fragment_id": "fragment:OpenQuestionsBlockV1:web:1.0.0"
        }
    },
    "status": "accepted"
}


# =============================================================================
# ADR-034-EXP3: Story Components
# =============================================================================

STORY_V1_COMPONENT = {
    "component_id": "component:StoryV1:1.0.0",
    "schema_id": "schema:StoryV1",
    "generation_guidance": {
        "bullets": [
            "Produce a story with a stable id and explicit epic_id reference.",
            "Keep title short and specific; description should be actionable and user-facing.",
            "Set status to one of: draft, ready, in_progress, blocked, done (default draft).",
            "Acceptance criteria must be concrete, testable statements.",
            "Include dependencies only when explicitly known; otherwise omit or leave empty.",
            "Avoid implementation detail (no class names, endpoints, tech stack) unless explicitly provided.",
            "Keep notes brief; do not introduce new scope silently.",
            "epic_id must match parent epic id when nested under an epic."
        ]
    },
    "view_bindings": {
        "web": {
            "fragment_id": "fragment:StoryV1:web:1.0.0"
        }
    },
    "status": "accepted"
}


STORIES_BLOCK_V1_COMPONENT = {
    "component_id": "component:StoriesBlockV1:1.0.0",
    "schema_id": "schema:StoriesBlockV1",
    "generation_guidance": {
        "bullets": [
            "This is a render-only container. Do not generate new stories here.",
            "Render items in the order provided; do not reorder unless explicitly instructed."
        ]
    },
    "view_bindings": {
        "web": {
            "fragment_id": "fragment:StoriesBlockV1:web:1.0.0"
        }
    },
    "status": "accepted"
}


# =============================================================================
# DOCUMENT DEFINITIONS - ADR-034
# =============================================================================

EPIC_BACKLOG_DOCDEF = {
    "document_def_id": "docdef:EpicBacklog:1.0.0",
    "document_schema_id": None,  # nullable for MVP; schema bundle from components
    "prompt_header": {
        "role": "You are a Business Analyst creating an Epic Backlog for a software project.",
        "constraints": [
            "Output valid JSON matching the document schema.",
            "Be specific and actionable.",
            "Do not invent requirements not supported by inputs.",
            "Each epic must have at least one open question if unknowns exist."
        ]
    },
    "sections": [
        {
            "section_id": "epic_open_questions",
            "title": "Open Questions",
            "description": "Questions requiring human decision before implementation",
            "order": 10,
            "component_id": "component:OpenQuestionV1:1.0.0",
            "shape": "nested_list",
            "source_pointer": "/open_questions",
            "repeat_over": "/epics",
            "context": {
                "epic_id": "/id",
                "epic_title": "/title"
            }
        }
    ],
    "status": "accepted"
}


# ADR-034-EXP: EpicBacklog v1.1.0 with container rendering
EPIC_BACKLOG_V1_1_DOCDEF = {
    "document_def_id": "docdef:EpicBacklog:1.1.0",
    "document_schema_id": None,
    "prompt_header": {
        "role": "You are a Business Analyst creating an Epic Backlog for a software project.",
        "constraints": [
            "Output valid JSON matching the document schema.",
            "Be specific and actionable.",
            "Do not invent requirements not supported by inputs.",
            "Each epic must have at least one open question if unknowns exist."
        ]
    },
    "sections": [
        {
            "section_id": "epic_open_questions",
            "title": "Open Questions",
            "description": "Questions requiring human decision before implementation",
            "order": 10,
            "component_id": "component:OpenQuestionsBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/open_questions",
            "repeat_over": "/epics",
            "context": {
                "epic_id": "/id",
                "epic_title": "/title"
            }
        }
    ],
    "status": "accepted"
}


# ADR-034-EXP2 S1: Root-level container test docdef
ROOT_QUESTIONS_TEST_DOCDEF = {
    "document_def_id": "docdef:RootQuestionsTest:1.0.0",
    "document_schema_id": None,
    "prompt_header": {
        "role": "Test document for root-level questions.",
        "constraints": []
    },
    "sections": [
        {
            "section_id": "root_questions",
            "title": "Open Questions",
            "order": 10,
            "component_id": "component:OpenQuestionsBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/open_questions"
            # No repeat_over - root level
        }
    ],
    "status": "accepted"
}


# ADR-034-EXP2 S3: Deep nesting probe docdef
# NOTE: This is a probe to test limitations of current repeat_over semantics.
# Payload structure: /epics/*/capabilities/*/open_questions
# Question: Can we collect open_questions from all capabilities across all epics?
#
# Current hypothesis: NO - repeat_over only supports one level of iteration.
# We can iterate /epics OR /epics/0/capabilities, but not /epics/*/capabilities.
DEEP_NESTING_TEST_DOCDEF = {
    "document_def_id": "docdef:DeepNestingTest:1.0.0",
    "document_schema_id": None,
    "prompt_header": {
        "role": "Test document for deep nesting probe.",
        "constraints": []
    },
    "sections": [
        {
            "section_id": "deep_questions",
            "title": "Capability Questions",
            "order": 10,
            "component_id": "component:OpenQuestionsBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/open_questions",
            # Probe attempt: What happens if we try to reach nested capabilities?
            # This uses /capabilities as source_pointer, expecting open_questions inside each
            "repeat_over": "/epics",
            "context": {
                "epic_id": "/id",
                "epic_title": "/title"
            }
        }
    ],
    "status": "accepted"
}


# =============================================================================
# ADR-034-DISCOVERY: Generic List and Summary Components
# =============================================================================

STRING_LIST_BLOCK_V1_COMPONENT = {
    "component_id": "component:StringListBlockV1:1.0.0",
    "schema_id": "schema:StringListBlockV1",
    "generation_guidance": {
        "bullets": [
            "This is a render-only container. Items come from upstream data.",
            "Use context.title to set the section heading.",
            "Style defaults to bullet; can be numbered or check."
        ]
    },
    "view_bindings": {
        "web": {
            "fragment_id": "fragment:StringListBlockV1:web:1.0.0"
        }
    },
    "status": "accepted"
}


SUMMARY_BLOCK_V1_COMPONENT = {
    "component_id": "component:SummaryBlockV1:1.0.0",
    "schema_id": "schema:SummaryBlockV1",
    "generation_guidance": {
        "bullets": [
            "Produce a summary with clear, concise prose for each field.",
            "problem_understanding: What is the core problem being solved?",
            "architectural_intent: What high-level approach is being taken?",
            "scope_pressure_points: Where might scope expand or contract?",
            "Keep each field under 2-3 sentences for readability."
        ]
    },
    "view_bindings": {
        "web": {
            "fragment_id": "fragment:SummaryBlockV1:web:1.0.0"
        }
    },
    "status": "accepted"
}


RISKS_BLOCK_V1_COMPONENT = {
    "component_id": "component:RisksBlockV1:1.0.0",
    "schema_id": "schema:RisksBlockV1",
    "generation_guidance": {
        "bullets": [
            "This is a render-only container. Do not generate new risks here.",
            "Render items in the order provided.",
            "Each item should conform to RiskV1 schema."
        ]
    },
    "view_bindings": {
        "web": {
            "fragment_id": "fragment:RisksBlockV1:web:1.0.0"
        }
    },
    "status": "accepted"
}


PARAGRAPH_BLOCK_V1_COMPONENT = {
    "component_id": "component:ParagraphBlockV1:1.0.0",
    "schema_id": "schema:ParagraphBlockV1",
    "generation_guidance": {
        "bullets": [
            "Produce clear, concise prose for the section content.",
            "Keep paragraphs focused on a single topic or theme.",
            "Avoid bullet points within paragraph blocks.",
            "Use context.title to understand the section purpose."
        ]
    },
    "view_bindings": {
        "web": {
            "fragment_id": "fragment:ParagraphBlockV1:web:1.0.0"
        }
    },
    "status": "accepted"
}


INDICATOR_BLOCK_V1_COMPONENT = {
    "component_id": "component:IndicatorBlockV1:1.0.0",
    "schema_id": "schema:IndicatorBlockV1",
    "generation_guidance": {
        "bullets": [
            "This is a render-only block for derived values.",
            "Do not generate indicator values directly.",
            "Values come from frozen derivation rules."
        ]
    },
    "view_bindings": {
        "web": {
            "fragment_id": "fragment:IndicatorBlockV1:web:1.0.0"
        }
    },
    "status": "accepted"
}


EPIC_SUMMARY_BLOCK_V1_COMPONENT = {
    "component_id": "component:EpicSummaryBlockV1:1.0.0",
    "schema_id": "schema:EpicSummaryBlockV1",
    "generation_guidance": {
        "bullets": [
            "This is a render-only container for backlog views.",
            "Contains 3-5 fields: title, intent, phase, risk_level, detail_ref.",
            "Intentionally lossy - optimized for scanning.",
            "risk_level is derived, not generated.",
            "detail_ref links to EpicDetailView."
        ]
    },
    "view_bindings": {
        "web": {
            "fragment_id": "fragment:EpicSummaryBlockV1:web:1.0.0"
        }
    },
    "status": "accepted"
}


DEPENDENCIES_BLOCK_V1_COMPONENT = {
    "component_id": "component:DependenciesBlockV1:1.0.0",
    "schema_id": "schema:DependenciesBlockV1",
    "generation_guidance": {
        "bullets": [
            "This is a render-only container for dependency lists.",
            "Each item should conform to DependencyV1 schema.",
            "Include depends_on_id, reason, and blocking flag.",
            "Mark blocking=true for hard dependencies."
        ]
    },
    "view_bindings": {
        "web": {
            "fragment_id": "fragment:DependenciesBlockV1:web:1.0.0"
        }
    },
    "status": "accepted"
}


# ADR-034-EXP3: Story backlog test docdef
STORY_BACKLOG_TEST_DOCDEF = {
    "document_def_id": "docdef:StoryBacklogTest:1.0.0",
    "document_schema_id": None,
    "prompt_header": {
        "role": "Test document for story backlog rendering.",
        "constraints": []
    },
    "sections": [
        {
            "section_id": "epic_stories",
            "title": "Stories",
            "order": 10,
            "component_id": "component:StoriesBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/stories",
            "repeat_over": "/epics",
            "context": {
                "epic_id": "/id",
                "epic_title": "/title"
            }
        }
    ],
    "status": "accepted"
}


# =============================================================================
# ADR-034-DISCOVERY: Project Discovery DocDef
# =============================================================================

PROJECT_DISCOVERY_DOCDEF = {
    "document_def_id": "docdef:ProjectDiscovery:1.0.0",
    "document_schema_id": None,  # Will link to project_discovery schema eventually
    "prompt_header": {
        "role": "You are producing a Project Discovery document.",
        "constraints": [
            "Do not propose solutions, architectures, plans, or implementation approaches.",
            "Do not infer intent beyond what is supported by inputs.",
            "All assumptions must be stated explicitly and labeled as assumptions.",
            "Unknowns must remain visible, not filled in.",
        ]
    },
    "sections": [
        # Summary (single block)
        {
            "section_id": "summary",
            "title": "Preliminary Summary",
            "order": 10,
            "component_id": "component:SummaryBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/preliminary_summary",
        },
        # Constraints (string list container)
        {
            "section_id": "constraints",
            "title": "Known Constraints",
            "order": 20,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/known_constraints",
            "context": {"title": "Known Constraints"},
        },
        # Assumptions (string list container)
        {
            "section_id": "assumptions",
            "title": "Assumptions",
            "order": 30,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/assumptions",
            "context": {"title": "Assumptions"},
        },
        # Risks (typed container)
        {
            "section_id": "risks",
            "title": "Identified Risks",
            "order": 40,
            "component_id": "component:RisksBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/identified_risks",
            "context": {"title": "Identified Risks"},
        },
        # Guardrails (string list container)
        {
            "section_id": "guardrails",
            "title": "MVP Guardrails",
            "order": 50,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/mvp_guardrails",
            "context": {"title": "MVP Guardrails", "style": "check"},
        },
        # Recommendations (string list container)
        {
            "section_id": "recommendations",
            "title": "Recommendations for PM",
            "order": 60,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/recommendations_for_pm",
            "context": {"title": "Recommendations for PM"},
        },
    ],
    "status": "accepted"
}


# =============================================================================
# ADR-034-EPIC-SUMMARY: Epic Summary View DocDef
# =============================================================================

EPIC_SUMMARY_VIEW_DOCDEF = {
    "document_def_id": "docdef:EpicSummaryView:1.0.0",
    "document_schema_id": None,  # Projection over CanonicalEpicV1
    "prompt_header": {
        "role": "You are producing an Epic Summary for backlog scanning.",
        "constraints": [
            "Keep summary intentionally brief.",
            "3-5 fields maximum.",
            "Optimized for scanning, not understanding.",
        ]
    },
    "sections": [
        # Title (simple string)
        {
            "section_id": "title",
            "title": "Title",
            "order": 10,
            "component_id": "component:ParagraphBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/title",
            "context": {"title": ""},
        },
        # Intent (one paragraph - use vision)
        {
            "section_id": "intent",
            "title": "Intent",
            "order": 20,
            "component_id": "component:ParagraphBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/vision",
            "context": {"title": "Intent"},
        },
        # Phase (MVP indicator)
        {
            "section_id": "phase",
            "title": "Phase",
            "order": 30,
            "component_id": "component:ParagraphBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/phase",
            "context": {"title": "Phase"},
        },
        # Risk Level (derived from risks array)
        {
            "section_id": "risk_level",
            "title": "Risk Level",
            "order": 40,
            "component_id": "component:IndicatorBlockV1:1.0.0",
            "shape": "single",
            "derived_from": {"function": "risk_level", "source": "/risks"},
            "context": {"title": "Risk"},
        },
    ],
    "status": "accepted"
}


# =============================================================================
# ADR-034-EPIC-DETAIL: Epic Detail DocDef
# =============================================================================

EPIC_DETAIL_VIEW_DOCDEF = {
    "document_def_id": "docdef:EpicDetailView:1.0.0",
    "document_schema_id": None,  # Will link to CanonicalEpicV1 schema
    "prompt_header": {
        "role": "You are producing an Epic Detail document.",
        "constraints": [
            "Focus on the single epic being defined.",
            "Be specific about scope boundaries.",
            "All risks must include likelihood and impact.",
            "Open questions should identify blocking vs non-blocking.",
        ]
    },
    "sections": [
        # Vision (paragraph)
        {
            "section_id": "vision",
            "title": "Vision",
            "order": 10,
            "component_id": "component:ParagraphBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/vision",
            "context": {"title": "Vision"},
        },
        # Problem (paragraph)
        {
            "section_id": "problem",
            "title": "Problem/Opportunity",
            "order": 20,
            "component_id": "component:ParagraphBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/problem",
            "context": {"title": "Problem/Opportunity"},
        },
        # Business Goals (string list)
        {
            "section_id": "business_goals",
            "title": "Business Goals",
            "order": 30,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/business_goals",
            "context": {"title": "Business Goals"},
        },
        # In Scope (string list with checks)
        {
            "section_id": "in_scope",
            "title": "In Scope",
            "order": 40,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/in_scope",
            "context": {"title": "In Scope", "style": "check"},
        },
        # Out of Scope (string list)
        {
            "section_id": "out_of_scope",
            "title": "Out of Scope",
            "order": 50,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/out_of_scope",
            "context": {"title": "Out of Scope"},
        },
        # Requirements (numbered list)
        {
            "section_id": "requirements",
            "title": "Requirements",
            "order": 60,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/requirements",
            "context": {"title": "Requirements", "style": "numbered"},
        },
        # Acceptance Criteria (checkmarks)
        {
            "section_id": "acceptance_criteria",
            "title": "Acceptance Criteria",
            "order": 70,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/acceptance_criteria",
            "context": {"title": "Acceptance Criteria", "style": "check"},
        },
        # Risks (typed container)
        {
            "section_id": "risks",
            "title": "Risks",
            "order": 80,
            "component_id": "component:RisksBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/risks",
            "context": {"title": "Risks"},
        },
        # Open Questions (typed container)
        {
            "section_id": "open_questions",
            "title": "Open Questions",
            "order": 90,
            "component_id": "component:OpenQuestionsBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/open_questions",
            "context": {"title": "Open Questions"},
        },
        # Dependencies (typed container)
        {
            "section_id": "dependencies",
            "title": "Dependencies",
            "order": 100,
            "component_id": "component:DependenciesBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/dependencies",
            "context": {"title": "Dependencies"},
        },
    ],
    "status": "accepted"
}


# =============================================================================
# ADR-034-EPIC-BACKLOG: Epic Backlog View DocDef
# =============================================================================

EPIC_BACKLOG_VIEW_DOCDEF = {
    "document_def_id": "docdef:EpicBacklogView:1.0.0",
    "document_schema_id": None,  # Projection over epic backlog data
    "prompt_header": {
        "role": "You are producing an Epic Backlog for project navigation.",
        "constraints": [
            "Each epic renders as a summary card.",
            "Details are referenced, not embedded.",
            "Optimized for scanning multiple epics.",
        ]
    },
    "sections": [
        {
            "section_id": "epic_summaries",
            "title": "Epics",
            "order": 10,
            "component_id": "component:EpicSummaryBlockV1:1.0.0",
            "shape": "container",
            "repeat_over": "/epics",
            "source_pointer": "/",
            "exclude_fields": ["risks", "open_questions", "requirements", "acceptance_criteria"],
            "context": {
                "epic_id": "/epic_id",
                "epic_title": "/title"
            },
            "derived_fields": [
                {"field": "risk_level", "function": "risk_level", "source": "/risks"},
            ],
            "detail_ref_template": {
                "document_type": "EpicDetailView",
                "params": {"epic_id": "/epic_id"}
            },
        },
    ],
    "status": "accepted"
}


# Lists for seeding
INITIAL_COMPONENT_ARTIFACTS: List[Dict[str, Any]] = [
    OPEN_QUESTION_V1_COMPONENT,
    OPEN_QUESTIONS_BLOCK_V1_COMPONENT,
    STORY_V1_COMPONENT,
    STORIES_BLOCK_V1_COMPONENT,
    STRING_LIST_BLOCK_V1_COMPONENT,
    SUMMARY_BLOCK_V1_COMPONENT,
    RISKS_BLOCK_V1_COMPONENT,
    PARAGRAPH_BLOCK_V1_COMPONENT,
    INDICATOR_BLOCK_V1_COMPONENT,
    EPIC_SUMMARY_BLOCK_V1_COMPONENT,
    DEPENDENCIES_BLOCK_V1_COMPONENT,
]

INITIAL_DOCUMENT_DEFINITIONS: List[Dict[str, Any]] = [
    EPIC_BACKLOG_DOCDEF,
    EPIC_BACKLOG_V1_1_DOCDEF,
    ROOT_QUESTIONS_TEST_DOCDEF,
    DEEP_NESTING_TEST_DOCDEF,
    STORY_BACKLOG_TEST_DOCDEF,
    PROJECT_DISCOVERY_DOCDEF,
    EPIC_SUMMARY_VIEW_DOCDEF,
    EPIC_DETAIL_VIEW_DOCDEF,
    EPIC_BACKLOG_VIEW_DOCDEF,
]


async def _get_schema_artifact_id(db: AsyncSession, schema_id: str) -> str:
    """
    Look up schema_artifact UUID by schema_id.
    
    Args:
        db: Database session
        schema_id: Schema ID (e.g., "OpenQuestionV1" or "schema:OpenQuestionV1")
        
    Returns:
        UUID of the schema artifact
        
    Raises:
        ValueError: If schema not found
    """
    # Strip 'schema:' prefix if present
    lookup_id = schema_id
    if schema_id.startswith("schema:"):
        lookup_id = schema_id[7:]
    
    stmt = select(SchemaArtifact).where(SchemaArtifact.schema_id == lookup_id)
    result = await db.execute(stmt)
    schema = result.scalar_one_or_none()
    
    if not schema:
        raise ValueError(f"Schema artifact not found: {schema_id}")
    
    return schema.id


async def seed_component_artifacts(db: AsyncSession) -> int:
    """
    Seed the component_artifacts table with canonical components.
    
    Skips any artifacts that already exist (by component_id).
    
    Args:
        db: Database session
        
    Returns:
        Number of artifacts created
    """
    service = ComponentRegistryService(db)
    created_count = 0
    
    for artifact_data in INITIAL_COMPONENT_ARTIFACTS:
        component_id = artifact_data["component_id"]
        
        # Check if already exists
        existing = await service.get(component_id)
        
        if existing:
            logger.info(f"Component '{component_id}' already exists, skipping")
            continue
        
        # Look up schema artifact UUID
        schema_artifact_id = await _get_schema_artifact_id(db, artifact_data["schema_id"])
        
        # Create the component
        await service.create(
            component_id=component_id,
            schema_artifact_id=schema_artifact_id,
            schema_id=artifact_data["schema_id"],
            generation_guidance=artifact_data["generation_guidance"],
            view_bindings=artifact_data["view_bindings"],
            status=artifact_data["status"],
            created_by="seed",
        )
        
        created_count += 1
        logger.info(f"Created component: {component_id} ({artifact_data['status']})")
    
    await db.commit()
    logger.info(f"Seeded {created_count} component artifacts")
    return created_count


async def seed_document_definitions(db: AsyncSession) -> int:
    """
    Seed the document_definitions table with document definitions.
    
    Skips any definitions that already exist (by document_def_id).
    
    Args:
        db: Database session
        
    Returns:
        Number of definitions created
    """
    service = DocumentDefinitionService(db)
    created_count = 0
    
    for docdef_data in INITIAL_DOCUMENT_DEFINITIONS:
        document_def_id = docdef_data["document_def_id"]
        
        # Check if already exists
        existing = await service.get(document_def_id)
        
        if existing:
            logger.info(f"Document definition '{document_def_id}' already exists, skipping")
            continue
        
        # Create the document definition
        await service.create(
            document_def_id=document_def_id,
            prompt_header=docdef_data["prompt_header"],
            sections=docdef_data["sections"],
            document_schema_id=docdef_data.get("document_schema_id"),
            status=docdef_data["status"],
            created_by="seed",
        )
        
        created_count += 1
        logger.info(f"Created document definition: {document_def_id} ({docdef_data['status']})")
    
    await db.commit()
    logger.info(f"Seeded {created_count} document definitions")
    return created_count


async def seed_all(db: AsyncSession) -> Dict[str, int]:
    """
    Seed all component artifacts and document definitions.
    
    Args:
        db: Database session
        
    Returns:
        Dict with counts: {"components": n, "docdefs": n}
    """
    components = await seed_component_artifacts(db)
    docdefs = await seed_document_definitions(db)
    
    return {
        "components": components,
        "docdefs": docdefs,
    }


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()  # Load .env before importing database
    from app.core.database import async_session_factory
    
    async def main():
        async with async_session_factory() as db:
            counts = await seed_all(db)
            print(f"Seeded {counts['components']} components, {counts['docdefs']} document definitions")
    
    asyncio.run(main())




































