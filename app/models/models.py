"""
Database models for the application.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Float, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class DocumentType(str, enum.Enum):
    """Document classification types."""
    FACTURA = "factura"
    INFORMACION = "informacion"
    PENDIENTE = "pendiente"


class EventType(str, enum.Enum):
    """Event types for historical logging."""
    DOCUMENT_UPLOAD = "subida_documento"
    AI_ANALYSIS = "analisis_ia"
    USER_INTERACTION = "interaccion_usuario"
    SYSTEM = "sistema"


class SentimentType(str, enum.Enum):
    """Sentiment analysis types."""
    POSITIVE = "positivo"
    NEGATIVE = "negativo"
    NEUTRAL = "neutral"


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True)
    role = Column(String(50), nullable=False, default="user")  # user, admin, uploader
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    uploaded_files = relationship("UploadedFile", back_populates="user")
    documents = relationship("Document", back_populates="user")
    events = relationship("EventLog", back_populates="user")


class UploadedFile(Base):
    """Model to track uploaded CSV files."""
    __tablename__ = "uploaded_files"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    s3_key = Column(String(500), nullable=False)
    file_size = Column(Integer)
    content_type = Column(String(100))
    param1 = Column(String(255))  # Additional parameter 1
    param2 = Column(String(255))  # Additional parameter 2
    row_count = Column(Integer)
    upload_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="uploaded_files")
    csv_data = relationship("CSVData", back_populates="uploaded_file")
    validations = relationship("FileValidation", back_populates="uploaded_file")


class CSVData(Base):
    """Model to store processed CSV data."""
    __tablename__ = "csv_data"
    
    id = Column(Integer, primary_key=True, index=True)
    uploaded_file_id = Column(Integer, ForeignKey("uploaded_files.id"), nullable=False)
    row_number = Column(Integer, nullable=False)
    data = Column(Text, nullable=False)  # JSON string of row data
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    uploaded_file = relationship("UploadedFile", back_populates="csv_data")


class FileValidation(Base):
    """Model to store file validation results."""
    __tablename__ = "file_validations"
    
    id = Column(Integer, primary_key=True, index=True)
    uploaded_file_id = Column(Integer, ForeignKey("uploaded_files.id"), nullable=False)
    validation_type = Column(String(100), nullable=False)  # empty_value, incorrect_type, duplicate
    row_number = Column(Integer)
    column_name = Column(String(255))
    message = Column(String(500))
    severity = Column(String(50), default="warning")  # warning, error
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    uploaded_file = relationship("UploadedFile", back_populates="validations")


# ==================== Document Analysis Models ====================

class Document(Base):
    """Model to store uploaded documents for AI analysis."""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    s3_key = Column(String(500), nullable=False)
    file_size = Column(Integer)
    content_type = Column(String(100))  # application/pdf, image/jpeg, image/png
    document_type = Column(String(50), default=DocumentType.PENDIENTE.value)  # factura, informacion, pendiente
    analysis_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    analysis_error = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="documents")
    invoice_data = relationship("InvoiceData", back_populates="document", uselist=False)
    info_data = relationship("InfoData", back_populates="document", uselist=False)


class InvoiceData(Base):
    """Model to store extracted invoice data."""
    __tablename__ = "invoice_data"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, unique=True)
    
    # Client information
    client_name = Column(String(255))
    client_address = Column(Text)
    
    # Provider information
    provider_name = Column(String(255))
    provider_address = Column(Text)
    
    # Invoice details
    invoice_number = Column(String(100))
    invoice_date = Column(String(100))
    invoice_total = Column(Float)
    currency = Column(String(10), default="MXN")
    
    # Products (stored as JSON)
    products_json = Column(Text)  # JSON array of products
    
    # Raw extracted text
    raw_text = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="invoice_data")


class InfoData(Base):
    """Model to store extracted information document data."""
    __tablename__ = "info_data"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, unique=True)
    
    # Extracted information
    description = Column(Text)
    summary = Column(Text)
    sentiment = Column(String(50))  # positivo, negativo, neutral
    sentiment_score = Column(Float)
    
    # Key topics/entities
    key_topics_json = Column(Text)  # JSON array of key topics
    
    # Raw extracted text
    raw_text = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="info_data")


# ==================== Event Log Models ====================

class EventLog(Base):
    """Model to store historical events."""
    __tablename__ = "event_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(100), nullable=False)  # subida_documento, analisis_ia, interaccion_usuario, sistema
    description = Column(Text, nullable=False)
    
    # Related entities (optional)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Additional metadata (JSON)
    metadata_json = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="events")
