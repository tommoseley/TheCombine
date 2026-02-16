"""Create reset_document stored procedure

Revision ID: 20260216_001
Revises: 20260204_001
Create Date: 2026-02-16

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260216_001'
down_revision: Union[str, None] = '20260204_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE PROCEDURE reset_document(
            p_project_code TEXT,
            p_doc_type     TEXT
        )
        LANGUAGE plpgsql AS $$
        DECLARE
            v_project_uuid UUID;
            v_doc_id       UUID;
            v_child_count  INT;
            v_exec_count   INT;
        BEGIN
            -- Resolve project
            SELECT id INTO v_project_uuid
            FROM projects
            WHERE project_id = p_project_code AND deleted_at IS NULL;

            IF v_project_uuid IS NULL THEN
                RAISE EXCEPTION 'Project "%" not found', p_project_code;
            END IF;

            -- Find target document
            SELECT id INTO v_doc_id
            FROM documents
            WHERE space_id = v_project_uuid
              AND doc_type_id = p_doc_type
              AND is_latest = TRUE;

            IF v_doc_id IS NULL THEN
                RAISE EXCEPTION 'No latest document of type "%" for project "%"',
                    p_doc_type, p_project_code;
            END IF;

            -- Delete child documents first (FK is RESTRICT)
            DELETE FROM documents WHERE parent_document_id = v_doc_id;
            GET DIAGNOSTICS v_child_count = ROW_COUNT;
            IF v_child_count > 0 THEN
                RAISE NOTICE 'Deleted % child document(s)', v_child_count;
            END IF;

            -- Delete the document
            DELETE FROM documents WHERE id = v_doc_id;
            RAISE NOTICE 'Deleted document % (%)', p_doc_type, v_doc_id;

            -- Delete workflow executions
            DELETE FROM workflow_executions
            WHERE project_id = v_project_uuid
              AND document_type = p_doc_type;
            GET DIAGNOSTICS v_exec_count = ROW_COUNT;
            IF v_exec_count > 0 THEN
                RAISE NOTICE 'Deleted % workflow execution(s)', v_exec_count;
            END IF;

            RAISE NOTICE 'Reset complete for %.%', p_project_code, p_doc_type;
        END;
        $$;
    """)


def downgrade() -> None:
    op.execute("DROP PROCEDURE IF EXISTS reset_document(TEXT, TEXT);")
