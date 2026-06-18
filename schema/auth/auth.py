from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from schema.response import BaseResponse

# ==================== REQUEST SCHEMAS ====================


class RegisterAdminRequest(BaseModel):
    """Request body for registering a new admin."""

    full_name: str = Field(..., min_length=2, max_length=255, description="Admin's full name", examples=["Vivek Vishwakarma"])
    email: EmailStr = Field(..., description="Admin's email (login identifier)", examples=["admin@example.com"])
    password: str = Field(..., min_length=8, max_length=128, description="Password (min 8 characters)", examples=["SecureP@ss123"])

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Full name cannot be empty")
        return v


# ==================== RESPONSE DATA MODELS ====================


class AdminProfile(BaseModel):
    """Typed admin profile data model (never exposes password_hash)."""

    admin_id: str = Field(..., description="Unique UUID of the admin", examples=["c9636f46-1080-4729-8f88-d2acd16fcfe7"])
    full_name: str = Field(..., description="Admin's full name", examples=["Vivek Vishwakarma"])
    email: str = Field(..., description="Admin's email address", examples=["admin@example.com"])
    created_at: Optional[str] = Field(None, description="ISO 8601 account creation timestamp", examples=["2026-06-18T10:30:00"])
    last_login_at: Optional[str] = Field(None, description="ISO 8601 last login timestamp", examples=["2026-06-18T10:30:00"])


# ==================== RESPONSE SCHEMAS ====================


class AuthResponse(BaseModel):
    """Response returned after successful register or login (carries the JWT)."""

    success: bool = Field(default=True, description="Whether the request succeeded")
    message: str = Field(..., description="Result message", examples=["Login successful"])
    access_token: str = Field(..., description="JWT access token (Bearer)", examples=["eyJhbGciOiJIUzI1NiIs..."])
    token_type: str = Field(default="bearer", description="Token type", examples=["bearer"])
    admin: AdminProfile = Field(..., description="Authenticated admin profile")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Login successful",
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "admin": {
                    "admin_id": "c9636f46-1080-4729-8f88-d2acd16fcfe7",
                    "full_name": "Vivek Vishwakarma",
                    "email": "admin@example.com",
                    "created_at": "2026-06-18T10:30:00",
                    "last_login_at": "2026-06-18T10:30:00",
                },
            }
        }
    )


class LogoutResponse(BaseResponse):
    """Response returned after a successful logout (token revoked)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Logged out successfully",
            }
        }
    )
