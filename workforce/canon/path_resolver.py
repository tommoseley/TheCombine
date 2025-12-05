# workforce/canon/path_resolver.py

"""Canon file path resolution."""

import os
from pathlib import Path
from typing import Optional

from workforce.utils.errors import CanonFileNotFoundError
from workforce.utils.logging import log_info

# Import settings
try:
    from config import settings
except ImportError:
    # Fallback if config not available
    settings = None


def resolve_canon_path() -> Path:
    """
    Resolve canon file path using canonical resolution order.
    
    Resolution Order:
    1. COMBINE_CANON_PATH environment variable (if set)
    2. {WORKFORCE_ROOT}/canon/pipeline_flow.md (canonical location)
    3. Fail with clear error
    
    Returns:
        Path: Absolute path to canon file
        
    Raises:
        CanonFileNotFoundError: If file doesn't exist at resolved path
    """
    # Step 1: Environment variable override
    override_path = os.environ.get("COMBINE_CANON_PATH", "").strip()
    
    if override_path:
        canon_path = Path(override_path).resolve()
        
        if not canon_path.exists():
            raise CanonFileNotFoundError(
                f"Canon file not found at override path: {canon_path}\n"
                f"Environment variable COMBINE_CANON_PATH is set but file doesn't exist.\n"
                f"Either create file at this path or unset COMBINE_CANON_PATH."
            )
        
        if not canon_path.is_file():
            raise CanonFileNotFoundError(
                f"COMBINE_CANON_PATH points to directory, not file: {canon_path}"
            )
        
        log_info(f"Using canon file from COMBINE_CANON_PATH: {canon_path}")
        return canon_path
    
    # Step 2: Canonical location
    if settings is not None:
        workforce_root = settings.WORKFORCE_ROOT
    else:
        workforce_root = Path.cwd() / "workforce"
    
    canon_path = workforce_root / "canon" / "pipeline_flow.md"
    
    if not canon_path.exists():
        raise CanonFileNotFoundError(
            f"Canon file not found at canonical location: {canon_path}\n"
            f"Expected location: workforce/canon/pipeline_flow.md\n"
            f"Current WORKFORCE_ROOT: {workforce_root}\n"
            f"Either create file at canonical location or set COMBINE_CANON_PATH."
        )
    
    log_info(f"Using canon file from canonical location: {canon_path}")
    return canon_path