"""
Seed data for schema_artifacts table.

Per ADR-031: Canonical types are seeded as governed artifacts.

Usage:
    python -m app.domain.registry.seed_schema_artifacts
    
Or call seed_schema_artifacts(db) from your migration/startup.
"""

from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.api.services.schema_registry_service import SchemaRegistryService

logger = logging.getLogger(__name__)


# =============================================================================
# CANONICAL TYPES - Governed schema artifacts per ADR-031
# =============================================================================

OPEN_QUESTION_V1_SCHEMA = {
    "$id": "schema:OpenQuestionV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "title": "Open Question",
    "description": "A structured open question with optional decision options.",
    "required": ["id", "text", "blocking", "why_it_matters"],
    "properties": {
        "id": {
            "type": "string",
            "minLength": 1,
            "description": "Unique identifier for the question"
        },
        "text": {
            "type": "string",
            "minLength": 2,
            "description": "The question text"
        },
        "blocking": {
            "type": "boolean",
            "default": False,
            "description": "Whether this question blocks progress"
        },
        "why_it_matters": {
            "type": "string",
            "minLength": 2,
            "description": "Explanation of why this question is important"
        },
        "priority": {
            "type": "string",
            "enum": ["must", "should", "could"],
            "default": "should",
            "description": "Priority level for human guidance"
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
            "description": "Optional categorization tags"
        },
        "options": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "label"],
                "properties": {
                    "id": {
                        "type": "string",
                        "minLength": 1,
                        "description": "Option identifier"
                    },
                    "label": {
                        "type": "string",
                        "minLength": 1,
                        "description": "Short option label"
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed option description"
                    }
                },
                "additionalProperties": False
            },
            "default": [],
            "description": "Possible answer options"
        },
        "default_response": {
            "type": "object",
            "properties": {
                "option_id": {
                    "type": "string",
                    "description": "ID of selected option"
                },
                "free_text": {
                    "type": "string",
                    "description": "Free-text response"
                }
            },
            "additionalProperties": False,
            "description": "Default or recommended response"
        },
        "notes": {
            "type": "string",
            "description": "Additional context or notes"
        }
    },
    "additionalProperties": False
}

RISK_V1_SCHEMA = {
    "$id": "schema:RiskV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "title": "Risk",
    "description": "A structured risk with impact and affected items.",
    "required": ["id", "description", "impact"],
    "properties": {
        "id": {
            "type": "string",
            "minLength": 1,
            "description": "Unique identifier for the risk"
        },
        "description": {
            "type": "string",
            "minLength": 2,
            "description": "Description of the risk"
        },
        "impact": {
            "type": "string",
            "minLength": 2,
            "description": "Impact if the risk materializes"
        },
        "likelihood": {
            "type": "string",
            "enum": ["low", "medium", "high"],
            "description": "Likelihood of the risk occurring"
        },
        "severity": {
            "type": "string",
            "enum": ["low", "medium", "high", "critical"],
            "description": "Severity if the risk occurs"
        },
        "affected_items": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
            "description": "IDs of affected epics, stories, or components"
        },
        "mitigation": {
            "type": "string",
            "description": "Proposed mitigation strategy"
        },
        "notes": {
            "type": "string",
            "description": "Additional context"
        }
    },
    "additionalProperties": False
}

SCOPE_LIST_V1_SCHEMA = {
    "$id": "schema:ScopeListV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "title": "Scope List",
    "description": "A list of in-scope or out-of-scope items.",
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of scope items"
        },
        "notes": {
            "type": "string",
            "description": "Additional context about scope"
        }
    },
    "additionalProperties": False
}

DEPENDENCY_V1_SCHEMA = {
    "$id": "schema:DependencyV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "title": "Dependency",
    "description": "A dependency reference with reason.",
    "required": ["depends_on_id", "reason"],
    "properties": {
        "depends_on_id": {
            "type": "string",
            "minLength": 1,
            "description": "ID of the item this depends on"
        },
        "depends_on_type": {
            "type": "string",
            "enum": ["epic", "story", "component", "external"],
            "description": "Type of the dependency target"
        },
        "reason": {
            "type": "string",
            "minLength": 2,
            "description": "Why this dependency exists"
        },
        "blocking": {
            "type": "boolean",
            "default": True,
            "description": "Whether this is a blocking dependency"
        },
        "notes": {
            "type": "string",
            "description": "Additional context"
        }
    },
    "additionalProperties": False
}


# =============================================================================
# RENDER MODEL SCHEMAS - ADR-033 Experience Contract Standard
# =============================================================================

