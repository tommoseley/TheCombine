#!/usr/bin/env python3
"""
Run The Combine API server.

Usage:
    python scripts/run.py
    ./run.sh (Unix)
    .\run.ps1 (Windows)
"""

import os
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

def load_env():
    """Load environment variables from .env file."""
    env_file = ROOT / ".env"
    if env_file.exists():
        print(f"✅ Loaded environment from {env_file}")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    os.environ[key.strip()] = value.strip()
    else:
        print(f"⚠️  No .env file found at {env_file}")

def print_config():
    """Print server configuration."""
    db_url = os.getenv("WORKBENCH_DATABASE_URL", "sqlite:///./data/workbench_ai.db")
    
    print(f"   Database: {db_url}")
    print(f"   API docs: http://localhost:8000/docs")
    print(f"   Health: http://localhost:8000/health")
    print()
    print("💡 After server starts, visit http://localhost:8000/health to verify system health")
    print()

def main():
    """Run the server."""
    print("🚀 Starting The Combine API...")
    
    # Load environment
    load_env()
    print_config()
    
    # Start server
    import uvicorn
    
    uvicorn.run(
        "app.orchestrator_api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )

if __name__ == "__main__":
    main()