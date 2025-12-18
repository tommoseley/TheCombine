"""
Seed acceptance configuration for document types (ADR-007).

This script updates existing document types with:
- acceptance_required: Whether human sign-off is needed
- accepted_by_role: Which role must accept
- icon: Lucide icon name for sidebar display

Run after migration: 20241218_001_acceptance
"""

import logging
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import update, select
from database import get_db_session

logger = logging.getLogger(__name__)

# ============================================================================
# ACCEPTANCE CONFIGURATION
# ============================================================================
# 
# Key principle from ADR-007:
# - project_discovery: No acceptance required (foundational, low-risk)
# - architecture_spec: Architect must accept (high-impact technical decisions)
# - epic_set: PM must accept (scoping decisions)
# - story_backlog: No acceptance (derived from accepted epics)
#

DOCUMENT_TYPE_CONFIG = {
    "project_discovery": {
        "acceptance_required": False,
        "accepted_by_role": None,
        "icon": "search",
        "display_order": 10,
    },
    "architecture_spec": {
        "acceptance_required": True,
        "accepted_by_role": "architect",
        "icon": "landmark",
        "display_order": 20,
    },
    "epic_set": {
        "acceptance_required": True,
        "accepted_by_role": "pm",
        "icon": "layers",
        "display_order": 30,
    },
    "story_backlog": {
        "acceptance_required": False,
        "accepted_by_role": None,
        "icon": "list-checks",
        "display_order": 40,
    },
    # Standards documents (typically organization-level)
    "security_baseline": {
        "acceptance_required": True,
        "accepted_by_role": "security",
        "icon": "shield",
        "display_order": 100,
    },
    "coding_standards": {
        "acceptance_required": True,
        "accepted_by_role": "tech_lead",
        "icon": "code",
        "display_order": 110,
    },
}


def seed_acceptance_config() -> None:
    """
    Update document types with acceptance configuration.
    
    Idempotent - safe to run multiple times.
    """
    from app.api.models.document_type import DocumentType
    
    with get_db_session() as session:
        for doc_type_id, config in DOCUMENT_TYPE_CONFIG.items():
            try:
                stmt = (
                    update(DocumentType)
                    .where(DocumentType.doc_type_id == doc_type_id)
                    .values(
                        acceptance_required=config["acceptance_required"],
                        accepted_by_role=config["accepted_by_role"],
                        icon=config["icon"],
                        display_order=config["display_order"],
                    )
                )
                result = session.execute(stmt)
                
                if result.rowcount > 0:
                    logger.info(f"✅ Updated {doc_type_id}: acceptance_required={config['acceptance_required']}")
                else:
                    logger.warning(f"⚠️ Document type '{doc_type_id}' not found - skipping")
                    
            except Exception as e:
                logger.error(f"❌ Failed to update {doc_type_id}: {e}")
                raise
        
        # Commit happens automatically via context manager
        logger.info("✅ Acceptance configuration seeding complete")


def verify_config() -> None:
    """Verify the configuration was applied correctly."""
    from app.api.models.document_type import DocumentType
    
    with get_db_session() as session:
        stmt = select(DocumentType).where(DocumentType.is_active == True)
        result = session.execute(stmt)
        doc_types = result.scalars().all()
        
        print("\n" + "=" * 70)
        print("DOCUMENT TYPE ACCEPTANCE CONFIGURATION")
        print("=" * 70)
        print(f"{'Type ID':<25} {'Accept?':<10} {'Role':<15} {'Icon':<15}")
        print("-" * 70)
        
        for dt in sorted(doc_types, key=lambda x: x.display_order or 0):
            accept = "Yes" if dt.acceptance_required else "No"
            role = dt.accepted_by_role or "-"
            icon = dt.icon or "-"
            print(f"{dt.doc_type_id:<25} {accept:<10} {role:<15} {icon:<15}")
        
        print("=" * 70 + "\n")


def main():
    """Run seeding with verification."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    seed_acceptance_config()
    verify_config()


if __name__ == "__main__":
    main()