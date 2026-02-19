"""
Seed data for document_types table.

Run this after creating the document_types table to populate
the initial document types.

Usage:
    python -m app.domain.registry.seed_document_types
    
Or call seed_document_types(db) from your migration.
"""

from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.api.models.document_type import DocumentType

logger = logging.getLogger(__name__)


# =============================================================================
# SEED DATA - Initial Document Types
# =============================================================================

INITIAL_DOCUMENT_TYPES: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # INTAKE DOCUMENTS
    # -------------------------------------------------------------------------
    {
        "doc_type_id": "concierge_intake",
        "name": "Concierge Intake",
        "view_docdef": "ConciergeIntakeView",
        "description": (
            "Structured intake document produced by the Concierge workflow. "
            "Contains synthesized intent, constraints, and gate outcomes."
        ),
        "category": "intake",
        "icon": "message-circle",
        "builder_role": "concierge",
        "builder_task": "intake",
        "handler_id": "concierge_intake",
        "required_inputs": [],
        "optional_inputs": [],
        "gating_rules": {},
        "scope": "project",
        "display_order": 5,
        "schema_definition": {
            "$ref": "schema:ConciergeIntakeDocumentV1"
        },
        "schema_version": "1.0",
    },
    # -------------------------------------------------------------------------
    # ARCHITECTURE DOCUMENTS
    # -------------------------------------------------------------------------
    {
        "doc_type_id": "project_discovery",
        "name": "Project Discovery",
        "view_docdef": "ProjectDiscovery",
        "description": (
            "Early architectural discovery performed before PM decomposition. "
            "Surfaces critical questions, identifies constraints and risks, "
            "proposes candidate directions, and establishes guardrails."
        ),
        "category": "architecture",
        "icon": "search",
        "builder_role": "architect",
        "builder_task": "preliminary",
        "handler_id": "project_discovery",
        "required_inputs": [],  # No dependencies - this is the first document
        "optional_inputs": [],
        "gating_rules": {},
        "scope": "project",
        "display_order": 10,
        "schema_definition": {
            "type": "object",
            "required": ["project_name", "preliminary_summary"],
            "properties": {
                "project_name": {"type": "string"},
                "preliminary_summary": {"type": "string"},
                "unknowns": {"type": "array", "items": {"type": "object"}},
                "blocking_questions": {"type": "array", "items": {"type": "object"}},
                "early_decision_points": {"type": "array", "items": {"type": "object"}},
                "mvp_guardrails": {"type": "array", "items": {"type": "object"}},
                "architectural_directions": {"type": "array", "items": {"type": "object"}},
            }
        },
        "schema_version": "1.0",
    },
    {
        "doc_type_id": "technical_architecture",
        "name": "Technical Architecture",
        "view_docdef": "TechnicalArchitectureView",
        "description": (
            "Comprehensive technical architecture including components, "
            "interfaces, data models, workflows, and quality attributes. "
            "Built after primary implementation plan, informs final planning."
        ),
        "category": "architecture",
        "icon": "landmark",
        "builder_role": "architect",
        "builder_task": "technical_architecture",
        "handler_id": "technical_architecture",
        "required_inputs": ["project_discovery", "implementation_plan_primary"],
        "optional_inputs": [],
        "gating_rules": {},
        "scope": "project",
        "display_order": 30,  # After implementation_plan_primary (25)
        "schema_definition": {
            "type": "object",
            "required": ["architecture_summary", "components"],
            "properties": {
                "architecture_summary": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "style": {"type": "string"},
                        "key_decisions": {"type": "array", "items": {"type": "string"}},
                    }
                },
                "components": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "purpose"],
                        "properties": {
                            "name": {"type": "string"},
                            "purpose": {"type": "string"},
                            "technology": {"type": "string"},
                            "interfaces": {"type": "array"},
                        }
                    }
                },
                "data_models": {"type": "array"},
                "api_interfaces": {"type": "array"},
                "quality_attributes": {"type": "object"},
                "workflows": {"type": "array"},
                "risks": {"type": "array"},
            }
        },
        "schema_version": "1.0",
    },
    
    # -------------------------------------------------------------------------
    # PLANNING DOCUMENTS
    # -------------------------------------------------------------------------
    {
        "doc_type_id": "implementation_plan_primary",
        "name": "Implementation Plan (Primary)",
        "view_docdef": "ImplementationPlanPrimaryView",
        "description": (
            "Preliminary implementation plan produced before technical architecture. "
            "Contains epic candidates that inform architectural decisions. "
            "Epic candidates are not yet commitments - they become Epics after "
            "architecture review in the full Implementation Plan."
        ),
        "category": "planning",
        "icon": "map",
        "builder_role": "pm",
        "builder_task": "preliminary_planning",
        "handler_id": "implementation_plan_primary",
        "required_inputs": ["project_discovery"],
        "optional_inputs": [],  # Comes before architecture
        "gating_rules": {},
        "scope": "project",
        "display_order": 25,  # Before architecture_spec (20 -> 25 -> 30)
        "schema_definition": {
            "type": "object",
            "required": ["epic_candidates"],
            "properties": {
                "epic_set_summary": {
                    "type": "object",
                    "properties": {
                        "overall_intent": {"type": "string"},
                        "mvp_definition": {"type": "string"},
                        "key_constraints": {"type": "array", "items": {"type": "string"}},
                        "out_of_scope": {"type": "array", "items": {"type": "string"}},
                    }
                },
                "epic_candidates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "intent"],
                        "properties": {
                            "candidate_id": {"type": "string"},
                            "name": {"type": "string"},
                            "intent": {"type": "string"},
                            "in_scope": {"type": "array", "items": {"type": "string"}},
                            "out_of_scope": {"type": "array", "items": {"type": "string"}},
                            "mvp_phase": {"type": "string"},
                            "open_questions": {"type": "array"},
                            "notes_for_architecture": {"type": "array", "items": {"type": "string"}},
                        }
                    }
                },
                "risks_overview": {"type": "array"},
                "recommendations_for_architecture": {"type": "array", "items": {"type": "string"}},
            }
        },
        "schema_version": "1.0",
    },
    {
        "doc_type_id": "implementation_plan",
        "name": "Implementation Plan",
        "view_docdef": "ImplementationPlanView",
        "description": (
            "Final implementation plan produced after technical architecture review. "
            "Defines committed Epics with sequencing, dependencies, and design requirements. "
            "Creating this document spawns individual Epic documents."
        ),
        "category": "planning",
        "icon": "git-branch",
        "builder_role": "pm",
        "builder_task": "implementation_planning",
        "handler_id": "implementation_plan",
        "required_inputs": ["implementation_plan_primary", "technical_architecture"],
        "optional_inputs": [],
        "gating_rules": {},
        "scope": "project",
        "display_order": 35,
        "creates_children": ["epic"],  # This plan creates Epic documents
        "schema_definition": {
            "type": "object",
            "required": ["plan_summary", "epics"],
            "properties": {
                "plan_summary": {
                    "type": "object",
                    "properties": {
                        "overall_intent": {"type": "string"},
                        "mvp_definition": {"type": "string"},
                        "key_constraints": {"type": "array", "items": {"type": "string"}},
                        "sequencing_rationale": {"type": "string"},
                    }
                },
                "epics": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["epic_id", "name", "intent"],
                        "properties": {
                            "epic_id": {"type": "string"},
                            "name": {"type": "string"},
                            "intent": {"type": "string"},
                            "sequence": {"type": "integer"},
                            "mvp_phase": {"type": "string", "enum": ["mvp", "later"]},
                            "design_required": {"type": "string", "enum": ["not_needed", "recommended", "required"]},
                            "in_scope": {"type": "array", "items": {"type": "string"}},
                            "out_of_scope": {"type": "array", "items": {"type": "string"}},
                            "dependencies": {"type": "array"},
                            "risks": {"type": "array"},
                            "open_questions": {"type": "array"},
                            "architecture_notes": {"type": "array", "items": {"type": "string"}},
                        }
                    }
                },
                "cross_cutting_concerns": {"type": "array", "items": {"type": "string"}},
                "risk_summary": {"type": "array"},
            }
        },
        "schema_version": "1.0",
    },
    # -------------------------------------------------------------------------
    # EPIC & FEATURE DOCUMENTS (SDLC Workflow)
    # -------------------------------------------------------------------------
    {
        "doc_type_id": "epic",
        "name": "Epic",
        "view_docdef": "EpicView",
        "description": (
            "Unit of planning and commitment. Has lifecycle gates (draft, ready, "
            "in_progress, blocked, complete). May require design phase. "
            "Parent container for Features."
        ),
        "category": "planning",
        "icon": "package",
        "builder_role": None,  # Created by implementation_plan, not LLM-generated
        "builder_task": None,
        "handler_id": "epic",
        "required_inputs": [],
        "optional_inputs": [],
        "gating_rules": {
            "lifecycle_states": ["draft", "ready", "in_progress", "blocked", "complete"],
            "design_status": ["not_needed", "recommended", "required", "complete"],
        },
        "scope": "project",
        "parent_doc_type": "implementation_plan",  # Created by implementation_plan
        "display_order": 36,
        "creates_children": ["feature"],
        "schema_definition": {
            "type": "object",
            "required": ["epic_id", "name", "intent"],
            "properties": {
                "epic_id": {"type": "string"},
                "name": {"type": "string"},
                "intent": {"type": "string"},
                "lifecycle_state": {"type": "string", "enum": ["draft", "ready", "in_progress", "blocked", "complete"]},
                "design_status": {"type": "string", "enum": ["not_needed", "recommended", "required", "complete"]},
                "sequence": {"type": "integer"},
                "mvp_phase": {"type": "string", "enum": ["mvp", "later"]},
                "in_scope": {"type": "array", "items": {"type": "string"}},
                "out_of_scope": {"type": "array", "items": {"type": "string"}},
                "dependencies": {"type": "array"},
                "risks": {"type": "array"},
                "open_questions": {"type": "array"},
                "architecture_notes": {"type": "array", "items": {"type": "string"}},
                "features": {"type": "array"},  # Nested feature summaries
            }
        },
        "schema_version": "1.0",
    },
    {
        "doc_type_id": "feature",
        "name": "Feature",
        "view_docdef": "FeatureView",
        "description": (
            "Unit of production intent. Defines what will be produced. "
            "Handoff point between planning and execution. "
            "Contains nested Stories."
        ),
        "category": "planning",
        "icon": "puzzle",
        "builder_role": "ba",
        "builder_task": "feature_decomposition",
        "handler_id": "feature",
        "required_inputs": [],
        "optional_inputs": ["technical_architecture"],
        "gating_rules": {},
        "scope": "epic",
        "parent_doc_type": "epic",
        "display_order": 37,
        "schema_definition": {
            "type": "object",
            "required": ["feature_id", "name", "description"],
            "properties": {
                "feature_id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
                "stories": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["story_id", "title"],
                        "properties": {
                            "story_id": {"type": "string"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "acceptance_criteria": {"type": "array"},
                            "story_points": {"type": "integer"},
                            "priority": {"type": "string"},
                        }
                    }
                },
                "technical_notes": {"type": "array", "items": {"type": "string"}},
            }
        },
        "schema_version": "1.0",
    },
    # -------------------------------------------------------------------------
    # WORK PACKAGE (WS-ONTOLOGY-001)
    # -------------------------------------------------------------------------
    {
        "doc_type_id": "work_package",
        "name": "Work Package",
        "view_docdef": "WorkPackageView",
        "description": (
            "Unit of planned work replacing the Epic/Feature ontology. "
            "Created by IPF reconciliation. Tracks state, dependencies, "
            "governance pins, and child Work Statement references."
        ),
        "category": "planning",
        "icon": "package",
        "builder_role": None,  # Not LLM-generated — created by IPF reconciliation
        "builder_task": None,
        "handler_id": "work_package",
        "required_inputs": [],
        "optional_inputs": [],
        "gating_rules": {},
        "scope": "project",
        "cardinality": "multi",
        "instance_key": "wp_id",
        "display_order": 38,
        "schema_definition": {
            "type": "object",
            "required": [
                "wp_id",
                "title",
                "rationale",
                "scope_in",
                "scope_out",
                "dependencies",
                "definition_of_done",
                "state",
                "ws_child_refs",
                "governance_pins",
            ],
            "properties": {
                "wp_id": {"type": "string"},
                "title": {"type": "string"},
                "rationale": {"type": "string"},
                "scope_in": {"type": "array", "items": {"type": "string"}},
                "scope_out": {"type": "array", "items": {"type": "string"}},
                "dependencies": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "wp_id": {"type": "string"},
                            "dependency_type": {"type": "string"},
                        },
                    },
                },
                "definition_of_done": {"type": "array", "items": {"type": "string"}},
                "state": {
                    "type": "string",
                    "enum": ["PLANNED", "READY", "IN_PROGRESS", "AWAITING_GATE", "DONE"],
                },
                "ws_child_refs": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "governance_pins": {
                    "type": "object",
                    "properties": {
                        "adr_refs": {"type": "array", "items": {"type": "string"}},
                        "policy_refs": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
        },
        "schema_version": "1.0",
    },
    # -------------------------------------------------------------------------
    # WORK STATEMENT (WS-ONTOLOGY-002)
    # -------------------------------------------------------------------------
    {
        "doc_type_id": "work_statement",
        "name": "Work Statement",
        "view_docdef": "WorkStatementView",
        "description": (
            "Unit of authorized execution within a Work Package. "
            "Defines objective, scope, procedure, verification criteria, "
            "and prohibited actions. Has its own lifecycle state machine."
        ),
        "category": "planning",
        "icon": "file-check",
        "builder_role": None,  # Not LLM-generated
        "builder_task": None,
        "handler_id": "work_statement",
        "required_inputs": [],
        "optional_inputs": [],
        "gating_rules": {},
        "scope": "project",
        "cardinality": "multi",
        "instance_key": "ws_id",
        "parent_doc_type": "work_package",
        "display_order": 39,
        "schema_definition": {
            "type": "object",
            "required": [
                "ws_id",
                "parent_wp_id",
                "title",
                "objective",
                "scope_in",
                "scope_out",
                "procedure",
                "verification_criteria",
                "prohibited_actions",
                "state",
                "governance_pins",
            ],
            "properties": {
                "ws_id": {"type": "string"},
                "parent_wp_id": {"type": "string"},
                "title": {"type": "string"},
                "objective": {"type": "string"},
                "scope_in": {"type": "array", "items": {"type": "string"}},
                "scope_out": {"type": "array", "items": {"type": "string"}},
                "procedure": {"type": "array", "items": {"type": "string"}},
                "verification_criteria": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "prohibited_actions": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "state": {
                    "type": "string",
                    "enum": [
                        "DRAFT",
                        "READY",
                        "IN_PROGRESS",
                        "ACCEPTED",
                        "REJECTED",
                        "BLOCKED",
                    ],
                },
                "governance_pins": {
                    "type": "object",
                    "properties": {
                        "adr_refs": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "policy_refs": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
        },
        "schema_version": "1.0",
    },
    # -------------------------------------------------------------------------
    # PROJECT LOGBOOK (WS-ONTOLOGY-003)
    # -------------------------------------------------------------------------
    {
        "doc_type_id": "project_logbook",
        "name": "Project Logbook",
        "view_docdef": "ProjectLogbookView",
        "description": (
            "Append-only audit trail of Work Statement acceptances. "
            "Created lazily on first WS acceptance. Tracks mode-B rate "
            "and verification debt across the project."
        ),
        "category": "governance",
        "icon": "book-open",
        "builder_role": None,  # Not LLM-generated — created by acceptance orchestration
        "builder_task": None,
        "handler_id": "project_logbook",
        "required_inputs": [],
        "optional_inputs": [],
        "gating_rules": {},
        "scope": "project",
        "display_order": 40,
        "schema_definition": {
            "type": "object",
            "required": [
                "schema_version",
                "project_id",
                "mode_b_rate",
                "verification_debt_open",
                "entries",
            ],
            "properties": {
                "schema_version": {"type": "string"},
                "project_id": {"type": "string"},
                "mode_b_rate": {"type": "number"},
                "verification_debt_open": {"type": "integer"},
                "program_ref": {"type": "string"},
                "entries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "timestamp": {"type": "string"},
                            "ws_id": {"type": "string"},
                            "parent_wp_id": {"type": "string"},
                            "result": {"type": "string"},
                            "mode_b_list": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "tier0_json": {"type": "object"},
                        },
                    },
                },
            },
        },
        "schema_version": "1.0",
    },
    # -------------------------------------------------------------------------
    # LEGACY
    # -------------------------------------------------------------------------
    {
        "doc_type_id": "story_backlog",
        "name": "Story Backlog (Legacy)",
        "view_docdef": "StoryBacklogView",
        "description": (
            "Legacy: User stories decomposed from an epic. "
            "Being replaced by Feature documents with nested stories."
        ),
        "category": "planning",
        "icon": "list-checks",
        "builder_role": "ba",
        "builder_task": "story_decomposition",
        "handler_id": "story_backlog",
        "required_inputs": [],  # Required at epic scope, so epic must exist
        "optional_inputs": ["technical_architecture"],
        "gating_rules": {},
        "scope": "epic",  # One per epic
        "display_order": 50,
        "schema_definition": {
            "type": "object",
            "required": ["stories"],
            "properties": {
                "epic_id": {"type": "string"},
                "stories": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["title", "description"],
                        "properties": {
                            "story_id": {"type": "string"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "acceptance_criteria": {"type": "array"},
                            "story_points": {"type": "integer"},
                            "priority": {"type": "string"},
                        }
                    }
                }
            }
        },
        "schema_version": "1.0",
    },
]


