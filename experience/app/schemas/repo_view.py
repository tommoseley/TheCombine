"""
Pydantic schemas for Repo View endpoints.

Defines request/response models for read-only repository introspection.
"""

from pydantic import BaseModel, Field, ConfigDict


class RepoFilesResponse(BaseModel):
    """
    Response model for GET /repo/files endpoint.
    
    Attributes:
        root: The root directory that was queried (relative to project root)
        files: List of relative file paths found (relative to project root)
        truncated: True if results were truncated due to max_files limit
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "root": "app",
                    "files": [
                        "app/main.py",
                        "app/routers/repo_view.py",
                        "app/services/repo_reader.py",
                        "app/schemas/repo_view.py"
                    ],
                    "truncated": False
                }
            ]
        }
    )
    
    root: str = Field(..., description="Root directory queried")
    files: list[str] = Field(..., description="List of relative file paths (relative to project root)")
    truncated: bool = Field(..., description="True if results exceeded max_files")


class FileContentResponse(BaseModel):
    """
    Response model for GET /repo/file endpoint.
    
    Attributes:
        path: The file path that was requested (relative to project root)
        content: UTF-8 file content (may be truncated)
        truncated: True if content was truncated due to max_bytes limit
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "path": "app/main.py",
                    "content": "from fastapi import FastAPI\n\napp = FastAPI()\n",
                    "truncated": False
                }
            ]
        }
    )
    
    path: str = Field(..., description="File path relative to project root")
    content: str = Field(..., description="UTF-8 file content")
    truncated: bool = Field(..., description="True if content was truncated due to max_bytes")