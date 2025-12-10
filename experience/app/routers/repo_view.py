"""
Repo View router.

Provides read-only API endpoints for repository introspection.
Intended for AI Dev Orchestrator to discover project structure.
"""

from fastapi import APIRouter, HTTPException, Query
import logging

from app.schemas.repo_view import RepoFilesResponse, FileContentResponse
from app.services.repo_reader import repo_file_reader, ForbiddenPathError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/files",
    response_model=RepoFilesResponse,
    summary="List repository files (read-only)",
    description=(
        "Lists files in the repository starting from an allowed root directory. "
        "Supports glob patterns for filtering. Strictly read-only with allow-list enforcement. "
        "All paths are relative to the project root."
    ),
    tags=["repo"],
)
async def list_repo_files(
    root: str = Query(
        ...,
        description="Root directory to list files from (must be in allow-list, relative to project root)",
        examples=["app"],
    ),
    glob: str | None = Query(
        None,
        description="Optional glob pattern for filtering files",
        examples=["**/*.py"],
    ),
    max_files: int = Query(
        200,
        ge=1,
        le=1000,
        description="Maximum number of files to return",
    ),
) -> RepoFilesResponse:
    """
    List files in the repository.
    
    **Allow-list (permitted roots, relative to project root):**
    - `app` - Application code
    - `templates` - Jinja2 templates
    - `tests` - Test suite
    - `static` - Static assets
    - `pyproject.toml` - Project configuration
    - `README.md` - Project documentation
    
    **Forbidden paths:**
    - `.env`, `.git`, `__pycache__`, `secrets`, etc. (case-insensitive)
    - Binary files: `.pyc`, `.db`, images, etc.
    
    **Security:**
    - Strictly read-only (no write operations)
    - Path traversal attempts blocked
    - Intended for AI/Orchestrator introspection only
    
    **Examples:**
    - List all files in app/: `?root=app`
    - List Python files in app/routers: `?root=app&glob=routers/**/*.py`
    - List max 50 files: `?root=app&max_files=50`
    
    Args:
        root: Root directory to list from (required, relative to project root)
        glob: Optional glob pattern (e.g., "**/*.py")
        max_files: Maximum files to return (default 200, max 1000)
        
    Returns:
        RepoFilesResponse with list of files and truncation flag
        
    Raises:
        HTTPException: 403 if root is not in allow-list or path is forbidden
        HTTPException: 500 if file system error occurs
    """
    try:
        # Call service to list files
        files, truncated = repo_file_reader.list_files(
            root=root,
            glob_pattern=glob,
            max_files=max_files,
        )
        
        logger.info(
            f"Listed {len(files)} files from root '{root}' "
            f"(glob: {glob or 'none'}, truncated: {truncated})"
        )
        
        return RepoFilesResponse(
            root=root,
            files=files,
            truncated=truncated,
        )
    
    except ForbiddenPathError as e:
        logger.warning(f"Forbidden path access attempt: {e}")
        raise HTTPException(
            status_code=403,
            detail=str(e),
        )
    
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing files: {str(e)}",
        )


@router.get(
    "/file",
    response_model=FileContentResponse,
    summary="Get file content (read-only)",
    description=(
        "Reads content of a single file from the repository. "
        "Strictly read-only with allow-list enforcement. "
        "Only UTF-8 text files are supported."
    ),
    tags=["repo"],
)
async def get_repo_file(
    path: str = Query(
        ...,
        description="File path relative to project root (must be in allow-list)",
        examples=["app/main.py"],
    ),
    max_bytes: int = Query(
        16384,
        ge=1,
        le=1048576,
        description="Maximum bytes to read (default 16KB, max 1MB)",
    ),
) -> FileContentResponse:
    """
    Get content of a single file.
    
    **Allow-list (permitted roots, relative to project root):**
    - `app` - Application code
    - `templates` - Jinja2 templates
    - `tests` - Test suite
    - `static` - Static assets
    - `pyproject.toml` - Project configuration
    - `README.md` - Project documentation
    
    **Forbidden paths:**
    - `.env`, `.git`, `__pycache__`, `secrets`, etc. (case-insensitive)
    - Binary files: `.pyc`, `.db`, `.sqlite`, images, etc.
    
    **Security:**
    - Strictly read-only (no write operations)
    - Path traversal attempts blocked
    - Only UTF-8 text files supported
    - Content truncated if exceeds max_bytes
    
    **Examples:**
    - Get main.py: `?path=app/main.py`
    - Get with 8KB limit: `?path=app/main.py&max_bytes=8192`
    - Get config: `?path=pyproject.toml`
    
    Args:
        path: File path relative to project root (required)
        max_bytes: Maximum bytes to read (default 16384, max 1048576)
        
    Returns:
        FileContentResponse with file content and truncation flag
        
    Raises:
        HTTPException: 400 if file not found, is binary, or not a file
        HTTPException: 403 if path is not in allow-list or is forbidden
    """
    try:
        # Call service to read file content
        content, truncated = repo_file_reader.get_file_content(
            path=path,
            max_bytes=max_bytes,
        )
        
        logger.info(
            f"Read file '{path}' ({len(content)} bytes, truncated: {truncated})"
        )
        
        return FileContentResponse(
            path=path,
            content=content,
            truncated=truncated,
        )
    
    except ForbiddenPathError as e:
        logger.warning(f"Forbidden path access attempt: {e}")
        raise HTTPException(
            status_code=403,
            detail=str(e),
        )
    
    except FileNotFoundError as e:
        logger.warning(f"File not found: {path}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    
    except ValueError as e:
        logger.warning(f"Invalid file access: {path} - {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error reading file: {str(e)}",
        )