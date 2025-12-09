# workforce/canon/drift_detector.py

"""Canon version drift detection."""

from pathlib import Path
from typing import Optional

from workforce.canon.loader import CanonLoader, SemanticVersion
from workforce.canon.path_resolver import resolve_canon_path
from workforce.utils.logging import log_info, log_warning


class DriftDetector:
    """Detect canon version drift."""
    
    def __init__(self):
        self.loader = CanonLoader()
    
    def check_for_drift(self, current_version: SemanticVersion) -> Optional[SemanticVersion]:
        """
        Check if canon file version differs from in-memory version.
        
        Args:
            current_version: Current in-memory version
            
        Returns:
            New version if drift detected, None otherwise
        """
        try:
            canon_path = resolve_canon_path()
            
            # Read first line to get version
            with canon_path.open('r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        match = CanonLoader.VERSION_PATTERN.match(line)
                        if match:
                            disk_version = SemanticVersion(
                                int(match.group(1)),
                                int(match.group(2))
                            )
                            
                            if disk_version != current_version:
                                log_info(
                                    f"Canon version drift detected: "
                                    f"{current_version} → {disk_version}"
                                )
                                return disk_version
                            return None
            
            log_warning("No version line found in canon file")
            return None
        
        except Exception as e:
            log_warning(f"Error checking for drift: {e}")
            return None