async def seed_document_types(db: AsyncSession) -> int:
    """
    Seed the document_types table with initial document types.
    
    Skips any document types that already exist (by doc_type_id).
    
    Args:
        db: Database session
        
    Returns:
        Number of document types created
    """
    created_count = 0
    
    for doc_data in INITIAL_DOCUMENT_TYPES:
        doc_type_id = doc_data["doc_type_id"]
        
        # Check if already exists
        query = select(DocumentType).where(DocumentType.doc_type_id == doc_type_id)
        result = await db.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.info(f"Document type '{doc_type_id}' already exists, skipping")
            continue
        
        # Create new document type
        doc_type = DocumentType(**doc_data)
        db.add(doc_type)
        created_count += 1
        logger.info(f"Created document type: {doc_type_id}")
    
    await db.commit()
    logger.info(f"Seeded {created_count} document types")
    
    return created_count


async def clear_document_types(db: AsyncSession) -> int:
    """
    Clear all document types from the table.
    
    WARNING: This is destructive. Use only in development/testing.
    
    Args:
        db: Database session
        
    Returns:
        Number of document types deleted
    """
    from sqlalchemy import delete
    
    result = await db.execute(delete(DocumentType))
    await db.commit()
    
    deleted_count = result.rowcount
    logger.warning(f"Deleted {deleted_count} document types")
    
    return deleted_count


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import asyncio
    from app.core.database import async_session_factory
    
    async def main():
        async with async_session_factory() as db:
            count = await seed_document_types(db)
            await db.commit()
            print(f"Seeded {count} document types")
    
    asyncio.run(main())