RENDER_MODEL_V1_SCHEMA = {
    "$id": "schema:RenderModelV1",
    "title": "Render Model V1",
    "type": "object",
    "required": [
        "render_model_version",
        "document_id",
        "document_type",
        "schema_id",
        "schema_bundle_sha256",
        "title",
        "sections"
    ],
    "properties": {
        "render_model_version": {
            "type": "string",
            "const": "1.0"
        },
        "document_id": {"type": "string", "minLength": 1},
        "document_type": {"type": "string", "minLength": 1},
        "schema_id": {
            "type": "string",
            "pattern": "^schema:[A-Za-z0-9._-]+$"
        },
        "schema_bundle_sha256": {
            "type": "string",
            "pattern": "^sha256:[a-f0-9]{64}$"
        },
        "title": {"type": "string", "minLength": 1},
        "subtitle": {"type": "string"},
        "sections": {
            "type": "array",
            "items": {"$ref": "schema:RenderSectionV1"}
        },
        "actions": {
            "type": "array",
            "items": {"$ref": "schema:RenderActionV1"}
        }
    },
    "additionalProperties": False
}

RENDER_SECTION_V1_SCHEMA = {
    "$id": "schema:RenderSectionV1",
    "title": "Render Section V1",
    "type": "object",
    "required": ["id", "title", "order", "blocks"],
    "properties": {
        "id": {"type": "string", "minLength": 1},
        "title": {"type": "string", "minLength": 1},
        "order": {"type": "integer", "minimum": 0},
        "description": {"type": "string"},
        "blocks": {
            "type": "array",
            "items": {"$ref": "schema:RenderBlockV1"}
        }
    },
    "additionalProperties": False
}

RENDER_BLOCK_V1_SCHEMA = {
    "$id": "schema:RenderBlockV1",
    "title": "Render Block V1",
    "type": "object",
    "required": ["type", "data"],
    "properties": {
        "type": {
            "type": "string",
            "pattern": "^schema:[A-Za-z0-9._-]+$"
        },
        "data": {"type": "object"},
        "key": {"type": "string"}
    },
    "additionalProperties": False
}

RENDER_ACTION_V1_SCHEMA = {
    "$id": "schema:RenderActionV1",
    "title": "Render Action V1",
    "type": "object",
    "required": ["id", "label", "method", "href"],
    "properties": {
        "id": {"type": "string", "minLength": 1},
        "label": {"type": "string", "minLength": 1},
        "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
        "href": {"type": "string", "minLength": 1}
    },
    "additionalProperties": False
}



# =============================================================================
# ADR-034 CANONICAL COMPONENT & DOCUMENT DEFINITION SCHEMAS
# =============================================================================

CANONICAL_COMPONENT_V1_SCHEMA = {
    "$id": "schema:CanonicalComponentV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "title": "Canonical Component Specification",
    "description": "Defines a reusable component with schema, prompt guidance, and view bindings.",
    "required": ["component_id", "schema_id", "generation_guidance", "view_bindings"],
    "properties": {
        "component_id": {
            "type": "string",
            "pattern": "^component:[A-Za-z0-9._-]+:[0-9]+\\.[0-9]+\\.[0-9]+$",
            "description": "Canonical component ID with semver (e.g., component:OpenQuestionV1:1.0.0)"
        },
        "schema_id": {
            "type": "string",
            "pattern": "^schema:[A-Za-z0-9._-]+$",
            "description": "Reference to canonical schema (e.g., schema:OpenQuestionV1)"
        },
        "generation_guidance": {
            "type": "object",
            "required": ["bullets"],
            "properties": {
                "bullets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "description": "Prompt generation bullets for LLM"
                }
            },
            "additionalProperties": False
        },
        "view_bindings": {
            "type": "object",
            "description": "Channel-specific fragment bindings",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "fragment_id": {
                        "type": "string",
                        "description": "Canonical fragment ID for this channel"
                    }
                },
                "additionalProperties": False
            }
        }
    },
    "additionalProperties": False
}

DOCUMENT_DEFINITION_V2_SCHEMA = {
    "$id": "schema:DocumentDefinitionV2",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "title": "Document Definition V2",
    "description": "Composes canonical components into a document structure.",
    "required": ["document_def_id", "prompt_header", "sections"],
    "properties": {
        "document_def_id": {
            "type": "string",
            "pattern": "^docdef:[A-Za-z0-9._-]+:[0-9]+\\.[0-9]+\\.[0-9]+$",
            "description": "Canonical document definition ID with semver"
        },
        "document_schema_id": {
            "type": "string",
            "pattern": "^schema:[A-Za-z0-9._-]+$",
            "description": "Optional reference to document-level schema"
        },
        "prompt_header": {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "description": "Role context for LLM"
                },
                "constraints": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Generation constraints"
                }
            },
            "additionalProperties": False
        },
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["section_id", "title", "order", "component_id", "shape", "source_pointer"],
                "properties": {
                    "section_id": {
                        "type": "string",
                        "minLength": 1,
                        "description": "Unique section identifier"
                    },
                    "title": {
                        "type": "string",
                        "minLength": 1,
                        "description": "Section title"
                    },
                    "description": {
                        "type": "string",
                        "description": "Section description"
                    },
                    "order": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Section ordering"
                    },
                    "component_id": {
                        "type": "string",
                        "pattern": "^component:[A-Za-z0-9._-]+:[0-9]+\\.[0-9]+\\.[0-9]+$",
                        "description": "Reference to canonical component"
                    },
                    "shape": {
                        "type": "string",
                        "enum": ["single", "list", "nested_list"],
                        "description": "How component data is structured"
                    },
                    "source_pointer": {
                        "type": "string",
                        "pattern": "^/.*$",
                        "description": "JSON pointer to data source"
                    },
                    "repeat_over": {
                        "type": "string",
                        "pattern": "^/.*$",
                        "description": "JSON pointer for nested_list parent iteration"
                    },
                    "context": {
                        "type": "object",
                        "description": "Context mappings from parent to child",
                        "additionalProperties": {
                            "type": "string",
                            "pattern": "^/.*$"
                        }
                    }
                },
                "additionalProperties": False
            },
            "description": "Ordered list of document sections"
        }
    },
    "additionalProperties": False
}


