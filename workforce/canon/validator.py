# workforce/canon/validator.py

"""Version validation and comparison."""

import re
from enum import Enum

from workforce.canon.loader import SemanticVersion
from workforce.utils.logging import log_warning, log_error


class VersionComparison(Enum):
    """Version comparison results."""
    SAME = "same"
    UPGRADE = "upgrade"
    DOWNGRADE = "downgrade"


class VersionValidator:
    """Validate version format and detect changes."""
    
    VERSION_PATTERN = re.compile(r'PIPELINE_FLOW_VERSION=(\d+)\.(\d+)')
    
    def compare_versions(self, v1: SemanticVersion, v2: SemanticVersion) -> VersionComparison:
        """
        Compare two versions.
        
        Args:
            v1: First version
            v2: Second version
        
        Returns:
            SAME: Versions identical
            UPGRADE: v2 > v1 (major or minor increased)
            DOWNGRADE: v2 < v1 (major or minor decreased)
        """
        if v1 == v2:
            return VersionComparison.SAME
        
        if v2.major > v1.major:
            return VersionComparison.UPGRADE
        elif v2.major < v1.major:
            return VersionComparison.DOWNGRADE
        
        # Same major version, compare minor
        if v2.minor > v1.minor:
            return VersionComparison.UPGRADE
        else:
            return VersionComparison.DOWNGRADE
    
    def validate_llm_version(self, llm_response: str, 
                            expected_version: SemanticVersion) -> bool:
        """
        Validate LLM reports correct version.
        
        Parses PIPELINE_FLOW_VERSION=X.X from LLM response.
        
        Args:
            llm_response: Text response from LLM
            expected_version: Expected version
            
        Returns:
            True if LLM reported correct version, False otherwise
        """
        match = self.VERSION_PATTERN.search(llm_response)
        
        if not match:
            log_warning("LLM did not report PIPELINE_FLOW_VERSION")
            return False
        
        reported_major = int(match.group(1))
        reported_minor = int(match.group(2))
        reported_version = SemanticVersion(reported_major, reported_minor)
        
        if reported_version != expected_version:
            log_error(
                f"Version mismatch: LLM reported {reported_version}, "
                f"expected {expected_version}"
            )
            return False
        
        return True