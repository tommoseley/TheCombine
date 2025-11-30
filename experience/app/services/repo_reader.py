"""
Repository file reader service.

Provides read-only file system introspection for AI Dev Orchestrator.
Enforces strict allow-list and excludes binary files.

This service is exclusively for AI/Orchestrator introspection and must remain
strictly read-only. No write, delete, or mutate operations are permitted.
"""

from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ForbiddenPathError(Exception):
    """Raised when attempting to access a path outside the allow-list."""
    pass


class RepoFileReader:
    """
    Service for reading repository file structure and content.
    
    Enforces security constraints:
    - Only allows access to explicit allow-listed roots
    - Blocks .env, .git, __pycache__, secrets, etc. (case-insensitive)
    - Filters out binary files (.pyc, .db, .sqlite, images, etc.)
    
    Project root is the experience/ directory (derived from file location).
    All allowed roots are relative to project root.
    """
    
    # Allowed root directories and files (relative to project root: experience/)
    # Per REPO-100 canonical story requirements
    ALLOWED_ROOTS: set[str] = {
        "app",
        "templates",
        "tests",
        "static",
        "pyproject.toml",
        "README.md",
    }
    
    # Forbidden path components (case-insensitive matching)
    FORBIDDEN_NAMES: set[str] = {
        ".env",
        ".git",
        "__pycache__",
        "secrets",
        ".venv",
        "venv",
        "node_modules",
    }
    
    # Binary file extensions to exclude
    BINARY_EXTENSIONS: set[str] = {
        ".pyc",
        ".pyo",
        ".db",
        ".sqlite",
        ".sqlite3",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".ico",
        ".pdf",
        ".zip",
        ".tar",
        ".gz",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
    }
    
    def __init__(self, project_root: Path | None = None):
        """
        Initialize RepoFileReader.
        
        Args:
            project_root: Root directory of the project (experience/).
                         Defaults to deriving from this file's location.
        """
        # Derive project root from file location: experience/app/services/repo_reader.py
        # Go up 2 levels: services/ -> app/ -> experience/
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        logger.info(f"RepoFileReader initialized with project_root: {self.project_root}")
    
    def _is_allowed_root(self, root: str) -> bool:
        """
        Check if root is in the allow-list.
        
        Args:
            root: Root path to validate (relative to project root)
            
        Returns:
            True if root is allowed, False otherwise
        """
        return root in self.ALLOWED_ROOTS
    
    def _is_forbidden_path(self, path: Path) -> bool:
        """
        Check if path contains forbidden components (case-insensitive).
        
        Args:
            path: Path to check
            
        Returns:
            True if path contains forbidden components, False otherwise
        """
        # Case-insensitive check for forbidden path parts
        path_parts_lower = {p.lower() for p in path.parts}
        return bool(path_parts_lower & self.FORBIDDEN_NAMES)
    
    def _is_binary_file(self, path: Path) -> bool:
        """
        Check if file is a binary file based on extension.
        
        Args:
            path: File path to check
            
        Returns:
            True if file is binary, False otherwise
        """
        return path.suffix.lower() in self.BINARY_EXTENSIONS
    
    def _extract_root_from_path(self, path_obj: Path) -> str:
        """
        Extract root from path, handling both single files and directories.
        
        Args:
            path_obj: Path object to extract root from
            
        Returns:
            Root component as string
        """
        path_str = str(path_obj)
        
        # Check if path itself is an allowed root (e.g., pyproject.toml)
        if path_str in self.ALLOWED_ROOTS:
            return path_str
        
        # Otherwise, extract first component
        if not path_obj.parts:
            return ""
        
        return path_obj.parts[0]
    
    def list_files(
        self,
        root: str,
        glob_pattern: str | None = None,
        max_files: int = 200,
    ) -> tuple[list[str], bool]:
        """
        List files in the repository starting from root.
        
        This method is strictly read-only and intended for AI/Orchestrator introspection.
        No write, delete, or mutate operations are performed.
        
        Args:
            root: Root directory to start listing from (must be in allow-list, relative to project root)
            glob_pattern: Optional glob pattern for filtering (e.g., "**/*.py")
            max_files: Maximum number of files to return
            
        Returns:
            Tuple of (file_list, truncated) where:
                - file_list: List of relative file paths (strings) relative to project root
                - truncated: True if results exceeded max_files
                
        Raises:
            ForbiddenPathError: If root is not in allow-list or path is forbidden
        """
        # Validate root is in allow-list
        if not self._is_allowed_root(root):
            logger.warning(f"Attempted access to forbidden root: {root}")
            raise ForbiddenPathError(
                f"Root '{root}' is not in allow-list. "
                f"Allowed roots: {', '.join(sorted(self.ALLOWED_ROOTS))}"
            )
        
        # Resolve root path relative to project root (experience/)
        root_path = self.project_root / root
        
        # Ensure root_path stays within project_root (prevent path traversal attacks)
        try:
            root_path = root_path.resolve()
            root_path.relative_to(self.project_root.resolve())
        except ValueError:
            logger.warning(f"Path traversal attempt detected: {root}")
            raise ForbiddenPathError(f"Path traversal not allowed: {root}")
        
        # Check if root path exists
        if not root_path.exists():
            logger.warning(f"Root path does not exist: {root_path}")
            return [], False
        
        # Handle single-file roots (e.g., pyproject.toml, README.md)
        if root_path.is_file():
            if self._is_binary_file(root_path):
                logger.info(f"Single file root is binary, excluding: {root}")
                return [], False
            # Return the root as-is (relative to project root)
            return [root], False
        
        # Collect files from directory
        pattern = glob_pattern or "**/*"
        collected_files: list[str] = []
        truncated = False
        
        try:
            for path in root_path.glob(pattern):
                # Skip if we've hit the limit
                if len(collected_files) >= max_files:
                    truncated = True
                    logger.info(f"Hit max_files limit ({max_files}), truncating results")
                    break
                
                # Skip directories
                if not path.is_file():
                    continue
                
                # Skip forbidden paths (case-insensitive check)
                if self._is_forbidden_path(path):
                    logger.debug(f"Skipping forbidden path: {path}")
                    continue
                
                # Skip binary files
                if self._is_binary_file(path):
                    logger.debug(f"Skipping binary file: {path}")
                    continue
                
                # Get relative path from project root
                try:
                    relative_path = path.relative_to(self.project_root)
                    collected_files.append(str(relative_path))
                except ValueError:
                    # Path is outside project root (should not happen due to earlier check)
                    logger.warning(f"Path outside project root: {path}")
                    continue
        
        except Exception as e:
            logger.error(f"Error listing files in {root_path}: {e}")
            raise
        
        logger.info(
            f"Listed {len(collected_files)} files from root '{root}' "
            f"(pattern: {pattern}, truncated: {truncated})"
        )
        
        return collected_files, truncated
    
    def get_file_content(
        self,
        path: str,
        max_bytes: int = 16384,
    ) -> tuple[str, bool]:
        """
        Read file content from repository.
        
        This method is strictly read-only and intended for AI/Orchestrator introspection.
        Enforces same security constraints as list_files.
        
        Args:
            path: File path relative to project root (must be in allow-list)
            max_bytes: Maximum bytes to read (default 16384)
            
        Returns:
            Tuple of (content, truncated) where:
                - content: UTF-8 file content (truncated if needed)
                - truncated: True if file was larger than max_bytes
                
        Raises:
            ForbiddenPathError: If path is not in allow-list or is forbidden
            FileNotFoundError: If file does not exist
            ValueError: If file is binary or not a regular file
        """
        # Validate and normalize path
        path_obj = Path(path)
        
        # Determine root from path
        root = self._extract_root_from_path(path_obj)
        
        # Validate root is in allow-list
        if not self._is_allowed_root(root):
            logger.warning(f"Attempted access to forbidden root: {root}")
            raise ForbiddenPathError(
                f"Root '{root}' is not in allow-list. "
                f"Allowed roots: {', '.join(sorted(self.ALLOWED_ROOTS))}"
            )
        
        # Resolve full path and validate it's within project root
        full_path = self.project_root / path
        
        try:
            full_path = full_path.resolve()
            full_path.relative_to(self.project_root.resolve())
        except ValueError:
            logger.warning(f"Path traversal attempt detected: {path}")
            raise ForbiddenPathError(f"Path traversal not allowed: {path}")
        
        # Validate file exists and is a regular file
        if not full_path.exists():
            logger.warning(f"File not found: {path}")
            raise FileNotFoundError(f"File not found: {path}")
        
        if not full_path.is_file():
            raise ValueError(f"Path is not a file: {path}")
        
        # Security checks
        if self._is_forbidden_path(full_path):
            logger.warning(f"Access to forbidden path attempted: {path}")
            raise ForbiddenPathError(f"Access forbidden: {path}")
        
        if self._is_binary_file(full_path):
            raise ValueError("File is not a text file")
        
        # Read content with memory-efficient truncation
        try:
            with full_path.open('r', encoding='utf-8') as f:
                content = f.read(max_bytes)
                # Check if there's more content without reading it all
                remaining = f.read(1)
                truncated = len(remaining) > 0
            
            logger.info(f"Read file '{path}' ({len(content)} bytes, truncated: {truncated})")
            return content, truncated
            
        except UnicodeDecodeError as e:
            logger.warning(f"Non-UTF-8 file detected: {path}")
            raise ValueError("File is not a text file")


# Singleton instance for dependency injection
repo_file_reader = RepoFileReader()