OPEN_QUESTIONS_BLOCK_V1_SCHEMA = {
    "$id": "schema:OpenQuestionsBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "title": "Open Questions Block",
    "description": "Container block for a list of open questions within a section context.",
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "items": {"$ref": "schema:OpenQuestionV1"},
            "description": "List of open questions"
        },
        "total_count": {
            "type": "integer",
            "minimum": 0,
            "description": "Total count of questions (derived, non-authoritative)"
        },
        "blocking_count": {
            "type": "integer",
            "minimum": 0,
            "description": "Count of blocking questions (derived, non-authoritative)"
        }
    },
    "additionalProperties": False
}

# =============================================================================
# ADR-034-EXP3: Story Schemas
# =============================================================================

STORY_V1_SCHEMA = {
    "$id": "schema:StoryV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Story",
    "type": "object",
    "required": ["id", "epic_id", "title", "description", "status"],
    "properties": {
        "id": {
            "type": "string",
            "minLength": 1,
            "description": "Stable story identifier"
        },
        "epic_id": {
            "type": "string",
            "minLength": 1,
            "description": "Parent epic identifier (reference, must match parent when nested)"
        },
        "title": {
            "type": "string",
            "minLength": 2,
            "description": "Short story title"
        },
        "description": {
            "type": "string",
            "minLength": 2,
            "description": "Story description"
        },
        "status": {
            "type": "string",
            "enum": ["draft", "ready", "in_progress", "blocked", "done"],
            "default": "draft",
            "description": "Workflow status"
        },
        "acceptance_criteria": {
            "type": "array",
            "items": {"type": "string", "minLength": 2},
            "default": [],
            "description": "User-validated acceptance criteria"
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
            "description": "Optional categorization tags"
        },
        "notes": {
            "type": "string",
            "description": "Additional context / notes"
        }
    },
    "additionalProperties": False,
    "description": "A story linked to an epic via epic_id (flatten-first canonical reference)."
}


# =============================================================================
# ADR-034-DISCOVERY: Generic List and Summary Components
# =============================================================================

STRING_LIST_BLOCK_V1_SCHEMA = {
    "$id": "schema:StringListBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "String List Block",
    "type": "object",
    "required": ["items"],
    "properties": {
        "title": {
            "type": "string",
            "description": "Optional title for the list section"
        },
        "items": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of string items"
        },
        "style": {
            "type": "string",
            "enum": ["bullet", "numbered", "check"],
            "default": "bullet",
            "description": "Rendering style for the list"
        }
    },
    "additionalProperties": False,
    "description": "Generic container block for rendering simple string lists."
}


UNKNOWNS_BLOCK_V1_SCHEMA = {
    "$id": "schema:UnknownsBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Unknowns Block",
    "type": "object",
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["question"],
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The unknown question or gap"
                    },
                    "why_it_matters": {
                        "type": "string",
                        "description": "Why this unknown is important"
                    },
                    "impact_if_unresolved": {
                        "type": "string",
                        "description": "Impact if this unknown is not resolved"
                    }
                },
                "additionalProperties": False
            },
            "description": "List of unknown items"
        }
    },
    "additionalProperties": False,
    "description": "Container block for rendering unknowns with question, why_it_matters, and impact_if_unresolved."
}


SUMMARY_BLOCK_V1_SCHEMA = {
    "$id": "schema:SummaryBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Summary Block",
    "type": "object",
    "properties": {
        "problem_understanding": {
            "type": "string",
            "description": "Understanding of the problem space"
        },
        "architectural_intent": {
            "type": "string",
            "description": "High-level architectural direction"
        },
        "scope_pressure_points": {
            "type": "string",
            "description": "Areas where scope may expand or contract"
        }
    },
    "additionalProperties": False,
    "description": "Multi-field summary block for document headers."
}


RISKS_BLOCK_V1_SCHEMA = {
    "$id": "schema:RisksBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Risks Block",
    "type": "object",
    "required": ["items"],
    "properties": {
        "title": {
            "type": "string",
            "description": "Optional title override"
        },
        "items": {
            "type": "array",
            "items": {"$ref": "schema:RiskV1"},
            "description": "Risks to render in this block"
        }
    },
    "additionalProperties": False,
    "description": "Container block for rendering risk lists."
}


