"""Debug script to verify imports and table creation."""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    # Test 1: Can we import Base?
    try:
        from app.core.database import Base
        print("✅ Base imported from app.core.database")
    except ImportError as e:
        print(f"❌ Failed to import Base: {e}")
    
    # Test 2: Import Document
    try:
        from app.api.models.document import Document
        print("✅ Document model imported")
        print(f"   Table name: {Document.__tablename__}")
    except ImportError as e:
        print(f"❌ Failed to import Document: {e}")
    
    # Test 3: Import Project
    try:
        from app.api.models import Project
        print("✅ Project model imported")
        print(f"   Table name: {Project.__tablename__}")
    except ImportError as e:
        print(f"❌ Failed to import Project: {e}")
    
    # Test 4: Import LLM models (THIS IS THE KEY!)
    try:
        from app.domain.models import (  # noqa: F401
            LLMContent, LLMRun, LLMRunInputRef,
            LLMRunOutputRef, LLMRunError, LLMRunToolCall
        )
        print("✅ LLM models imported from app.domain.models")
        print(f"   LLMContent table: {LLMContent.__tablename__}")
        print(f"   LLMRun table: {LLMRun.__tablename__}")
    except ImportError as e:
        print(f"❌ Failed to import LLM models: {e}")
    
    # Test 5: NOW check what's registered (AFTER importing models)
    try:
        from app.core.database import Base
        print(f"\n📋 Registered tables ({len(Base.metadata.tables)}):")
        for table_name in sorted(Base.metadata.tables.keys()):
            print(f"  - {table_name}")
    except Exception as e:
        print(f"❌ Failed to list tables: {e}")
    
    # Test 6: Check specifically for LLM tables
    try:
        from app.core.database import Base
        llm_tables = [t for t in Base.metadata.tables.keys() if 'llm' in t]
        if llm_tables:
            print(f"\n✅ LLM logging tables found ({len(llm_tables)}):")
            for table in sorted(llm_tables):
                print(f"  - {table}")
        else:
            print("\n❌ No LLM logging tables found!")
    except Exception as e:
        print(f"❌ Error checking LLM tables: {e}")