"""
Request/Response models for Mentor API endpoints.

These Pydantic models define the expected request payloads
for each mentor's streaming endpoint.
"""

from pydantic import BaseModel, Field


class PMRequest(BaseModel):
    """Request to PM Mentor"""
    user_query: str = Field(..., description="User's natural language request")
    project_id: str = Field(..., description="Project ID for artifact path (e.g., 'PROJ')")
    model: str = Field(default="claude-sonnet-4-20250514", description="Model to use")
    max_tokens: int = Field(default=4096, description="Maximum tokens")
    temperature: float = Field(default=0.7, description="Temperature for generation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_query": "I want to build a user authentication system with email/password login and password reset.",
                "project_id": "AUTH"
            }
        }


class ArchitectRequest(BaseModel):
    """Request to Architect Mentor"""
    epic_artifact_path: str = Field(..., description="RSP-1 path to PM epic (e.g., 'PROJ/E001')")
    model: str = Field(default="claude-sonnet-4-20250514", description="Model to use")
    max_tokens: int = Field(default=16384, description="Maximum tokens (higher for architecture)")
    temperature: float = Field(default=0.5, description="Temperature for generation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "epic_artifact_path": "AUTH/E001"
            }
        }


class PreliminaryArchitectRequest(BaseModel):
    """Request to Preliminary Architect Mentor"""
    project_id: str = Field(..., description="Project ID (e.g., 'PROJ')")
    artifact_path: str = Field(..., description="Path for output artifact (e.g., 'PROJ/ARCH/DISCOVERY')")
    model: str = Field(default="claude-sonnet-4-20250514", description="Model to use")
    max_tokens: int = Field(default=8192, description="Maximum tokens")
    temperature: float = Field(default=0.5, description="Temperature for generation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "AUTH",
                "artifact_path": "AUTH/ARCH/DISCOVERY"
            }
        }


class BARequest(BaseModel):
    """Request to BA Mentor"""
    epic_artifact_path: str = Field(..., description="RSP-1 path to Epic (e.g., 'PROJ/E001')")
    architecture_artifact_path: str = Field(
        ..., 
        description="RSP-1 path to Architecture (e.g., 'PROJ/E001' - same as epic)"
    )
    model: str = Field(default="claude-sonnet-4-20250514", description="Model to use")
    max_tokens: int = Field(default=8192, description="Maximum tokens (higher for stories)")
    temperature: float = Field(default=0.6, description="Temperature for generation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "epic_artifact_path": "AUTH/E001",
                "architecture_artifact_path": "AUTH/E001"
            }
        }


class DeveloperRequest(BaseModel):
    """Request to Developer Mentor"""
    story_artifact_path: str = Field(..., description="RSP-1 path to Story (e.g., 'PROJ/E001/S001')")
    model: str = Field(default="claude-sonnet-4-20250514", description="Model to use")
    max_tokens: int = Field(default=16384, description="Maximum tokens (very high for code)")
    temperature: float = Field(default=0.3, description="Temperature (low for deterministic code)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "story_artifact_path": "AUTH/E001/S001"
            }
        }