PARAGRAPH_BLOCK_V1_SCHEMA = {
    "$id": "schema:ParagraphBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Paragraph Block",
    "type": "object",
    "properties": {
        "content": {
            "type": "string",
            "description": "The paragraph text content"
        },
        "value": {
            "type": "string",
            "description": "Alternative field name for content (builder compatibility)"
        },
        "detail_ref": {
            "$ref": "schema:DocumentRefV1",
            "description": "Optional reference to detail view"
        }
    },
    "additionalProperties": False,
    "description": "Simple paragraph text block for narrative content."
}


INDICATOR_BLOCK_V1_SCHEMA = {
    "$id": "schema:IndicatorBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Indicator Block",
    "type": "object",
    "required": ["value"],
    "properties": {
        "value": {
            "type": "string",
            "description": "The indicator value (e.g., low, medium, high)"
        },
        "label": {
            "type": "string",
            "description": "Optional label for the indicator"
        }
    },
    "additionalProperties": False,
    "description": "Simple indicator block for derived values like risk level."
}


EPIC_SUMMARY_BLOCK_V1_SCHEMA = {
    "$id": "schema:EpicSummaryBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Epic Summary Block",
    "type": "object",
    "required": ["title"],
    "properties": {
        "epic_id": {
            "type": "string",
            "description": "Epic identifier"
        },
        "title": {
            "type": "string",
            "description": "Epic title"
        },
        "intent": {
            "type": "string",
            "description": "One-paragraph intent/vision"
        },
        "phase": {
            "type": "string",
            "description": "MVP phase indicator"
        },
        "risk_level": {
            "type": "string",
            "enum": ["low", "medium", "high"],
            "description": "Derived aggregate risk level"
        },
        "detail_ref": {
            "$ref": "schema:DocumentRefV1",
            "description": "Reference to EpicDetailView"
        }
    },
    "additionalProperties": False,
    "description": "Compact epic summary for backlog views. Intentionally lossy."
}


DEPENDENCIES_BLOCK_V1_SCHEMA = {
    "$id": "schema:DependenciesBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Dependencies Block",
    "type": "object",
    "required": ["items"],
    "properties": {
        "title": {
            "type": "string",
            "description": "Optional title override"
        },
        "items": {
            "type": "array",
            "items": {"$ref": "schema:DependencyV1"},
            "description": "Dependencies to render in this block"
        }
    },
    "additionalProperties": False,
    "description": "Container block for rendering dependency lists."
}


DOCUMENT_REF_V1_SCHEMA = {
    "$id": "schema:DocumentRefV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Document Reference",
    "type": "object",
    "required": ["document_type"],
    "properties": {
        "document_type": {
            "type": "string",
            "description": "Target docdef type (e.g., EpicDetailView, EpicArchitectureView)"
        },
        "params": {
            "type": "object",
            "additionalProperties": {"type": "string"},
            "description": "Parameters to resolve the target document (e.g., {epic_id: 'AUTH-100'})"
        }
    },
    "additionalProperties": False,
    "description": "Frozen reference to another document view. Used in summary views for detail links."
}


STORY_SUMMARY_BLOCK_V1_SCHEMA = {
    "$id": "schema:StorySummaryBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Story Summary Block",
    "type": "object",
    "required": ["story_id", "title", "intent", "detail_ref"],
    "properties": {
        "story_id": {
            "type": "string",
            "minLength": 1,
            "description": "Stable story identifier"
        },
        "title": {
            "type": "string",
            "minLength": 1,
            "description": "Story title for scanning"
        },
        "intent": {
            "type": "string",
            "minLength": 2,
            "description": "Short intent (1-2 sentences)"
        },
        "phase": {
            "type": "string",
            "enum": ["mvp", "later"],
            "description": "Story phase indicator"
        },
        "risk_level": {
            "type": "string",
            "enum": ["low", "medium", "high"],
            "description": "Derived risk level (optional, omit if no risks)"
        },
        "detail_ref": {
            "$ref": "schema:DocumentRefV1",
            "description": "Reference to StoryDetailView (required)"
        }
    },
    "additionalProperties": False,
    "description": "Lossy story summary for backlog views. Intentionally excludes acceptance_criteria, scope, dependencies, questions, notes."
}


STORIES_BLOCK_V1_SCHEMA = {
    "$id": "schema:StoriesBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Stories Block",
    "type": "object",
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "items": {"$ref": "schema:StorySummaryBlockV1"},
            "description": "Story summaries in this container"
        }
    },
    "additionalProperties": False,
    "description": "Container block for story summaries within an epic."
}


# =============================================================================
# ADR-034: Architecture Component Schema
# =============================================================================

