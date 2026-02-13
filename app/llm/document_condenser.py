"""Document condenser for role-aware summarization."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class CondenseConfig:
    """Configuration for document condensing."""
    max_tokens: int = 2000
    preserve_structure: bool = True
    include_metadata: bool = True


# Role-specific focus areas for condensing
ROLE_FOCUS = {
    "PM": [
        "requirements",
        "acceptance criteria",
        "business value",
        "stakeholders",
        "timeline",
        "risks",
    ],
    "BA": [
        "user stories",
        "requirements",
        "data flows",
        "business rules",
        "edge cases",
        "validation",
    ],
    "Developer": [
        "technical specifications",
        "interfaces",
        "data models",
        "algorithms",
        "dependencies",
        "implementation details",
    ],
    "QA": [
        "acceptance criteria",
        "test cases",
        "edge cases",
        "validation rules",
        "quality requirements",
        "expected behavior",
    ],
    "Architect": [
        "system design",
        "architecture",
        "interfaces",
        "integration points",
        "scalability",
        "security",
        "data flows",
    ],
}


class DocumentCondenser:
    """Condenses documents based on target role's focus areas."""
    
    def __init__(self, config: Optional[CondenseConfig] = None):
        """
        Initialize condenser.
        
        Args:
            config: Condensing configuration
        """
        self._config = config or CondenseConfig()
    
    def condense(
        self,
        content: str,
        role: str,
        document_type: Optional[str] = None,
    ) -> str:
        """
        Condense document content for a specific role.
        
        Args:
            content: Original document content
            role: Target role (PM, BA, Developer, QA, Architect)
            document_type: Optional document type hint
            
        Returns:
            Condensed content optimized for the role
        """
        # For short documents, return as-is
        if self._estimate_tokens(content) <= self._config.max_tokens:
            return content
        
        # Get role's focus areas
        focus_areas = ROLE_FOCUS.get(role, [])
        
        # Split into sections
        sections = self._split_sections(content)
        
        # If no sections found (no headers), treat whole content as one section
        if not sections:
            return self._truncate(content, self._config.max_tokens)
        
        # Score and prioritize sections
        scored = self._score_sections(sections, focus_areas)
        
        # Build condensed output within token limit
        return self._build_condensed(scored, self._config.max_tokens)
    
    def condense_multiple(
        self,
        documents: List[Dict[str, str]],
        role: str,
        total_max_tokens: int = 4000,
    ) -> List[Dict[str, str]]:
        """
        Condense multiple documents with shared token budget.
        
        Args:
            documents: List of {type, content} dicts
            role: Target role
            total_max_tokens: Total token budget for all documents
            
        Returns:
            List of condensed documents
        """
        if not documents:
            return []
        
        # Allocate tokens per document
        tokens_per_doc = total_max_tokens // len(documents)
        
        result = []
        for doc in documents:
            condensed = self.condense(
                content=doc.get("content", ""),
                role=role,
                document_type=doc.get("type"),
            )
            # Further truncate if over budget
            if self._estimate_tokens(condensed) > tokens_per_doc:
                condensed = self._truncate(condensed, tokens_per_doc)
            
            result.append({
                "type": doc.get("type", "Unknown"),
                "content": condensed,
            })
        
        return result
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough: ~4 chars per token)."""
        return len(text) // 4
    
    def _split_sections(self, content: str) -> List[Dict[str, str]]:
        """Split content into sections by headers."""
        import re
        
        sections = []
        current_header = None
        current_content = []
        
        for line in content.split("\n"):
            # Check for markdown headers
            header_match = re.match(r'^(#{1,3})\s+(.+)$', line)
            if header_match:
                # Save previous section if it has content
                if current_header is not None and current_content:
                    sections.append({
                        "header": current_header,
                        "content": "\n".join(current_content),
                    })
                current_header = header_match.group(2)
                current_content = []
            else:
                current_content.append(line)
        
        # Save last section if it has a header
        if current_header is not None and current_content:
            sections.append({
                "header": current_header,
                "content": "\n".join(current_content),
            })
        
        return sections
    
    def _score_sections(
        self, 
        sections: List[Dict[str, str]], 
        focus_areas: List[str]
    ) -> List[Dict]:
        """Score sections based on relevance to focus areas."""
        scored = []
        
        for section in sections:
            header_lower = section["header"].lower()
            content_lower = section["content"].lower()
            combined = header_lower + " " + content_lower
            
            score = 0
            for area in focus_areas:
                if area.lower() in combined:
                    score += 2 if area.lower() in header_lower else 1
            
            scored.append({
                **section,
                "score": score,
                "tokens": self._estimate_tokens(section["content"]),
            })
        
        # Sort by score descending
        return sorted(scored, key=lambda x: x["score"], reverse=True)
    
    def _build_condensed(
        self, 
        scored_sections: List[Dict], 
        max_tokens: int
    ) -> str:
        """Build condensed output from scored sections."""
        parts = []
        used_tokens = 0
        
        for section in scored_sections:
            section_tokens = section["tokens"] + 10  # Header overhead
            
            if used_tokens + section_tokens > max_tokens:
                # Try to fit partial section
                remaining = max_tokens - used_tokens
                if remaining > 100:  # Worth including partial
                    truncated = self._truncate(section["content"], remaining - 10)
                    parts.append(f"## {section['header']}\n{truncated}")
                break
            
            parts.append(f"## {section['header']}\n{section['content']}")
            used_tokens += section_tokens
        
        return "\n\n".join(parts)
    
    def _truncate(self, text: str, max_tokens: int) -> str:
        """Truncate text to approximate token limit."""
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        
        # Try to truncate at sentence boundary
        truncated = text[:max_chars]
        last_period = truncated.rfind(".")
        if last_period > max_chars * 0.7:
            return truncated[:last_period + 1] + " [truncated]"
        
        return truncated + "... [truncated]"
