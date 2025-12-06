# config.py

"""Configuration for The Combine workforce."""

import os
import sys
from pathlib import Path
from typing import Optional
from pydantic import Field
# Detect if running in pytest
_IN_PYTEST = "pytest" in sys.modules

# Project root directory
if _IN_PYTEST:
    # In tests, use WORKBENCH_DATA_ROOT from environment (set by conftest.py)
    # This maintains architectural constraint: config override via env vars only
    data_root_env = os.environ.get("WORKBENCH_DATA_ROOT")
    if data_root_env:
        DATA_ROOT = Path(data_root_env)
        PROJECT_ROOT = DATA_ROOT.parent
    else:
        # Fallback if env var not set (shouldn't happen with proper test setup)
        import tempfile
        # Use pytest-specific temp directory name to satisfy isolation check
        PROJECT_ROOT = Path(tempfile.gettempdir()) / "pytest_combine_test"
        DATA_ROOT = PROJECT_ROOT / "data"
        # Create directory if it doesn't exist
        DATA_ROOT.mkdir(parents=True, exist_ok=True)
else:
    # Production: use actual project root
    PROJECT_ROOT = Path(__file__).parent.resolve()
    DATA_ROOT = PROJECT_ROOT / "data"

# Workforce root directory
WORKFORCE_ROOT = PROJECT_ROOT / "workforce"

# Epic directory
EPIC_DIR = PROJECT_ROOT / "epics"

# Epics root (for compatibility with existing code)
EPICS_ROOT = DATA_ROOT / "epics"

# Logs root (for compatibility with existing code)
LOGS_ROOT = DATA_ROOT / "logs"

# Canon directory
CANON_DIR = WORKFORCE_ROOT / "canon"

# Output directory
OUTPUT_DIR = PROJECT_ROOT / "outputs"

# Document directory
DOCUMENT_DIR = PROJECT_ROOT / "docs"

# Guides directory
GUIDES_DIR = DOCUMENT_DIR / "guides"

# Tests root (if exists)
TESTS_ROOT = PROJECT_ROOT / "tests"

# --- DATABASE CONFIGURATION (NEW) ---
DB_PATH = DATA_ROOT / "workbench_ai.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Ensure test directories exist when in pytest
if _IN_PYTEST and not data_root_env:
    EPICS_ROOT.mkdir(parents=True, exist_ok=True)
    LOGS_ROOT.mkdir(parents=True, exist_ok=True)

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Authentication
API_KEYS = os.getenv("API_KEYS", "")  # Comma-separated

# Reset Behavior
ALLOW_RESET_IN_CRITICAL_PHASES = os.getenv("ALLOW_RESET_IN_CRITICAL_PHASES", "false").lower() == "true"

# Request Size Limits (QA-Blocker #1)
MAX_REQUEST_BODY_SIZE = int(os.getenv("MAX_REQUEST_BODY_SIZE", 10 * 1024 * 1024))  # 10MB default

# PIPELINE-175B: Data-driven orchestration feature flag
DATA_DRIVEN_ORCHESTRATION: bool = Field(
    default=False,
    description="Enable data-driven pipeline orchestration (PIPELINE-175B)"
)

# Anthropic API configuration (for data-driven mode)
ANTHROPIC_API_KEY: Optional[str] = Field(
    default=None,
    description="Anthropic API key for LLM calls"
)

class Settings:
    """Settings class for configuration."""
    
    def __init__(self):
        self.PROJECT_ROOT = PROJECT_ROOT
        self.DATA_ROOT = DATA_ROOT
        self.WORKFORCE_ROOT = WORKFORCE_ROOT
        self.EPIC_DIR = EPIC_DIR
        self.EPICS_ROOT = EPICS_ROOT
        self.LOGS_ROOT = LOGS_ROOT
        self.CANON_DIR = CANON_DIR
        self.OUTPUT_DIR = OUTPUT_DIR
        self.TESTS_ROOT = TESTS_ROOT
        self.DOCUMENT_DIR = DOCUMENT_DIR
        self.GUIDES_DIR = GUIDES_DIR
        # --- DATABASE (NEW) ---
        self.DB_PATH = DB_PATH
        self.DATABASE_URL = DATABASE_URL
        self.DATA_DRIVEN_ORCHESTRATION = DATA_DRIVEN_ORCHESTRATION
        self.ANTHROPIC_API_KEY = ANTHROPIC_API_KEY
            # --- NEW ---
        # The unified root for all Workbench/Workforce data.
        # roles.py and the orchestration layer will use this.
        self.workbench_data_root = self.PROJECT_ROOT
        # --- API CONFIGURATION (ADD THESE) ---
        self.API_HOST = API_HOST
        self.API_PORT = API_PORT
        self.API_KEYS = API_KEYS
        self.ALLOW_RESET_IN_CRITICAL_PHASES = ALLOW_RESET_IN_CRITICAL_PHASES
        self.MAX_REQUEST_BODY_SIZE = MAX_REQUEST_BODY_SIZE

# Global settings instance
settings = Settings()


# Backwards compatibility function
def epic_dir(epic_id: str) -> Path:
    """Get epic directory path for given epic ID."""
    return EPICS_ROOT / epic_id