ARCH_COMPONENT_BLOCK_V1_SCHEMA = {
    "$id": "schema:ArchComponentBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "title": "Architecture Component Block",
    "description": "An architecture component with layer, purpose, and dependencies.",
    "required": ["id", "name"],
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "layer": {"type": "string"},
        "purpose": {"type": "string"},
        "mvp_phase": {"type": "string"},
        "responsibilities": {"type": "array", "items": {"type": "string"}},
        "technology_choices": {"type": "array", "items": {"type": "string"}},
        "depends_on_components": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False
}


# =============================================================================
# ADR-034: Quality Attribute Schema
# =============================================================================

QUALITY_ATTRIBUTE_BLOCK_V1_SCHEMA = {
    "$id": "schema:QualityAttributeBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "title": "Quality Attribute Block",
    "description": "A quality attribute with target, rationale, and acceptance criteria.",
    "required": ["name"],
    "properties": {
        "name": {"type": "string"},
        "target": {"type": "string"},
        "rationale": {"type": "string"},
        "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False
}


# =============================================================================
# ADR-034: Interface Schema
# =============================================================================

INTERFACE_BLOCK_V1_SCHEMA = {
    "$id": "schema:InterfaceBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "title": "Interface Block",
    "description": "An API interface with endpoints.",
    "required": ["id", "name"],
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "type": {"type": "string"},
        "protocol": {"type": "string"},
        "description": {"type": "string"},
        "authentication": {"type": "string"},
        "authorization": {"type": "string"},
        "producer_components": {"type": "array", "items": {"type": "string"}},
        "consumer_components": {"type": "array", "items": {"type": "string"}},
        "endpoints": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "method": {"type": "string"},
                    "description": {"type": "string"},
                    "request_schema": {"type": "string"},
                    "response_schema": {"type": "string"},
                    "error_cases": {"type": "array", "items": {"type": "string"}},
                    "idempotency": {"type": "string"},
                }
            }
        },
    },
    "additionalProperties": False
}


# =============================================================================
# ADR-034: Workflow Schema
# =============================================================================

WORKFLOW_BLOCK_V1_SCHEMA = {
    "$id": "schema:WorkflowBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "title": "Workflow Block",
    "description": "A workflow with trigger and steps.",
    "required": ["id", "name"],
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "description": {"type": "string"},
        "trigger": {"type": "string"},
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "order": {"type": "integer"},
                    "actor": {"type": "string"},
                    "action": {"type": "string"},
                    "inputs": {"type": "array", "items": {"type": "string"}},
                    "outputs": {"type": "array", "items": {"type": "string"}},
                    "notes": {"type": "array", "items": {"type": "string"}},
                }
            }
        },
    },
    "additionalProperties": False
}


# =============================================================================
# ADR-034: Workflow V2 Schema (Graph-based)
# =============================================================================

WORKFLOW_BLOCK_V2_SCHEMA = {
    "$id": "schema:WorkflowBlockV2",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "title": "Workflow Block V2",
    "description": "A graph-based workflow with nodes and edges. Supports branching, gates, error paths, retry loops, and parallel rails. V1 steps[] auto-converted at render time.",
    "required": ["id", "name"],
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "description": {"type": "string"},
        "trigger": {"type": "string"},
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["node_id", "type", "label"],
                "properties": {
                    "node_id": {"type": "string", "minLength": 1},
                    "type": {
                        "type": "string",
                        "enum": ["action", "gate", "escalation", "parallel_fork", "parallel_join", "start", "end"]
                    },
                    "label": {"type": "string", "minLength": 1},
                    "actor": {"type": "string"},
                    "description": {"type": "string"},
                    "inputs": {"type": "array", "items": {"type": "string"}},
                    "outputs": {"type": "array", "items": {"type": "string"}},
                    "notes": {"type": "array", "items": {"type": "string"}},
                },
                "additionalProperties": False
            }
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["edge_id", "from_node_id", "to_node_id"],
                "properties": {
                    "edge_id": {"type": "string", "minLength": 1},
                    "from_node_id": {"type": "string", "minLength": 1},
                    "to_node_id": {"type": "string", "minLength": 1},
                    "label": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["normal", "error", "retry", "parallel"],
                        "default": "normal"
                    },
                },
                "additionalProperties": False
            }
        },
        "steps": {
            "type": "array",
            "description": "V1 compatibility: sequential steps. Auto-converted to nodes/edges at render time.",
            "items": {
                "type": "object",
                "properties": {
                    "order": {"type": "integer"},
                    "actor": {"type": "string"},
                    "action": {"type": "string"},
                    "inputs": {"type": "array", "items": {"type": "string"}},
                    "outputs": {"type": "array", "items": {"type": "string"}},
                    "notes": {"type": "array", "items": {"type": "string"}},
                }
            }
        },
    },
    "additionalProperties": False
}


# =============================================================================
# ADR-034: Data Model Schema
# =============================================================================

