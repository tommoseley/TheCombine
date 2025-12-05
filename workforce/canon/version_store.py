# workforce/canon/version_store.py

"""In-memory version storage."""

from typing import Optional
from datetime import datetime
from dataclasses import dataclass

from workforce.canon.loader import SemanticVersion


@dataclass
class VersionRecord:
    """Record of a canon version."""
    version: SemanticVersion
    content_hash: str
    loaded_at: datetime


class VersionStore:
    """Store current canon version in memory."""
    
    def __init__(self):
        self._current_version: Optional[SemanticVersion] = None
        self._current_content: Optional[str] = None
        self._loaded_at: Optional[datetime] = None
    
    def update_version(self, version: SemanticVersion, content: str) -> None:
        """
        Update stored version.
        
        Args:
            version: New semantic version
            content: Canon content
        """
        self._current_version = version
        self._current_content = content
        self._loaded_at = datetime.now()
    
    def get_current_version(self) -> Optional[SemanticVersion]:
        """Get current stored version."""
        return self._current_version
    
    def get_current_content(self) -> Optional[str]:
        """Get current stored content."""
        return self._current_content
    
    def get_loaded_at(self) -> Optional[datetime]:
        """Get timestamp of last version load."""
        return self._loaded_at
    
    def is_loaded(self) -> bool:
        """Check if a version is currently loaded."""
        return self._current_version is not None