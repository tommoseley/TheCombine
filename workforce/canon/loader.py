# workforce/canon/loader.py

"""Canon file loading and parsing."""

import re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

from workforce.utils.errors import (
    CanonFileNotFoundError,
    CanonParseError,
    CanonValidationError
)
from workforce.utils.logging import log_debug, log_info


@dataclass
class SemanticVersion:
    """Semantic version (major.minor)."""
    major: int
    minor: int
    
    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, SemanticVersion):
            return False
        return self.major == other.major and self.minor == other.minor


@dataclass
class CanonDocument:
    """Parsed canon document."""
    version: SemanticVersion
    content: str
    loaded_at: datetime
    file_path: Path


class CanonLoader:
    """Load canonical pipeline definition from file."""
    
    VERSION_PATTERN = re.compile(r'^PIPELINE_FLOW_VERSION=(\d+)\.(\d+)\s*$')
    MAX_FILE_SIZE = 1024 * 1024  # 1MB
    
    # Required sections matching actual pipeline_flow.md structure
    REQUIRED_SECTIONS = [
        "Overview",
        "Phase Sequence",
        "Phase Definitions",
        "PM Phase",
        "Architect Phase",
        "BA Phase",
        "Developer Phase",
        "QA Phase",
        "Commit Phase",
        "Error Handling",
        "Behavioral Rules",
        "Canonical Summary Diagram",
        "Canon Enforcement"
    ]
    
    def load_canon(self, filepath: Path) -> CanonDocument:
        """
        Load canon file and parse version + content.
        
        Args:
            filepath: Path to canon file
            
        Returns:
            CanonDocument with version and content
            
        Raises:
            CanonFileNotFoundError: File doesn't exist
            CanonParseError: Invalid format or version
            CanonValidationError: File too large or corrupted
        """
        if not filepath.exists():
            raise CanonFileNotFoundError(f"Canon file not found: {filepath}")
        
        # Check file size
        file_size = filepath.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            raise CanonValidationError(
                f"Canon file too large: {file_size} bytes (max {self.MAX_FILE_SIZE})"
            )
        
        # Read file content
        try:
            content = filepath.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # Try ASCII fallback
            try:
                content = filepath.read_text(encoding='ascii')
            except Exception as e:
                raise CanonValidationError(f"Cannot decode canon file: {e}")
        
        # Parse version from first non-empty line
        version = self._parse_version(content)
        
        # Validate structure
        self._validate_structure(content)
        
        log_info(f"Canon loaded successfully: version={version}, size={file_size} bytes")
        
        return CanonDocument(
            version=version,
            content=content,
            loaded_at=datetime.now(),
            file_path=filepath
        )
    
    def _parse_version(self, content: str) -> SemanticVersion:
        """Extract version from first non-empty line."""
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue  # Skip empty lines
            
            match = self.VERSION_PATTERN.match(line)
            if match:
                major = int(match.group(1))
                minor = int(match.group(2))
                return SemanticVersion(major, minor)
            else:
                raise CanonParseError(
                    f"Invalid version format on first non-empty line: {line}\n"
                    f"Expected format: PIPELINE_FLOW_VERSION=X.X"
                )
        
        raise CanonParseError("No version line found in canon file")
    
    def _validate_structure(self, content: str) -> None:
        """
        Validate canon file has required sections.
        
        Checks for presence of all sections defined in Pipeline Flow v1.
        Section names must match headings in actual pipeline_flow.md.
        
        Raises:
            CanonValidationError: If required section is missing
        """
        missing_sections = []
        
        for section in self.REQUIRED_SECTIONS:
            # Check for section heading (case-insensitive)
            # Pattern allows for optional numbers and periods before section name
            # Matches: "## Overview", "## 1. Overview", "### 3.1 PM Phase", etc.
            pattern = rf'#{{1,3}}\s+(?:\d+\.?\d*\.?\s*)?{re.escape(section)}'
            if not re.search(pattern, content, re.IGNORECASE):
                missing_sections.append(section)
        
        if missing_sections:
            raise CanonValidationError(
                f"Canon validation failed. Missing required sections:\n" +
                "\n".join(f"  - {section}" for section in missing_sections) +
                f"\n\nCanon must include all sections defined in Pipeline Flow v1."
            )
        
        log_debug(f"Canon structure validated: all {len(self.REQUIRED_SECTIONS)} required sections present")