DATA_MODEL_BLOCK_V1_SCHEMA = {
    "$id": "schema:DataModelBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "title": "Data Model Block",
    "description": "A data model entity with fields.",
    "required": ["name"],
    "properties": {
        "name": {"type": "string"},
        "description": {"type": "string"},
        "primary_keys": {"type": "array", "items": {"type": "string"}},
        "fields": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "required": {"type": "boolean"},
                    "validation_rules": {"type": "array", "items": {"type": "string"}},
                    "notes": {"type": "array", "items": {"type": "string"}},
                }
            }
        },
        "relationships": {"type": "array"},
    },
    "additionalProperties": False
}

# =============================================================================
# ADR-025/ADR-039: Concierge Intake Document Schema
# =============================================================================

# =============================================================================
# ADR-039: Concierge Intake View Block Schemas (Compound)
# =============================================================================

INTAKE_SUMMARY_BLOCK_V1_SCHEMA = {
    "$id": "schema:IntakeSummaryBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Intake Summary Block",
    "description": "Compound block for intake project summary with description and user statement.",
    "type": "object",
    "properties": {
        "description": {
            "type": "string",
            "description": "Synthesized project description"
        },
        "user_statement": {
            "type": "string",
            "description": "Original user statement or conversation summary"
        }
    },
    "additionalProperties": False
}

INTAKE_OUTCOME_BLOCK_V1_SCHEMA = {
    "$id": "schema:IntakeOutcomeBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Intake Outcome Block",
    "description": "Compound block for intake gate outcome with status, rationale, and next action.",
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["qualified", "not_ready", "out_of_scope", "redirect"],
            "description": "Gate outcome status"
        },
        "rationale": {
            "type": "string",
            "description": "Explanation for the outcome"
        },
        "next_action": {
            "type": "string",
            "description": "Recommended next action if qualified"
        }
    },
    "additionalProperties": False
}

INTAKE_CONSTRAINTS_BLOCK_V1_SCHEMA = {
    "$id": "schema:IntakeConstraintsBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Intake Constraints Block",
    "description": "Compound block for explicit and inferred constraints.",
    "type": "object",
    "properties": {
        "explicit": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Explicitly stated constraints"
        },
        "inferred": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Inferred constraints"
        }
    },
    "additionalProperties": False
}

INTAKE_OPEN_GAPS_BLOCK_V1_SCHEMA = {
    "$id": "schema:IntakeOpenGapsBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Intake Open Gaps Block",
    "description": "Compound block for open questions, missing context, and assumptions.",
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Open questions requiring answers"
        },
        "missing_context": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Missing context or information"
        },
        "assumptions_made": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Assumptions made during intake"
        }
    },
    "additionalProperties": False
}

INTAKE_PROJECT_TYPE_BLOCK_V1_SCHEMA = {
    "$id": "schema:IntakeProjectTypeBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Intake Project Type Block",
    "description": "Compound block for project type with category, confidence, and rationale.",
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "description": "Project type category"
        },
        "confidence": {
            "type": "string",
            "description": "Confidence level in the categorization"
        },
        "rationale": {
            "type": "string",
            "description": "Explanation for the categorization"
        }
    },
    "additionalProperties": False
}


CONCIERGE_INTAKE_DOCUMENT_V1_SCHEMA = {
    "$id": "schema:ConciergeIntakeDocumentV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Concierge Intake Document",
    "description": "Structured intake document produced by the Concierge Document Interaction Workflow (ADR-039). Contains synthesized intent, constraints, and outcomes from the intake conversation.",
    "type": "object",
    "required": [
        "schema_version",
        "document_id",
        "captured_intent",
        "project_type",
        "gate_outcome",
        "conversation_summary"
    ],
    "properties": {
        "schema_version": {
            "type": "string",
            "const": "concierge_intake_document.v1",
            "description": "Schema version identifier"
        },
        "document_id": {
            "type": "string",
            "format": "uuid",
            "description": "Unique document identifier"
        },
        "workflow_execution_id": {
            "type": "string",
            "description": "Reference to the workflow execution that produced this document"
        },
        "captured_intent": {
            "type": "string",
            "minLength": 10,
            "maxLength": 2000,
            "description": "Synthesized description of what the user wants to accomplish"
        },
        "constraints": {
            "type": "array",
            "description": "Known constraints mentioned during intake conversation",
            "items": {
                "type": "string",
                "minLength": 1,
                "maxLength": 500
            },
            "default": []
        },
        "known_unknowns": {
            "type": "array",
            "description": "Identified gaps or uncertainties that need resolution in Discovery",
            "items": {
                "type": "string",
                "minLength": 1,
                "maxLength": 500
            },
            "default": []
        },
        "project_type": {
            "type": "string",
            "enum": ["greenfield", "enhancement", "migration", "integration", "replacement", "unknown"],
            "description": "Categorization of the project type based on intake conversation"
        },
        "gate_outcome": {
            "type": "string",
            "enum": ["qualified", "not_ready", "out_of_scope", "redirect"],
            "description": "Intake Gate outcome per ADR-025 governance boundary"
        },
        "conversation_summary": {
            "type": "string",
            "minLength": 20,
            "maxLength": 3000,
            "description": "LLM-synthesized summary of the intake conversation. INVARIANT: Must be derived, not copied verbatim from transcript."
        },
        "routing_rationale": {
            "type": "string",
            "minLength": 10,
            "maxLength": 1000,
            "description": "Explanation of why this gate outcome was determined"
        },
        "ready_for": {
            "type": ["string", "null"],
            "enum": ["pm_discovery", None],
            "description": "Next station if qualified, null otherwise"
        },
        "thread_id": {
            "type": "string",
            "description": "Reference to the durable conversation thread (ADR-035)"
        },
        "created_at": {
            "type": "string",
            "format": "date-time",
            "description": "Document creation timestamp"
        },
        "metadata": {
            "type": "object",
            "description": "Additional metadata",
            "additionalProperties": True
        }
    },
    "additionalProperties": False
}


