"""
Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ==================== Auth Schemas ====================

class LoginRequest(BaseModel):
    """Login request schema."""
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    
    class Config:
        from_attributes = True


class TokenPayload(BaseModel):
    """Token payload schema."""
    id_usuario: int
    rol: str
    tiempo_expiracion: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    token: str


# ==================== User Schemas ====================

class UserBase(BaseModel):
    """Base user schema."""
    username: str = Field(..., min_length=3, max_length=100)
    email: Optional[EmailStr] = None
    role: str = Field(default="user")


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(..., min_length=6)


class UserResponse(UserBase):
    """User response schema."""
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== File Upload Schemas ====================

class FileUploadParams(BaseModel):
    """Additional parameters for file upload."""
    param1: str = Field(..., description="Primer parámetro adicional")
    param2: str = Field(..., description="Segundo parámetro adicional")


class ValidationResult(BaseModel):
    """Single validation result."""
    validation_type: str
    row_number: Optional[int] = None
    column_name: Optional[str] = None
    message: str
    severity: str = "warning"


class FileUploadResponse(BaseModel):
    """Response schema for file upload."""
    id: int
    filename: str
    original_filename: str
    s3_key: str
    s3_url: str
    file_size: int
    row_count: int
    param1: str
    param2: str
    upload_status: str
    validations: List[ValidationResult]
    created_at: datetime
    
    class Config:
        from_attributes = True


class UploadedFileResponse(BaseModel):
    """Uploaded file response schema."""
    id: int
    filename: str
    original_filename: str
    s3_key: str
    file_size: Optional[int]
    param1: Optional[str]
    param2: Optional[str]
    row_count: Optional[int]
    upload_status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Generic Schemas ====================

class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Error response schema."""
    detail: str
    error_code: Optional[str] = None
