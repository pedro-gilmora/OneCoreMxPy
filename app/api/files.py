"""
File upload API endpoints.
"""
import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import require_role, get_current_user
from app.models.models import User, UploadedFile, CSVData, FileValidation
from app.services.s3_service import get_s3_service
from app.services.csv_service import get_csv_service
from app.schemas.schemas import (
    FileUploadResponse,
    UploadedFileResponse,
    ValidationResult,
)

router = APIRouter(prefix="/files", tags=["File Upload"])
settings = get_settings()


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("uploader"))]
)
async def upload_csv_file(
    file: UploadFile = File(..., description="Archivo CSV a subir"),
    param1: str = Form(..., description="Primer parámetro adicional"),
    param2: str = Form(..., description="Segundo parámetro adicional"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and validate a CSV file.
    
    **Requires 'uploader' or 'admin' role.**
    
    - **file**: CSV file to upload
    - **param1**: First additional parameter
    - **param2**: Second additional parameter
    
    The file will be:
    1. Validated for structure and content
    2. Uploaded to S3 (LocalStack)
    3. Processed and stored in SQL Server
    
    Returns upload details and validation results.
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre del archivo es requerido"
        )
    
    file_ext = file.filename.rsplit(".", 1)[-1].lower()
    if file_ext not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Extensión de archivo no permitida. Permitidas: {settings.allowed_extensions}"
        )
    
    # Read file content
    file_content = await file.read()
    file_size = len(file_content)
    
    # Validate file size
    if file_size > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Archivo demasiado grande. Máximo: {settings.max_file_size_mb}MB"
        )
    
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo está vacío"
        )
    
    # Generate unique filename for S3
    unique_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    s3_key = f"uploads/{current_user.id}/{timestamp}_{unique_id}.csv"
    
    # Process and validate CSV
    csv_service = get_csv_service()
    rows, validations = csv_service.validate_and_process(file_content, file.filename)
    
    # Check for critical errors
    critical_errors = [v for v in validations if v.severity == "error"]
    if critical_errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "El archivo tiene errores críticos",
                "errors": [v.model_dump() for v in critical_errors]
            }
        )
    
    # Upload to S3
    s3_service = get_s3_service()
    upload_result = await s3_service.upload_file(
        file_content=file_content,
        s3_key=s3_key,
        content_type="text/csv"
    )
    
    if not upload_result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir archivo a S3: {upload_result.get('error', 'Unknown error')}"
        )
    
    # Create database record for uploaded file
    db_file = UploadedFile(
        filename=f"{timestamp}_{unique_id}.csv",
        original_filename=file.filename,
        s3_key=s3_key,
        file_size=file_size,
        content_type="text/csv",
        param1=param1,
        param2=param2,
        row_count=len(rows),
        upload_status="processing",
        user_id=current_user.id,
    )
    
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    
    # Store CSV data in database
    json_rows = csv_service.rows_to_json(rows)
    for row_num, json_data in enumerate(json_rows, start=1):
        csv_data = CSVData(
            uploaded_file_id=db_file.id,
            row_number=row_num,
            data=json_data,
        )
        db.add(csv_data)
    
    # Store validations in database
    for validation in validations:
        db_validation = FileValidation(
            uploaded_file_id=db_file.id,
            validation_type=validation.validation_type,
            row_number=validation.row_number,
            column_name=validation.column_name,
            message=validation.message,
            severity=validation.severity,
        )
        db.add(db_validation)
    
    # Update status to completed
    db_file.upload_status = "completed"
    db.commit()
    
    return FileUploadResponse(
        id=db_file.id,
        filename=db_file.filename,
        original_filename=db_file.original_filename,
        s3_key=db_file.s3_key,
        s3_url=upload_result["url"],
        file_size=file_size,
        row_count=len(rows),
        param1=param1,
        param2=param2,
        upload_status=db_file.upload_status,
        validations=validations,
        created_at=db_file.created_at,
    )


@router.get("/", response_model=List[UploadedFileResponse])
async def list_uploaded_files(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all uploaded files for the current user.
    
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    """
    query = db.query(UploadedFile)
    
    # Non-admin users can only see their own files
    if current_user.role != "admin":
        query = query.filter(UploadedFile.user_id == current_user.id)
    
    files = query.order_by(UploadedFile.created_at.desc()).offset(skip).limit(limit).all()
    
    return files


@router.get("/{file_id}", response_model=UploadedFileResponse)
async def get_uploaded_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific uploaded file.
    
    - **file_id**: ID of the file to retrieve
    """
    db_file = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    
    if not db_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo no encontrado"
        )
    
    # Check permissions
    if current_user.role != "admin" and db_file.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver este archivo"
        )
    
    return db_file


@router.get("/{file_id}/validations", response_model=List[ValidationResult])
async def get_file_validations(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get validation results for a specific file.
    
    - **file_id**: ID of the file
    """
    db_file = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    
    if not db_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo no encontrado"
        )
    
    # Check permissions
    if current_user.role != "admin" and db_file.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver este archivo"
        )
    
    validations = db.query(FileValidation).filter(
        FileValidation.uploaded_file_id == file_id
    ).all()
    
    return [
        ValidationResult(
            validation_type=v.validation_type,
            row_number=v.row_number,
            column_name=v.column_name,
            message=v.message,
            severity=v.severity,
        )
        for v in validations
    ]