# WS-STORY-BACKLOG-VIEW: Epic Stories Card Schema
# =============================================================================

EPIC_STORIES_CARD_BLOCK_V1_SCHEMA = {
    "$id": "schema:EpicStoriesCardBlockV1",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "title": "Epic Stories Card Block",
    "description": "View projection for an epic card with nested story summaries. NOT canonical storage.",
    "required": ["epic_id", "name", "stories"],
    "properties": {
        "epic_id": {
            "type": "string",
            "minLength": 1,
            "description": "Unique epic identifier"
        },
        "name": {
            "type": "string",
            "minLength": 1,
            "description": "Epic display name"
        },
        "intent": {
            "type": "string",
            "description": "Brief description of what the epic achieves"
        },
        "phase": {
            "type": "string",
            "enum": ["mvp", "later"],
            "description": "MVP or later phase"
        },
        "risk_level": {
            "type": "string",
            "enum": ["low", "medium", "high"],
            "description": "Derived or provided risk level"
        },
        "detail_ref": {
            "type": "object",
            "properties": {
                "document_type": {"type": "string"},
                "params": {"type": "object"}
            },
            "description": "Reference to EpicDetailView"
        },
        "stories": {
            "type": "array",
            "description": "Array of StorySummary items (empty allowed)",
            "items": {
                "type": "object",
                "required": ["story_id", "title", "intent", "phase"],
                "properties": {
                    "story_id": {
                        "type": "string",
                        "minLength": 1,
                        "description": "Story identifier (non-empty, no rigid format)"
                    },
                    "title": {
                        "type": "string",
                        "minLength": 1,
                        "description": "Story title"
                    },
                    "intent": {
                        "type": "string",
                        "minLength": 1,
                        "description": "Brief story intent"
                    },
                    "phase": {
                        "type": "string",
                        "enum": ["mvp", "later"],
                        "description": "MVP or later phase"
                    },
                    "risk_level": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Optional risk level"
                    },
                    "detail_ref": {
                        "type": "object",
                        "properties": {
                            "document_type": {"type": "string"},
                            "params": {"type": "object"}
                        },
                        "description": "Reference to StoryDetailView"
                    }
                }
            }
        }
    },
    "additionalProperties": False
}

