"""
Database models for the application.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


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
