"""
Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


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


# ==================== Document Analysis Schemas ====================

class DocumentTypeEnum(str, Enum):
    """Document classification types."""
    FACTURA = "factura"
    INFORMACION = "informacion"
    PENDIENTE = "pendiente"


class SentimentEnum(str, Enum):
    """Sentiment analysis types."""
    POSITIVE = "positivo"
    NEGATIVE = "negativo"
    NEUTRAL = "neutral"


class EventTypeEnum(str, Enum):
    """Event types for historical logging."""
    DOCUMENT_UPLOAD = "subida_documento"
    AI_ANALYSIS = "analisis_ia"
    USER_INTERACTION = "interaccion_usuario"
    SYSTEM = "sistema"


# Invoice Product Schema
class InvoiceProduct(BaseModel):
    """Schema for a single product in an invoice."""
    quantity: Optional[float] = None
    name: Optional[str] = None
    unit_price: Optional[float] = None
    total: Optional[float] = None


# Invoice Data Schemas
class InvoiceDataBase(BaseModel):
    """Base schema for invoice data."""
    client_name: Optional[str] = None
    client_address: Optional[str] = None
    provider_name: Optional[str] = None
    provider_address: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    invoice_total: Optional[float] = None
    currency: str = "MXN"
    products: List[InvoiceProduct] = []


class InvoiceDataResponse(InvoiceDataBase):
    """Response schema for invoice data."""
    id: int
    document_id: int
    raw_text: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# Info Data Schemas
class InfoDataBase(BaseModel):
    """Base schema for information document data."""
    description: Optional[str] = None
    summary: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    key_topics: List[str] = []


class InfoDataResponse(InfoDataBase):
    """Response schema for information document data."""
    id: int
    document_id: int
    raw_text: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# Document Schemas
class DocumentBase(BaseModel):
    """Base schema for document."""
    original_filename: str
    document_type: DocumentTypeEnum = DocumentTypeEnum.PENDIENTE


class DocumentCreate(DocumentBase):
    """Schema for creating a document."""
    pass


class DocumentResponse(BaseModel):
    """Response schema for document."""
    id: int
    filename: str
    original_filename: str
    s3_key: str
    s3_url: str
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    document_type: str
    analysis_status: str
    analysis_error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Extracted data (depending on document type)
    invoice_data: Optional[InvoiceDataBase] = None
    info_data: Optional[InfoDataBase] = None
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Response schema for listing documents."""
    id: int
    filename: str
    original_filename: str
    document_type: str
    analysis_status: str
    file_size: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class DocumentAnalysisResult(BaseModel):
    """Schema for document analysis result."""
    document_type: DocumentTypeEnum
    confidence: float
    invoice_data: Optional[InvoiceDataBase] = None
    info_data: Optional[InfoDataBase] = None
    raw_text: str


# ==================== Event Log Schemas ====================

class EventLogBase(BaseModel):
    """Base schema for event log."""
    event_type: EventTypeEnum
    description: str
    metadata: Optional[dict] = None


class EventLogCreate(EventLogBase):
    """Schema for creating an event log."""
    document_id: Optional[int] = None
    user_id: Optional[int] = None


class EventLogResponse(BaseModel):
    """Response schema for event log."""
    id: int
    event_type: str
    description: str
    document_id: Optional[int] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class EventLogListResponse(BaseModel):
    """Response schema for listing event logs."""
    total: int
    page: int
    page_size: int
    events: List[EventLogResponse]


class EventLogFilter(BaseModel):
    """Filter schema for event logs."""
    event_type: Optional[EventTypeEnum] = None
    description_search: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    user_id: Optional[int] = None


# ==================== Export Schema ====================

class ExportResponse(BaseModel):
    """Response schema for export operations."""
    filename: str
    content_type: str
    download_url: str