INITIAL_SCHEMA_ARTIFACTS: List[Dict[str, Any]] = [
    {
        "schema_id": "OpenQuestionV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": OPEN_QUESTION_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-031"],
            "policies": []
        },
    },
    {
        "schema_id": "RiskV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": RISK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-031"],
            "policies": []
        },
    },
    {
        "schema_id": "ScopeListV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": SCOPE_LIST_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-031"],
            "policies": []
        },
    },
    {
        "schema_id": "DependencyV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": DEPENDENCY_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-031"],
            "policies": []
        },
    },
    # ADR-033: Render Model schemas
    {
        "schema_id": "RenderModelV1",
        "version": "1.0",
        "kind": "envelope",
        "status": "accepted",
        "schema_json": RENDER_MODEL_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-033"],
            "policies": []
        },
    },
    {
        "schema_id": "RenderSectionV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": RENDER_SECTION_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-033"],
            "policies": []
        },
    },
    {
        "schema_id": "RenderBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": RENDER_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-033"],
            "policies": []
        },
    },
    {
        "schema_id": "RenderActionV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": RENDER_ACTION_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-033"],
            "policies": []
        },
    },
    # ADR-034: Canonical Component and Document Definition schemas
    {
        "schema_id": "CanonicalComponentV1",
        "version": "1.0",
        "kind": "document",
        "status": "accepted",
        "schema_json": CANONICAL_COMPONENT_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": []
        },
    },
    {
        "schema_id": "DocumentDefinitionV2",
        "version": "1.0",
        "kind": "document",
        "status": "accepted",
        "schema_json": DOCUMENT_DEFINITION_V2_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": []
        },
    },
    # ADR-034-EXP: Container block schema
    {
        "schema_id": "OpenQuestionsBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": OPEN_QUESTIONS_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": []
        },
    },
    # ADR-034-EXP3: Story schemas
    {
        "schema_id": "StoryV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": STORY_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": []
        },
    },
    # ADR-034-DISCOVERY: Generic list and summary schemas
    {
        "schema_id": "StringListBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": STRING_LIST_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": []
        },
    },
    {
        "schema_id": "UnknownsBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": UNKNOWNS_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": []
        },
    },
    {
        "schema_id": "SummaryBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": SUMMARY_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": []
        },
    },
    {
        "schema_id": "RisksBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": RISKS_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": []
        },
    },
    {
        "schema_id": "ParagraphBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": PARAGRAPH_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": []
        },
    },
    {
        "schema_id": "IndicatorBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": INDICATOR_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": []
        },
    },
    {
        "schema_id": "EpicSummaryBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": EPIC_SUMMARY_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": []
        },
    },
    {
        "schema_id": "DependenciesBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": DEPENDENCIES_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": []
        },
    },
    {
        "schema_id": "DocumentRefV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": DOCUMENT_REF_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": ["SUMMARY_VIEW_CONTRACT"]
        },
    },
    {
        "schema_id": "StorySummaryBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": STORY_SUMMARY_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": ["SUMMARY_VIEW_CONTRACT"]
        },
    },
    {
        "schema_id": "StoriesBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": STORIES_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": []
        },
    },
    # ADR-034: Architecture component schemas
    {
        "schema_id": "ArchComponentBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": ARCH_COMPONENT_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": []
        },
    },
    {
        "schema_id": "QualityAttributeBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": QUALITY_ATTRIBUTE_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": []
        },
    },
    {
        "schema_id": "InterfaceBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": INTERFACE_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": []
        },
    },
    {
        "schema_id": "WorkflowBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": WORKFLOW_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": []
        },
    },
    {
        "schema_id": "WorkflowBlockV2",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": WORKFLOW_BLOCK_V2_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": []
        },
    },
    {
        "schema_id": "DataModelBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": DATA_MODEL_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": []
        },
    },
    # WS-STORY-BACKLOG-VIEW: Epic Stories Card
    {
        "schema_id": "EpicStoriesCardBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": EPIC_STORIES_CARD_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-034"],
            "policies": ["WS-STORY-BACKLOG-VIEW"]
        },
    },
    # ADR-025/ADR-039: Concierge Intake Document
    {
        "schema_id": "ConciergeIntakeDocumentV1",
        "version": "1.0",
        "kind": "document",
        "status": "accepted",
        "schema_json": CONCIERGE_INTAKE_DOCUMENT_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-025", "ADR-039"],
            "policies": []
        },
    },
    # ADR-039: Concierge Intake View Compound Blocks
    {
        "schema_id": "IntakeSummaryBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": INTAKE_SUMMARY_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-039"],
            "policies": []
        },
    },
    {
        "schema_id": "IntakeOutcomeBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": INTAKE_OUTCOME_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-039"],
            "policies": []
        },
    },
    {
        "schema_id": "IntakeConstraintsBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": INTAKE_CONSTRAINTS_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-039"],
            "policies": []
        },
    },
    {
        "schema_id": "IntakeOpenGapsBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": INTAKE_OPEN_GAPS_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-039"],
            "policies": []
        },
    },
    {
        "schema_id": "IntakeProjectTypeBlockV1",
        "version": "1.0",
        "kind": "type",
        "status": "accepted",
        "schema_json": INTAKE_PROJECT_TYPE_BLOCK_V1_SCHEMA,
        "governance_refs": {
            "adrs": ["ADR-039"],
            "policies": []
        },
    },
]


async def seed_schema_artifacts(db: AsyncSession) -> int:
    """
    Seed the schema_artifacts table with canonical types.
    
    Skips any artifacts that already exist (by schema_id + version).
    
    Args:
        db: Database session
        
    Returns:
        Number of artifacts created
    """
    registry = SchemaRegistryService(db)
    created_count = 0
    
    for artifact_data in INITIAL_SCHEMA_ARTIFACTS:
        schema_id = artifact_data["schema_id"]
        version = artifact_data["version"]
        
        # Check if already exists
        existing = await registry.get_by_id(schema_id, version)
        
        if existing:
            logger.info(f"Schema '{schema_id}' v{version} already exists, skipping")
            continue
        
        # Create the artifact
        await registry.create(
            schema_id=schema_id,
            version=version,
            kind=artifact_data["kind"],
            status=artifact_data["status"],
            schema_json=artifact_data["schema_json"],
            governance_refs=artifact_data.get("governance_refs"),
            created_by="seed",
        )
        
        created_count += 1
        logger.info(f"Created schema: {schema_id} v{version} ({artifact_data['status']})")
    
    logger.info(f"Seeded {created_count} schema artifacts")
    return created_count


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
            count = await seed_schema_artifacts(db)
            await db.commit()
            print(f"Seeded {count} schema artifacts")
    
    asyncio.run(main())































