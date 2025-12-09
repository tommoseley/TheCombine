"""
Pydantic schemas for authentication endpoints.

Defines request/response models for:
- Magic link authentication (AUTH-100)
- Current user information (AUTH-101)
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# Magic Link Schemas (AUTH-100)
class MagicLinkRequest(BaseModel):
    """Request schema for magic link generation."""
    email: EmailStr = Field(..., description="User's email address")


class MagicLinkResponse(BaseModel):
    """Response schema for magic link request."""
    message: str = Field(..., description="Success message")
    email: EmailStr = Field(..., description="Email where link was sent")


class ValidateTokenRequest(BaseModel):
    """Request schema for magic link token validation."""
    token: str = Field(..., description="Magic link token to validate")


class ValidateTokenResponse(BaseModel):
    """Response schema for successful token validation."""
    session_id: str = Field(..., description="Created session identifier")
    email: EmailStr = Field(..., description="User's email address")
    expires_at: datetime = Field(..., description="Session expiration timestamp")


# User Information Schemas (AUTH-101)
class UserResponse(BaseModel):
    """
    Response schema for current user information.
    
    Used by the /auth/me endpoint to return authenticated user details.
    """
    id: int = Field(..., description="User's unique identifier")
    email: EmailStr = Field(..., description="User's email address")
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = ConfigDict(
        """Pydantic configuration."""
        from_attributes = True  # Allows creation from ORM models
        json_schema_extra = {
            "example": {
                "id": 123,
                "email": "user@example.com",
                "created_at": "2024-01-15T10:30:00Z"
            }
        }
    )