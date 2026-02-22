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
            "Render-only container. Do not generate this block; items are provided upstream."
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


# STORIES_BLOCK_V1_COMPONENT moved to later in file (consolidated)


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
            "Render-only container. Do not generate items; items are provided upstream."
        ]
    },
    "view_bindings": {
        "web": {
            "fragment_id": "fragment:StringListBlockV1:web:1.0.0"
        }
    },
    "status": "accepted"
}


UNKNOWNS_BLOCK_V1_COMPONENT = {
    "component_id": "component:UnknownsBlockV1:1.0.0",
    "schema_id": "schema:UnknownsBlockV1",
    "generation_guidance": {
        "bullets": [
            "Render-only container for unknowns display.",
            "Each item should have question, why_it_matters, and impact_if_unresolved."
        ]
    },
    "view_bindings": {
        "web": {
            "fragment_id": "fragment:UnknownsBlockV1:web:1.0.0"
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
            "Render-only container. Do not generate this block; items are provided upstream."
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


STORY_SUMMARY_BLOCK_V1_COMPONENT = {
    "component_id": "component:StorySummaryBlockV1:1.0.0",
    "schema_id": "schema:StorySummaryBlockV1",
    "generation_guidance": {
        "bullets": [
            "This is a render-only item for story backlog views.",
            "Required: story_id, title, intent (1-2 sentences), detail_ref.",
            "Optional: phase (mvp|later), risk_level (low|medium|high).",
            "Intentionally lossy - excludes acceptance_criteria, scope, dependencies, questions, notes.",
            "risk_level is derived upstream, omit if no risks.",
            "detail_ref must link to StoryDetailView."
        ]
    },
    "view_bindings": {
        "web": {
            "fragment_id": "fragment:StorySummaryBlockV1:web:1.0.0"
        }
    },
    "status": "accepted"
}


STORIES_BLOCK_V1_COMPONENT = {
    "component_id": "component:StoriesBlockV1:1.0.0",
    "schema_id": "schema:StoriesBlockV1",
    "generation_guidance": {
        "bullets": [
            "Render-only container. Do not generate this block; items are provided upstream."
        ]
    },
    "view_bindings": {
        "web": {
            "fragment_id": "fragment:StoriesBlockV1:web:1.0.0"
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
        # Summary (single block) - SIDECAR: 2-3 lines
        {
            "section_id": "summary",
            "title": "Preliminary Summary",
            "order": 10,
            "component_id": "component:SummaryBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/preliminary_summary",
            "viewer_tab": "overview",
        },
        # Unknowns - SIDECAR: expandable, primary
        {
            "section_id": "unknowns",
            "title": "Unknowns",
            "order": 15,
            "component_id": "component:UnknownsBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/unknowns",
            "context": {"title": "Unknowns"},
            "viewer_tab": "overview",
        },
        # Constraints (string list container) - SIDECAR: binding list
        {
            "section_id": "constraints",
            "title": "Known Constraints",
            "order": 20,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/known_constraints",
            "context": {"title": "Known Constraints"},
            "viewer_tab": "overview",
        },
        # Assumptions (string list container) - SIDECAR: if any (unvalidated)
        {
            "section_id": "assumptions",
            "title": "Assumptions (Unvalidated)",
            "order": 30,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/assumptions",
            "context": {"title": "Assumptions (Unvalidated)"},
            "viewer_tab": "overview",
        },
        # Risks (typed container) - SIDECAR: Top 3 only
        {
            "section_id": "risks",
            "title": "Top Risks",
            "order": 40,
            "component_id": "component:RisksBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/identified_risks",
            "context": {"title": "Top Risks"},
            "viewer_tab": "overview",
            "sidecar_max_items": 3,
        },
        # Stakeholder Questions (questions container) - FULL VIEW
        {
            "section_id": "stakeholder_questions",
            "title": "Stakeholder Questions",
            "order": 45,
            "component_id": "component:OpenQuestionsBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/stakeholder_questions",
            "context": {"title": "Stakeholder Questions"},
            "viewer_tab": "overview",
        },
        # Early Decision Points (questions container) - FULL VIEW
        {
            "section_id": "early_decision_points",
            "title": "Early Decision Points",
            "order": 47,
            "component_id": "component:OpenQuestionsBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/early_decision_points",
            "context": {"title": "Early Decision Points"},
            "viewer_tab": "overview",
        },
        # Guardrails (string list container) - FULL VIEW ONLY
        {
            "section_id": "guardrails",
            "title": "MVP Guardrails",
            "order": 50,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/mvp_guardrails",
            "context": {"title": "MVP Guardrails", "style": "check"},
            "viewer_tab": "details",
        },
        # Recommendations (string list container) - FULL VIEW ONLY
        {
            "section_id": "recommendations",
            "title": "Recommendations for PM",
            "order": 60,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/recommendations_for_pm",
            "context": {"title": "Recommendations for PM"},
            "viewer_tab": "details",
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
# ADR-034: Implementation Plan (Primary) View DocDef
# =============================================================================

IMPLEMENTATION_PLAN_PRIMARY_VIEW_DOCDEF = {
    "document_def_id": "docdef:ImplementationPlanPrimaryView:1.0.0",
    "document_schema_id": None,  # Projection over implementation plan data
    "prompt_header": {
        "role": "You are producing a preliminary Implementation Plan.",
        "constraints": [
            "Show project context and plan summary first.",
            "Epic candidates are informational - they inform architecture.",
            "Include recommendations for technical architecture.",
        ]
    },
    "sections": [
        # Plan Summary - Overall Intent & MVP Definition
        {
            "section_id": "plan_summary",
            "title": "Plan Summary",
            "order": 10,
            "component_id": "component:SummaryBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/epic_set_summary",
            "viewer_tab": "overview",
        },
        # Key Constraints - top 5 in sidecar
        {
            "section_id": "key_constraints",
            "title": "Key Constraints",
            "order": 20,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/epic_set_summary/key_constraints",
            "viewer_tab": "overview",
            "sidecar_max_items": 5,
        },
        # Out of Scope
        {
            "section_id": "out_of_scope",
            "title": "Out of Scope",
            "order": 30,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/epic_set_summary/out_of_scope",
            "viewer_tab": "overview",
        },
        # Epic Candidate Cards - informational, no detail view
        {
            "section_id": "epic_candidates",
            "title": "Epic Candidates",
            "order": 40,
            "component_id": "component:EpicSummaryBlockV1:1.0.0",
            "shape": "container",
            "repeat_over": "/epic_candidates",
            "source_pointer": "/",
            "exclude_fields": ["risks", "open_questions", "requirements", "acceptance_criteria", "related_discovery_items"],
            "context": {
                "candidate_id": "/candidate_id",
                "candidate_name": "/name"
            },
            "viewer_tab": "details",
            # Note: No detail_ref_template - candidates are informational only
        },
        # Risks Overview - full view only
        {
            "section_id": "risks_overview",
            "title": "Risks Overview",
            "order": 50,
            "component_id": "component:RisksBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/risks_overview",
            "viewer_tab": "details",
        },
        # Recommendations for Architecture - full view only
        {
            "section_id": "architecture_recommendations",
            "title": "Recommendations for Architecture",
            "order": 60,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/recommendations_for_architecture",
            "viewer_tab": "details",
        },
    ],
    "status": "accepted"
}

# Backward compatibility alias
EPIC_BACKLOG_VIEW_DOCDEF = IMPLEMENTATION_PLAN_PRIMARY_VIEW_DOCDEF


# =============================================================================
# ADR-034: Implementation Plan (Final) View DocDef
# =============================================================================

IMPLEMENTATION_PLAN_VIEW_DOCDEF = {
    "document_def_id": "docdef:ImplementationPlanView:1.0.0",
    "document_schema_id": None,
    "prompt_header": {
        "role": "You are producing a Final Implementation Plan.",
        "constraints": [
            "Show plan summary and key constraints first.",
            "Epics are committed, architecture-informed work packages.",
            "Include candidate reconciliation for audit traceability.",
            "Risk summary aggregates across all epics.",
        ]
    },
    "sections": [
        # Plan Summary
        {
            "section_id": "plan_summary",
            "title": "Plan Summary",
            "order": 10,
            "component_id": "component:SummaryBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/plan_summary",
            "viewer_tab": "overview",
        },
        # Key Constraints
        {
            "section_id": "key_constraints",
            "title": "Key Constraints",
            "order": 20,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/plan_summary/key_constraints",
            "viewer_tab": "overview",
            "sidecar_max_items": 5,
        },
        # Cross-Cutting Concerns
        {
            "section_id": "cross_cutting_concerns",
            "title": "Cross-Cutting Concerns",
            "order": 30,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/cross_cutting_concerns",
            "viewer_tab": "overview",
        },
        # Committed Epics
        {
            "section_id": "epics",
            "title": "Committed Epics",
            "order": 40,
            "component_id": "component:EpicSummaryBlockV1:1.0.0",
            "shape": "container",
            "repeat_over": "/epics",
            "source_pointer": "/",
            "exclude_fields": ["risks", "open_questions", "architecture_notes", "source_candidate_ids", "transformation_notes"],
            "context": {
                "epic_id": "/epic_id",
                "epic_name": "/name"
            },
            "viewer_tab": "details",
        },
        # Risk Summary
        {
            "section_id": "risk_summary",
            "title": "Risk Summary",
            "order": 50,
            "component_id": "component:RisksBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/risk_summary",
            "viewer_tab": "details",
        },
    ],
    "status": "accepted"
}


# =============================================================================
# ADR-034: Epic Architecture View DocDef
# =============================================================================

EPIC_ARCHITECTURE_VIEW_DOCDEF = {
    "document_def_id": "docdef:EpicArchitectureView:1.0.0",
    "document_schema_id": None,  # Projection over architecture data
    "prompt_header": {
        "role": "You are producing an Epic Architecture document.",
        "constraints": [
            "Focus on technical structure for one epic.",
            "Text-first, typed where it matters.",
            "No diagrams required.",
        ]
    },
    "sections": [
        # Architecture Intent
        {
            "section_id": "architecture_intent",
            "title": "Architecture Intent",
            "order": 10,
            "component_id": "component:ParagraphBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/architecture_intent",
            "context": {"title": "Architecture Intent"},
        },
        # Systems/Services Touched
        {
            "section_id": "systems_touched",
            "title": "Systems/Services Touched",
            "order": 20,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/systems_touched",
            "context": {"title": "Systems/Services Touched"},
        },
        # External Integrations
        {
            "section_id": "external_integrations",
            "title": "External Integrations",
            "order": 30,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/external_integrations",
            "context": {"title": "External Integrations"},
        },
        # Key Interfaces/APIs
        {
            "section_id": "key_interfaces",
            "title": "Key Interfaces/APIs",
            "order": 40,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/key_interfaces",
            "context": {"title": "Key Interfaces/APIs"},
        },
        # Data/Events
        {
            "section_id": "data_events",
            "title": "Data/Events",
            "order": 50,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/data_events",
            "context": {"title": "Data/Events"},
        },
        # Dependencies
        {
            "section_id": "dependencies",
            "title": "Dependencies",
            "order": 60,
            "component_id": "component:DependenciesBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/dependencies",
            "context": {"title": "Dependencies"},
        },
        # Architectural Constraints
        {
            "section_id": "architectural_constraints",
            "title": "Architectural Constraints",
            "order": 70,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/architectural_constraints",
            "context": {"title": "Architectural Constraints"},
        },
        # Architecture Decisions
        {
            "section_id": "architecture_decisions",
            "title": "Architecture Decisions",
            "order": 80,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/architecture_decisions",
            "context": {"title": "Architecture Decisions", "style": "numbered"},
        },
        # Architecture Open Questions
        {
            "section_id": "architecture_open_questions",
            "title": "Architecture Open Questions",
            "order": 90,
            "component_id": "component:OpenQuestionsBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/architecture_open_questions",
            "context": {"title": "Architecture Open Questions"},
        },
        # Observability/SLO Notes
        {
            "section_id": "observability_notes",
            "title": "Observability/SLO Notes",
            "order": 100,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/observability_notes",
            "context": {"title": "Observability/SLO Notes"},
        },
    ],
    "status": "accepted"
}


# =============================================================================
# ADR-034: Architectural Summary View DocDef
# =============================================================================

ARCHITECTURAL_SUMMARY_VIEW_DOCDEF = {
    "document_def_id": "docdef:ArchitecturalSummaryView:1.0.0",
    "document_schema_id": None,
    "prompt_header": {
        "role": "You are producing an Architecture document view.",
        "constraints": [
            "Full architecture detail with overview and details tabs.",
            "Overview shows summary and key decisions.",
            "Details shows components, interfaces, workflows, etc.",
        ]
    },
    "sections": [
        # =====================================================================
        # OVERVIEW TAB
        # =====================================================================
        # Architecture Summary
        {
            "section_id": "architecture_summary",
            "title": "Architecture Summary",
            "order": 10,
            "component_id": "component:SummaryBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/architecture_summary",
            "viewer_tab": "overview",
        },
        # Key Decisions
        {
            "section_id": "key_decisions",
            "title": "Key Decisions",
            "order": 20,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/architecture_summary/key_decisions",
            "viewer_tab": "overview",
        },
        # MVP Scope Notes
        {
            "section_id": "mvp_scope_notes",
            "title": "MVP Scope Notes",
            "order": 30,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/architecture_summary/mvp_scope_notes",
            "viewer_tab": "overview",
        },
        # Problem Statement (first in overview)
        {
            "section_id": "problem_statement",
            "title": "Problem Statement",
            "order": 5,
            "component_id": "component:ParagraphBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/context/problem_statement",
            "viewer_tab": "overview",
        },
        # =====================================================================
        # DETAILS TAB
        # =====================================================================
        # Context - Constraints
        {
            "section_id": "constraints",
            "title": "Constraints",
            "order": 100,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/context/constraints",
            "viewer_tab": "details",
        },
        # Context - Assumptions
        {
            "section_id": "assumptions",
            "title": "Assumptions",
            "order": 110,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/context/assumptions",
            "viewer_tab": "details",
        },
        # Context - Non Goals
        {
            "section_id": "non_goals",
            "title": "Non-Goals",
            "order": 120,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/context/non_goals",
            "viewer_tab": "details",
        },
        # Components
        {
            "section_id": "components",
            "title": "Components",
            "order": 200,
            "component_id": "component:ArchComponentBlockV1:1.0.0",
            "shape": "container",
            "repeat_over": "/components",
            "source_pointer": "/",
            "viewer_tab": "implementation",
        },
        # Data Model
        {
            "section_id": "data_model",
            "title": "Data Model",
            "order": 210,
            "component_id": "component:DataModelBlockV1:1.0.0",
            "shape": "container",
            "repeat_over": "/data_model",
            "source_pointer": "/",
            "viewer_tab": "implementation",
        },
        # Interfaces
        {
            "section_id": "interfaces",
            "title": "Interfaces",
            "order": 220,
            "component_id": "component:InterfaceBlockV1:1.0.0",
            "shape": "container",
            "repeat_over": "/interfaces",
            "source_pointer": "/",
            "viewer_tab": "implementation",
        },
        # Workflows (V2: graph-based with React Flow rendering)
        {
            "section_id": "workflows",
            "title": "Workflows",
            "order": 230,
            "component_id": "component:WorkflowBlockV2:1.0.0",
            "shape": "container",
            "repeat_over": "/workflows",
            "source_pointer": "/",
            "viewer_tab": "details",
        },
        # Quality Attributes
        {
            "section_id": "quality_attributes",
            "title": "Quality Attributes",
            "order": 240,
            "component_id": "component:QualityAttributeBlockV1:1.0.0",
            "shape": "container",
            "repeat_over": "/quality_attributes",
            "source_pointer": "/",
            "viewer_tab": "details",
        },
        # Security - Data Classification
        {
            "section_id": "security_data_classification",
            "title": "Data Classification",
            "order": 300,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/security_considerations/data_classification",
            "viewer_tab": "details",
        },
        # Security - Controls
        {
            "section_id": "security_controls",
            "title": "Security Controls",
            "order": 310,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/security_considerations/controls",
            "viewer_tab": "details",
        },
        # Observability - Logging
        {
            "section_id": "observability_logging",
            "title": "Logging",
            "order": 400,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/observability/logging",
            "viewer_tab": "details",
        },
        # Observability - Metrics
        {
            "section_id": "observability_metrics",
            "title": "Metrics",
            "order": 410,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/observability/metrics",
            "viewer_tab": "details",
        },
        # Risks
        {
            "section_id": "risks",
            "title": "Risks",
            "order": 500,
            "component_id": "component:RisksBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/risks",
            "viewer_tab": "details",
        },
        # Open Questions
        {
            "section_id": "open_questions",
            "title": "Open Questions",
            "order": 510,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/open_questions",
            "viewer_tab": "details",
        },
    ],
    "status": "accepted"
}


# =============================================================================
# ADR-034: Story Detail View DocDef
# =============================================================================

STORY_DETAIL_VIEW_DOCDEF = {
    "document_def_id": "docdef:StoryDetailView:1.0.0",
    "document_schema_id": None,  # Projection over StoryV1
    "prompt_header": {
        "role": "You are producing a Story Detail document.",
        "constraints": [
            "Single-story comprehensive view.",
            "Optimized for understanding and execution.",
            "Do not duplicate epic-level fields (vision, roadmap, business goals).",
            "Acceptance criteria must be a list, not prose.",
        ]
    },
    "sections": [
        # Story Intent (carries epic back-reference)
        {
            "section_id": "story_intent",
            "title": "Story Intent",
            "order": 10,
            "component_id": "component:ParagraphBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/intent",
            "context": {"title": "Story Intent"},
            "detail_ref_template": {
                "document_type": "EpicDetailView",
                "params": {"epic_id": "/epic_id"}
            },
        },
        # User Value / Outcome
        {
            "section_id": "user_value",
            "title": "User Value",
            "order": 20,
            "component_id": "component:ParagraphBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/user_value",
            "context": {"title": "User Value"},
        },
        # Acceptance Criteria (must be list)
        {
            "section_id": "acceptance_criteria",
            "title": "Acceptance Criteria",
            "order": 30,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/acceptance_criteria",
            "context": {"title": "Acceptance Criteria", "style": "check"},
        },
        # In Scope
        {
            "section_id": "in_scope",
            "title": "In Scope",
            "order": 40,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/in_scope",
            "context": {"title": "In Scope", "style": "check"},
        },
        # Out of Scope
        {
            "section_id": "out_of_scope",
            "title": "Out of Scope",
            "order": 50,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/out_of_scope",
            "context": {"title": "Out of Scope"},
        },
        # Dependencies
        {
            "section_id": "dependencies",
            "title": "Dependencies",
            "order": 60,
            "component_id": "component:DependenciesBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/dependencies",
            "context": {"title": "Dependencies"},
        },
        # Open Questions
        {
            "section_id": "open_questions",
            "title": "Open Questions",
            "order": 70,
            "component_id": "component:OpenQuestionsBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/open_questions",
            "context": {"title": "Open Questions"},
        },
        # Notes for Implementation
        {
            "section_id": "implementation_notes",
            "title": "Notes for Implementation",
            "order": 80,
            "component_id": "component:StringListBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/implementation_notes",
            "context": {"title": "Notes for Implementation"},
        },
        # Risks (omitted if empty - builder behavior)
        {
            "section_id": "risks",
            "title": "Risks",
            "order": 90,
            "component_id": "component:RisksBlockV1:1.0.0",
            "shape": "container",
            "source_pointer": "/risks",
            "context": {"title": "Risks"},
        },
    ],
    "status": "accepted"
}


# =============================================================================
# ADR-034: Story Summary View DocDef
# =============================================================================

STORY_SUMMARY_VIEW_DOCDEF = {
    "document_def_id": "docdef:StorySummaryView:1.0.0",
    "document_schema_id": None,  # Lightweight projection over StoryV1
    "prompt_header": {
        "role": "You are producing a Story Summary for scanning.",
        "constraints": [
            "3 fields maximum.",
            "Intentionally lossy.",
            "Optimized for scanning, not understanding.",
            "Must NOT include: acceptance_criteria, scope, dependencies, questions, notes.",
        ]
    },
    "sections": [
        # Story Intent (carries detail_ref to StoryDetailView)
        {
            "section_id": "story_intent",
            "title": "Story Intent",
            "order": 10,
            "component_id": "component:ParagraphBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/intent",
            "context": {"title": ""},
            "detail_ref_template": {
                "document_type": "StoryDetailView",
                "params": {"story_id": "/story_id"}
            },
        },
        # Phase indicator
        {
            "section_id": "phase",
            "title": "Phase",
            "order": 20,
            "component_id": "component:IndicatorBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/phase",
            "context": {"title": "Phase"},
        },
        # Risk Level (derived, omit when no risks)
        {
            "section_id": "risk_level",
            "title": "Risk Level",
            "order": 30,
            "component_id": "component:IndicatorBlockV1:1.0.0",
            "shape": "single",
            "derived_from": {
                "function": "risk_level",
                "source": "/risks",
                "omit_when_source_empty": True
            },
            "context": {"title": "Risk"},
        },
    ],
    "status": "accepted"
}


# =============================================================================
# ADR-034: Story Backlog View DocDef
# =============================================================================

# Lists for seeding
# =============================================================================
# ADR-034: Architecture Component Block
# =============================================================================

ARCH_COMPONENT_BLOCK_V1_COMPONENT = {
    "component_id": "component:ArchComponentBlockV1:1.0.0",
    "schema_id": "schema:ArchComponentBlockV1",
    "generation_guidance": {"bullets": ["Render-only container for architecture component display.", "Component data is provided upstream from architecture generation."]},
    "view_bindings": {"web": {"fragment_id": "fragment:ArchComponentBlockV1:web:1.0.0"}},
    "status": "accepted",
}


# =============================================================================
# ADR-034: Quality Attribute Block
# =============================================================================

QUALITY_ATTRIBUTE_BLOCK_V1_COMPONENT = {
    "component_id": "component:QualityAttributeBlockV1:1.0.0",
    "schema_id": "schema:QualityAttributeBlockV1",
    "generation_guidance": {"bullets": ["Render-only container for quality attribute display.", "Attribute data is provided upstream from architecture generation."]},
    "view_bindings": {"web": {"fragment_id": "fragment:QualityAttributeBlockV1:web:1.0.0"}},
    "status": "accepted",
}


# =============================================================================
# ADR-034: Interface Block
# =============================================================================

INTERFACE_BLOCK_V1_COMPONENT = {
    "component_id": "component:InterfaceBlockV1:1.0.0",
    "schema_id": "schema:InterfaceBlockV1",
    "generation_guidance": {"bullets": ["Render-only container for API interface display.", "Interface data is provided upstream from architecture generation."]},
    "view_bindings": {"web": {"fragment_id": "fragment:InterfaceBlockV1:web:1.0.0"}},
    "status": "accepted",
}


# =============================================================================
# ADR-034: Workflow Block
# =============================================================================

WORKFLOW_BLOCK_V1_COMPONENT = {
    "component_id": "component:WorkflowBlockV1:1.0.0",
    "schema_id": "schema:WorkflowBlockV1",
    "generation_guidance": {"bullets": ["Render-only container for workflow display.", "Workflow data is provided upstream from architecture generation."]},
    "view_bindings": {"web": {"fragment_id": "fragment:WorkflowBlockV1:web:1.0.0"}},
    "status": "accepted",
}


# =============================================================================
# ADR-034: Workflow Block V2 (Graph-based)
# =============================================================================

WORKFLOW_BLOCK_V2_COMPONENT = {
    "component_id": "component:WorkflowBlockV2:1.0.0",
    "schema_id": "schema:WorkflowBlockV2",
    "generation_guidance": {
        "bullets": [
            "Graph-based workflow with nodes[] and edges[].",
            "Each node has node_id, type (action|gate|escalation|parallel_fork|parallel_join|start|end), and label.",
            "Gate nodes MUST have 2+ outgoing edges (pass/fail paths).",
            "Error handling paths must be explicit edges with type=error.",
            "Retry loops use edges with type=retry.",
            "V1 steps[] data is auto-converted to linear graph at render time.",
        ]
    },
    "view_bindings": {"web": {"fragment_id": "fragment:WorkflowBlockV2:web:1.0.0"}},
    "status": "accepted",
}


# =============================================================================
# ADR-034: Data Model Block
# =============================================================================

DATA_MODEL_BLOCK_V1_COMPONENT = {
    "component_id": "component:DataModelBlockV1:1.0.0",
    "schema_id": "schema:DataModelBlockV1",
    "generation_guidance": {"bullets": ["Render-only container for data model display.", "Data model is provided upstream from architecture generation."]},
    "view_bindings": {"web": {"fragment_id": "fragment:DataModelBlockV1:web:1.0.0"}},
    "status": "accepted",
}

# =============================================================================
# WS-STORY-BACKLOG-VIEW: Epic Stories Card Component
# =============================================================================

EPIC_STORIES_CARD_BLOCK_V1_COMPONENT = {
    "component_id": "component:EpicStoriesCardBlockV1:1.0.0",
    "schema_id": "schema:EpicStoriesCardBlockV1",
    "generation_guidance": {"bullets": ["Render-only container for epic card with story summaries.", "Stories are summary-level only (no AC, no dependencies).", "Empty stories array omits story section entirely."]},
    "view_bindings": {"web": {"fragment_id": "fragment:EpicStoriesCardBlockV1:web:1.0.0"}},
    "status": "accepted",
}


# =============================================================================
# WS-STORY-BACKLOG-VIEW: Story Backlog View DocDef
# =============================================================================

STORY_BACKLOG_VIEW_DOCDEF = {
    "document_def_id": "docdef:StoryBacklogView:1.0.0",
    "document_schema_id": None,
    "prompt_header": {
        "role": "You are producing a Story Backlog view.",
        "constraints": [
            "Epic cards with nested story summaries.",
            "Stories are summary-level only.",
            "One card per epic.",
        ]
    },
    "sections": [
        # Epic Story Cards - one card per epic with nested stories
        {
            "section_id": "epic_stories",
            "title": None,  # No section header - cards ARE the content
            "order": 10,
            "component_id": "component:EpicStoriesCardBlockV1:1.0.0",
            "shape": "container",
            "repeat_over": "/epics",
            "source_pointer": "/",

        },
    ],
    "status": "accepted"
}


# =============================================================================
# ADR-039: Concierge Intake Compound Components
# =============================================================================

INTAKE_SUMMARY_BLOCK_V1_COMPONENT = {
    "component_id": "component:IntakeSummaryBlockV1:1.0.0",
    "schema_id": "schema:IntakeSummaryBlockV1",
    "generation_guidance": {
        "bullets": [
            "Render-only block for project summary display.",
            "Contains description and user statement."
        ]
    },
    "view_bindings": {
        "web": {"fragment_id": "fragment:IntakeSummaryBlockV1:web:1.0.0"}
    },
    "status": "accepted"
}

INTAKE_OUTCOME_BLOCK_V1_COMPONENT = {
    "component_id": "component:IntakeOutcomeBlockV1:1.0.0",
    "schema_id": "schema:IntakeOutcomeBlockV1",
    "generation_guidance": {
        "bullets": [
            "Render-only block for intake outcome display.",
            "Contains status badge, rationale, and next action."
        ]
    },
    "view_bindings": {
        "web": {"fragment_id": "fragment:IntakeOutcomeBlockV1:web:1.0.0"}
    },
    "status": "accepted"
}

INTAKE_CONSTRAINTS_BLOCK_V1_COMPONENT = {
    "component_id": "component:IntakeConstraintsBlockV1:1.0.0",
    "schema_id": "schema:IntakeConstraintsBlockV1",
    "generation_guidance": {
        "bullets": [
            "Render-only block for constraints display.",
            "Shows explicit constraints followed by inferred constraints."
        ]
    },
    "view_bindings": {
        "web": {"fragment_id": "fragment:IntakeConstraintsBlockV1:web:1.0.0"}
    },
    "status": "accepted"
}

INTAKE_OPEN_GAPS_BLOCK_V1_COMPONENT = {
    "component_id": "component:IntakeOpenGapsBlockV1:1.0.0",
    "schema_id": "schema:IntakeOpenGapsBlockV1",
    "generation_guidance": {
        "bullets": [
            "Render-only block for open gaps display.",
            "Shows questions, missing context, and assumptions."
        ]
    },
    "view_bindings": {
        "web": {"fragment_id": "fragment:IntakeOpenGapsBlockV1:web:1.0.0"}
    },
    "status": "accepted"
}

INTAKE_PROJECT_TYPE_BLOCK_V1_COMPONENT = {
    "component_id": "component:IntakeProjectTypeBlockV1:1.0.0",
    "schema_id": "schema:IntakeProjectTypeBlockV1",
    "generation_guidance": {
        "bullets": [
            "Render-only block for project type display.",
            "Shows category badge with confidence and rationale."
        ]
    },
    "view_bindings": {
        "web": {"fragment_id": "fragment:IntakeProjectTypeBlockV1:web:1.0.0"}
    },
    "status": "accepted"
}


# =============================================================================
# ADR-039: Concierge Intake View DocDef
# =============================================================================

CONCIERGE_INTAKE_VIEW_DOCDEF = {
    "document_def_id": "docdef:ConciergeIntakeView:1.0.0",
    "document_schema_id": None,  # Links to ConciergeIntakeDocumentV1 schema
    "prompt_header": {
        "role": "You are producing a Concierge Intake document view.",
        "constraints": [
            "Display captured intent and conversation summary prominently.",
            "Show constraints and known unknowns as lists.",
            "Show gate outcome with routing rationale.",
        ]
    },
    "sections": [
        # Project Summary (description + user statement)
        {
            "section_id": "project_summary",
            "title": "Project Summary",
            "order": 10,
            "component_id": "component:IntakeSummaryBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/summary",
            "viewer_tab": "overview",
        },
        # Project Type (category + confidence + rationale)
        {
            "section_id": "project_type",
            "title": "Project Type",
            "order": 20,
            "component_id": "component:IntakeProjectTypeBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/project_type",
            "viewer_tab": "overview",
        },
        # Constraints (explicit + inferred)
        {
            "section_id": "constraints",
            "title": "Constraints",
            "order": 30,
            "component_id": "component:IntakeConstraintsBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/constraints",
            "viewer_tab": "details",
        },
        # Open Gaps (questions + missing context + assumptions)
        {
            "section_id": "open_gaps",
            "title": "Open Gaps",
            "order": 40,
            "component_id": "component:IntakeOpenGapsBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/open_gaps",
            "viewer_tab": "details",
        },
        # Intake Outcome (status + rationale + next action)
        {
            "section_id": "intake_outcome",
            "title": "Intake Outcome",
            "order": 50,
            "component_id": "component:IntakeOutcomeBlockV1:1.0.0",
            "shape": "single",
            "source_pointer": "/outcome",
            "viewer_tab": "overview",
        },
    ],
    "status": "accepted"
}

INITIAL_COMPONENT_ARTIFACTS: List[Dict[str, Any]] = [
    OPEN_QUESTION_V1_COMPONENT,
    OPEN_QUESTIONS_BLOCK_V1_COMPONENT,
    STORY_V1_COMPONENT,
    STRING_LIST_BLOCK_V1_COMPONENT,
    UNKNOWNS_BLOCK_V1_COMPONENT,
    SUMMARY_BLOCK_V1_COMPONENT,
    RISKS_BLOCK_V1_COMPONENT,
    PARAGRAPH_BLOCK_V1_COMPONENT,
    INDICATOR_BLOCK_V1_COMPONENT,
    EPIC_SUMMARY_BLOCK_V1_COMPONENT,
    DEPENDENCIES_BLOCK_V1_COMPONENT,
    STORY_SUMMARY_BLOCK_V1_COMPONENT,
    STORIES_BLOCK_V1_COMPONENT,
    ARCH_COMPONENT_BLOCK_V1_COMPONENT,
    QUALITY_ATTRIBUTE_BLOCK_V1_COMPONENT,
    INTERFACE_BLOCK_V1_COMPONENT,
    WORKFLOW_BLOCK_V1_COMPONENT,
    WORKFLOW_BLOCK_V2_COMPONENT,
    DATA_MODEL_BLOCK_V1_COMPONENT,
    EPIC_STORIES_CARD_BLOCK_V1_COMPONENT,
    # ADR-039: Concierge Intake compound components
    INTAKE_SUMMARY_BLOCK_V1_COMPONENT,
    INTAKE_OUTCOME_BLOCK_V1_COMPONENT,
    INTAKE_CONSTRAINTS_BLOCK_V1_COMPONENT,
    INTAKE_OPEN_GAPS_BLOCK_V1_COMPONENT,
    INTAKE_PROJECT_TYPE_BLOCK_V1_COMPONENT,
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
    IMPLEMENTATION_PLAN_PRIMARY_VIEW_DOCDEF,
    IMPLEMENTATION_PLAN_VIEW_DOCDEF,
    EPIC_BACKLOG_VIEW_DOCDEF,  # Backward compatibility alias
    EPIC_ARCHITECTURE_VIEW_DOCDEF,
    ARCHITECTURAL_SUMMARY_VIEW_DOCDEF,
    STORY_DETAIL_VIEW_DOCDEF,
    STORY_SUMMARY_VIEW_DOCDEF,
    STORY_BACKLOG_VIEW_DOCDEF,
    CONCIERGE_INTAKE_VIEW_DOCDEF,
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






































































