"""Prompt assembly implementation.

Implements ADR-041: Prompt Template Include System.

Assembly is deterministic: same inputs produce byte-identical output.

Now uses combine-config/prompts/ as the canonical source.
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from app.config.package_loader import get_package_loader, PackageNotFoundError, VersionNotFoundError


# Token patterns per ADR-041
# Workflow Token: $$SECTION_NAME (must be on own line)
WORKFLOW_TOKEN_PATTERN = re.compile(r'^(\$\$([A-Z][A-Z0-9_]*))\s*$', re.MULTILINE)

# Template Include: $$include <path> (must be on own line)
TEMPLATE_INCLUDE_PATTERN = re.compile(r'^(\$\$include\s+(.+?))\s*$', re.MULTILINE)


@dataclass(frozen=True)
class AssembledPrompt:
    """Immutable assembled prompt artifact.
    
    Represents the result of assembling a prompt template with its includes.
    The content_hash enables replay verification: same inputs must produce
    the same hash.
    
    Attributes:
        content: The fully assembled prompt text (UTF-8, LF-normalized)
        content_hash: SHA-256 hash of content for replay verification
        task_ref: Original template reference (e.g., "Clarification Questions Generator v1.0")
        includes_resolved: Map of token name to file path that was used
        assembled_at: Timestamp when assembly occurred
        correlation_id: Correlation ID for tracing through the system
    """

    content: str
    content_hash: str
    task_ref: str
    includes_resolved: Dict[str, str]
    assembled_at: datetime
    correlation_id: UUID


class PromptAssembler:
    """Assembles prompts from templates and includes.
    
    Assembly is deterministic: same inputs produce same output (byte-identical).
    
    Per ADR-041:
    - Workflow Tokens ($$SECTION_NAME) resolve from workflow includes map
    - Template Includes ($$include <path>) resolve from file system
    - All files loaded as UTF-8, CRLF normalized to LF
    - SHA-256 hash computed on final canonicalized content
    
    Usage:
        assembler = PromptAssembler()
        result = assembler.assemble(
            task_ref="Clarification Questions Generator v1.0",
            includes={"PGC_CONTEXT": "combine-config/prompts/pgc/project_discovery.v1/releases/1.0.0/pgc.prompt.txt"},
            correlation_id=uuid4()
        )
    """

    def __init__(self, template_root: Optional[str] = None):
        """Initialize the assembler.

        Args:
            template_root: Directory containing task prompt templates.
                          Defaults to combine-config/prompts (via PackageLoader).
        """
        self._loader = get_package_loader()
        self._template_root = template_root or str(self._loader.config_path / "prompts")

    def assemble(
        self,
        task_ref: str,
        includes: Dict[str, str],
        correlation_id: UUID,
    ) -> AssembledPrompt:
        """Assemble a prompt from template and includes.
        
        Args:
            task_ref: Template reference (filename without .txt extension)
            includes: Map of token name to include file path
            correlation_id: Correlation ID for tracing
            
        Returns:
            AssembledPrompt with content, hash, and metadata
            
        Raises:
            UnresolvedTokenError: If any Workflow Token cannot be resolved
            IncludeNotFoundError: If referenced file doesn't exist
            NestedTokenError: If include file contains tokens
            EncodingError: If file is not valid UTF-8
        """
        # 1. Load template
        template = self._load_template(task_ref)

        # 2. Resolve Workflow Tokens (from includes map)
        resolved = self._resolve_workflow_tokens(template, includes)

        # 3. Resolve Template Includes (from file system)
        resolved = self._resolve_template_includes(resolved)

        # 4. Validate no unresolved tokens remain
        self._validate_no_unresolved_tokens(resolved)

        # 5. Normalize whitespace (collapse 3+ consecutive newlines to 2)
        resolved = re.sub(r"\n{3,}", "\n\n", resolved).strip()

        # 6. Compute SHA-256 hash on canonical UTF-8 bytes
        content_hash = hashlib.sha256(resolved.encode("utf-8")).hexdigest()

        # 7. Return immutable result
        return AssembledPrompt(
            content=resolved,
            content_hash=content_hash,
            task_ref=task_ref,
            includes_resolved=dict(includes),  # Defensive copy
            assembled_at=datetime.utcnow(),
            correlation_id=correlation_id,
        )

    def _scan_workflow_tokens(self, content: str) -> list[tuple[str, str]]:
        """Scan content for Workflow Tokens ($$SECTION_NAME).
        
        Args:
            content: Template or intermediate content to scan
            
        Returns:
            List of (full_match, token_name) tuples in lexical order.
            Example: [("$$PGC_CONTEXT", "PGC_CONTEXT"), ("$$OUTPUT_SCHEMA", "OUTPUT_SCHEMA")]
        """
        matches = WORKFLOW_TOKEN_PATTERN.findall(content)
        return matches

    def _scan_template_includes(self, content: str) -> list[tuple[str, str]]:
        """Scan content for Template Includes ($$include <path>).
        
        Args:
            content: Template or intermediate content to scan
            
        Returns:
            List of (full_match, path) tuples in lexical order.
            Example: [("$$include seed/shared/rules.txt", "seed/shared/rules.txt")]
        """
        matches = TEMPLATE_INCLUDE_PATTERN.findall(content)
        return matches

    def _has_tokens(self, content: str) -> bool:
        """Check if content contains any tokens.
        
        Used to detect nested tokens in includes (which is prohibited).
        
        Args:
            content: Content to check
            
        Returns:
            True if content contains any Workflow Tokens or Template Includes
        """
        return bool(
            WORKFLOW_TOKEN_PATTERN.search(content)
            or TEMPLATE_INCLUDE_PATTERN.search(content)
        )

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to repository root.

        Args:
            path: Relative path. Supports both old and new formats:
                - Old: "seed/prompts/pgc-contexts/project_discovery.v1.txt"
                - New: "combine-config/prompts/pgc/project_discovery.v1/releases/1.0.0/pgc.prompt.txt"

        Returns:
            Resolved Path object
        """
        # If it's a seed/prompts path, try to redirect to combine-config
        if path.startswith("seed/prompts/"):
            # Map old paths to new locations
            new_path = path.replace("seed/prompts/", str(self._loader.config_path / "prompts") + "/")
            # Handle pgc-contexts -> pgc
            new_path = new_path.replace("/pgc-contexts/", "/pgc/")
            # If a direct file path, convert to versioned path
            # e.g., "pgc/project_discovery.v1.txt" -> "pgc/project_discovery.v1/releases/1.0.0/pgc.prompt.txt"
            p = Path(new_path)
            if p.suffix == ".txt" and not "releases" in str(p):
                # Try to find the release directory
                stem = p.stem
                parent = p.parent
                versioned_path = parent / stem / "releases" / "1.0.0" / "pgc.prompt.txt"
                if versioned_path.exists():
                    return versioned_path
            return Path(new_path)

        # For now, resolve relative to current working directory
        # In production, this would be relative to a configured repo root
        return Path(path)

    def _load_file(self, path: str) -> str:
        """Load file with canonical encoding.
        
        Per ADR-041:
        - UTF-8 decoding (raises EncodingError if invalid)
        - CRLF -> LF normalization
        - No BOM handling needed (UTF-8 without BOM required)
        
        Args:
            path: Path to file (relative to repo root)
            
        Returns:
            File content with normalized line endings
            
        Raises:
            IncludeNotFoundError: If file doesn't exist
            EncodingError: If file is not valid UTF-8
        """
        from app.domain.prompt.errors import IncludeNotFoundError, EncodingError

        full_path = self._resolve_path(path)

        if not full_path.exists():
            raise IncludeNotFoundError(path)

        try:
            raw_bytes = full_path.read_bytes()
            content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise EncodingError(path)

        # Canonical newline normalization: CRLF -> LF, CR -> LF
        content = content.replace("\r\n", "\n").replace("\r", "\n")

        # Auto-minify JSON files (saves tokens, structure preserved)
        if path.endswith(".json"):
            try:
                import json
                parsed = json.loads(content)
                content = json.dumps(parsed, separators=(",", ":"))
            except json.JSONDecodeError:
                pass  # Not valid JSON, include as-is

        return content

    def _load_template(self, task_ref: str) -> str:
        """Load a task prompt template.

        Args:
            task_ref: Template reference. Supports formats:
                - Legacy: "Clarification Questions Generator v1.0"
                - New: "clarification_questions_generator" (uses active release)
                - Prefixed: "tasks/Clarification Questions Generator v1.0"

        Returns:
            Template content with normalized line endings

        Raises:
            IncludeNotFoundError: If template doesn't exist
            EncodingError: If template is not valid UTF-8
        """
        from app.domain.prompt.errors import IncludeNotFoundError

        # Strip tasks/ prefix if present
        if task_ref.startswith("tasks/"):
            task_ref = task_ref[6:]

        # Try to load via PackageLoader first (new versioned structure)
        task_id, version = self._parse_legacy_name(task_ref)
        try:
            task = self._loader.get_task(task_id, version)
            content = task.content
            # Canonical newline normalization
            content = content.replace("\r\n", "\n").replace("\r", "\n")
            return content
        except (PackageNotFoundError, VersionNotFoundError):
            pass

        # Fall back to legacy file path
        template_path = f"{self._template_root}/{task_ref}.txt"
        try:
            return self._load_file(template_path)
        except Exception:
            raise IncludeNotFoundError(
                f"Task prompt '{task_ref}' not found (tried: {task_id} and {template_path})"
            )

    def _parse_legacy_name(self, name: str) -> tuple[str, Optional[str]]:
        """Parse a legacy prompt name into (id, version).

        Examples:
            "Clarification Questions Generator v1.0" -> ("clarification_questions_generator", "1.0.0")
            "clarification_questions_generator" -> ("clarification_questions_generator", None)
        """
        # Already in new format (snake_case without version)
        if re.match(r'^[a-z][a-z0-9_]*$', name):
            return name, None

        # Extract version from end (e.g., "1.0", "v1.4")
        version_match = re.search(r'\s*v?(\d+\.\d+)$', name, re.IGNORECASE)
        if version_match:
            version = version_match.group(1) + ".0"  # Convert 1.0 to 1.0.0
            name = name[:version_match.start()]
        else:
            version = None

        # Convert to snake_case
        name_id = name.lower().strip().replace(' ', '_').replace('-', '_')
        name_id = re.sub(r'_+', '_', name_id).strip('_')

        return name_id, version

    def _resolve_workflow_tokens(self, content: str, includes: dict[str, str]) -> str:
        """Resolve $$SECTION_NAME tokens from workflow includes map.
        
        Process in lexical order. Fail on first unresolved token.
        
        Args:
            content: Template content with tokens
            includes: Map of token name to include file path
            
        Returns:
            Content with all Workflow Tokens resolved
            
        Raises:
            UnresolvedTokenError: If token not in includes map
            IncludeNotFoundError: If include file doesn't exist
            NestedTokenError: If include contains tokens
            EncodingError: If include is not valid UTF-8
        """
        from app.domain.prompt.errors import UnresolvedTokenError, NestedTokenError

        tokens = self._scan_workflow_tokens(content)

        for full_match, token_name in tokens:
            if token_name not in includes:
                raise UnresolvedTokenError(token_name)

            include_path = includes[token_name]
            include_content = self._load_file(include_path).strip()

            # Check for nested tokens (prohibited per ADR-041)
            if self._has_tokens(include_content):
                nested = self._scan_workflow_tokens(include_content) or self._scan_template_includes(include_content)
                nested_token = nested[0][1] if nested else "UNKNOWN"
                raise NestedTokenError(include_path, nested_token)

            # Replace first occurrence only (in case of duplicates)
            content = content.replace(full_match, include_content, 1)

        return content

    def _resolve_template_includes(self, content: str) -> str:
        """Resolve $$include <path> tokens from file system.
        
        Process in lexical order. Fail on first missing file.
        
        Args:
            content: Content with Template Include tokens
            
        Returns:
            Content with all Template Includes resolved
            
        Raises:
            IncludeNotFoundError: If include file doesn't exist
            NestedTokenError: If include contains tokens
            EncodingError: If include is not valid UTF-8
        """
        from app.domain.prompt.errors import NestedTokenError

        includes = self._scan_template_includes(content)

        for full_match, path in includes:
            path = path.strip()
            include_content = self._load_file(path).strip()

            # Check for nested tokens (prohibited per ADR-041)
            if self._has_tokens(include_content):
                nested = self._scan_workflow_tokens(include_content) or self._scan_template_includes(include_content)
                nested_token = nested[0][1] if nested else "UNKNOWN"
                raise NestedTokenError(path, nested_token)

            # Replace first occurrence only
            content = content.replace(full_match, include_content, 1)

        return content

    def _validate_no_unresolved_tokens(self, content: str) -> None:
        """Validate that no tokens remain after resolution.
        
        Safety check for typos or missing includes.
        
        Args:
            content: Fully resolved content
            
        Raises:
            UnresolvedTokenError: If any tokens remain
        """
        from app.domain.prompt.errors import UnresolvedTokenError

        workflow_tokens = self._scan_workflow_tokens(content)
        if workflow_tokens:
            raise UnresolvedTokenError(workflow_tokens[0][1])

        template_includes = self._scan_template_includes(content)
        if template_includes:
            # Extract path from template include for error message
            raise UnresolvedTokenError(f"include {template_includes[0][1]}")