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
    from app.core.database import get_db_session
    
    async def main():
        async with get_db_session() as db:
            count = await seed_schema_artifacts(db)
            print(f"Seeded {count} schema artifacts")
    
    asyncio.run(main())