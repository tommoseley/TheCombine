"""Add concierge_intake document type.

Revision ID: 20260121_001
Revises: update_project_id_fmt
Create Date: 2026-01-21

WS-INTAKE-SEP-001: Create Concierge Intake document type as part of 
IP-INTAKE-SEPARATION-001 (separating intake from PM Discovery).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260121_001'
down_revision = '20260119_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add concierge_intake document type."""
    # Insert concierge_intake document type using correct column names
    op.execute("""
        INSERT INTO document_types (
            id, doc_type_id, name, description, category, icon,
            schema_definition, schema_version, builder_role, builder_task,
            handler_id, required_inputs, optional_inputs, gating_rules,
            scope, display_order, is_active, version,
            created_at, updated_at, view_docdef
        ) VALUES (
            gen_random_uuid(),
            'concierge_intake',
            'Concierge Intake',
            'Captures the user''s raw input, interpreted fields, constraints, and routing classification from the intake workflow. This is the first document created for a project and serves as input to PM Discovery.',
            'intake',
            'clipboard-check',
            '{
                "type": "object",
                "required": ["project_name", "summary", "project_type", "outcome"],
                "properties": {
                    "project_name": {"type": "string"},
                    "summary": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "user_statement": {"type": "string"}
                        }
                    },
                    "project_type": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string"},
                            "confidence": {"type": "string"},
                            "rationale": {"type": "string"}
                        }
                    },
                    "constraints": {
                        "type": "object",
                        "properties": {
                            "explicit": {"type": "array"},
                            "inferred": {"type": "array"},
                            "none_stated": {"type": "boolean"}
                        }
                    },
                    "open_gaps": {
                        "type": "object",
                        "properties": {
                            "questions": {"type": "array"},
                            "missing_context": {"type": "array"},
                            "assumptions_made": {"type": "array"}
                        }
                    },
                    "outcome": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string"},
                            "rationale": {"type": "string"},
                            "next_action": {"type": "string"}
                        }
                    }
                }
            }'::jsonb,
            '1.0',
            'concierge',
            'intake',
            'concierge_intake',
            '[]'::jsonb,
            '[]'::jsonb,
            '{}'::jsonb,
            'project',
            5,
            true,
            '1.0',
            NOW(),
            NOW(),
            NULL
        )
        ON CONFLICT (doc_type_id) DO NOTHING;
    """)


def downgrade() -> None:
    """Remove concierge_intake document type."""
    op.execute("""
        DELETE FROM document_types WHERE doc_type_id = 'concierge_intake';
    """)