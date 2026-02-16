#!/usr/bin/env python3
"""
Reset a document and its dependents for re-production.

Calls the reset_document stored procedure, then cleans up
matching workflow state files from data/workflow_state/.

Usage:
    python ops/db/reset_document.py MTWA-001 implementation_plan
"""
import sys
import os
import glob
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <project_code> <doc_type>")
        print(f"Example: {sys.argv[0]} MTWA-001 implementation_plan")
        return 1

    project_code = sys.argv[1]
    doc_type = sys.argv[2]

    # --- DB: call stored procedure ---
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL environment variable not set")
        return 1

    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    if "+psycopg2" not in sync_url:
        sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://")

    engine = create_engine(sync_url)

    try:
        with engine.connect() as conn:
            conn.execute(
                text("CALL reset_document(:project_code, :doc_type)"),
                {"project_code": project_code, "doc_type": doc_type},
            )
            conn.commit()
        print(f"DB reset complete for {project_code}.{doc_type}")
    except Exception as e:
        print(f"DB error: {e}")
        return 1

    # --- Filesystem: clean up workflow state files ---
    state_dir = ROOT / "data" / "workflow_state"
    if state_dir.is_dir():
        # Workflow state files use project_id (lowercase, no dash)
        # e.g. software_product_development_proj_new_state.json
        # Match any file containing the project code (case-insensitive)
        pattern = str(state_dir / f"*{doc_type}*{project_code}*")
        matches = glob.glob(pattern, recursive=False)

        # Also try broader match: any file with both tokens
        if not matches:
            all_files = list(state_dir.glob("*.json"))
            code_lower = project_code.lower().replace("-", "_")
            matches = [
                str(f) for f in all_files
                if doc_type in f.name and code_lower in f.name.lower()
            ]

        if matches:
            for path in matches:
                os.remove(path)
                print(f"Removed: {path}")
        else:
            print("No matching workflow state files found (OK)")

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
