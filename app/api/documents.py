"""
Document Analysis API endpoints.
"""
import uuid
import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO

from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import require_role, get_current_user
from app.models.models import User, Document, InvoiceData, InfoData
from app.services.s3_service import get_s3_service
from app.services.document_service import get_document_service
from app.services.event_service import get_event_service
from app.schemas.schemas import (
    DocumentResponse,
    DocumentListResponse,
    InvoiceDataBase,
    InfoDataBase,
    InvoiceProduct,
    MessageResponse,
)

router = APIRouter(prefix="/documents", tags=["Document Analysis"])
settings = get_settings()


def _build_document_response(
    doc: Document,
    s3_url: str,
    invoice_data: Optional[InvoiceData] = None,
    info_data: Optional[InfoData] = None
) -> DocumentResponse:
    """Build document response from model."""
    invoice_data_schema = None
    info_data_schema = None
    
    if invoice_data:
        products = []
        if invoice_data.products_json:
            try:
                products_raw = json.loads(invoice_data.products_json)
                products = [InvoiceProduct(**p) for p in products_raw]
            except (json.JSONDecodeError, TypeError):
                pass
        
        invoice_data_schema = InvoiceDataBase(
            client_name=invoice_data.client_name,
            client_address=invoice_data.client_address,
            provider_name=invoice_data.provider_name,
            provider_address=invoice_data.provider_address,
            invoice_number=invoice_data.invoice_number,
            invoice_date=invoice_data.invoice_date,
            invoice_total=invoice_data.invoice_total,
            currency=invoice_data.currency,
            products=products
        )
    
    if info_data:
        key_topics = []
        if info_data.key_topics_json:
            try:
                key_topics = json.loads(info_data.key_topics_json)
            except json.JSONDecodeError:
                pass
        
        info_data_schema = InfoDataBase(
            description=info_data.description,
            summary=info_data.summary,
            sentiment=info_data.sentiment,
            sentiment_score=info_data.sentiment_score,
            key_topics=key_topics
        )
    
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        original_filename=doc.original_filename,
        s3_key=doc.s3_key,
        s3_url=s3_url,
        file_size=doc.file_size,
        content_type=doc.content_type,
        document_type=doc.document_type,
        analysis_status=doc.analysis_status,
        analysis_error=doc.analysis_error,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        invoice_data=invoice_data_schema,
        info_data=info_data_schema
    )


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("uploader"))]
)
async def upload_document(
    file: UploadFile = File(..., description="Documento PDF, JPG o PNG a analizar"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and analyze a document (PDF, JPG, or PNG).
    
    **Requires 'uploader' or 'admin' role.**
    
    The document will be:
    1. Uploaded to S3
    2. Classified automatically (Factura or Información)
    3. Data extracted based on classification
    
    Returns document details with extracted data.
    """
    event_service = get_event_service()
    
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre del archivo es requerido"
        )
    
    file_ext = file.filename.rsplit(".", 1)[-1].lower()
    if file_ext not in settings.document_allowed_extensions_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Extensión no permitida. Permitidas: {settings.document_allowed_extensions}"
        )
    
    # Read file content
    file_content = await file.read()
    file_size = len(file_content)
    
    # Validate file size
    if file_size > settings.max_document_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Archivo demasiado grande. Máximo: {settings.max_document_size_mb}MB"
        )
    
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo está vacío"
        )
    
    # Get content type
    document_service = get_document_service()
    content_type = document_service.get_content_type(file.filename)
    
    # Generate unique filename for S3
    unique_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    s3_key = f"documents/{current_user.id}/{timestamp}_{unique_id}.{file_ext}"
    
    # Upload to S3
    s3_service = get_s3_service()
    upload_result = await s3_service.upload_file(
        file_content=file_content,
        s3_key=s3_key,
        content_type=content_type
    )
    
    if not upload_result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir archivo a S3: {upload_result.get('error', 'Unknown error')}"
        )
    
    s3_url = upload_result["url"]
    
    # Create document record
    db_document = Document(
        filename=f"{timestamp}_{unique_id}.{file_ext}",
        original_filename=file.filename,
        s3_key=s3_key,
        file_size=file_size,
        content_type=content_type,
        analysis_status="processing",
        user_id=current_user.id,
    )
    
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    
    # Log upload event
    event_service.log_document_upload(
        db=db,
        document_id=db_document.id,
        filename=file.filename,
        user_id=current_user.id
    )
    
    # Analyze document with AI
    try:
        analysis_result = await document_service.analyze_document(
            file_content=file_content,
            content_type=content_type,
            filename=file.filename
        )
        
        # Update document with classification
        db_document.document_type = analysis_result.document_type.value
        db_document.analysis_status = "completed"
        
        # Store extracted data based on document type
        invoice_data = None
        info_data = None
        
        if analysis_result.document_type.value == "factura" and analysis_result.invoice_data:
            products_json = json.dumps([p.model_dump() for p in analysis_result.invoice_data.products])
            
            invoice_data = InvoiceData(
                document_id=db_document.id,
                client_name=analysis_result.invoice_data.client_name,
                client_address=analysis_result.invoice_data.client_address,
                provider_name=analysis_result.invoice_data.provider_name,
                provider_address=analysis_result.invoice_data.provider_address,
                invoice_number=analysis_result.invoice_data.invoice_number,
                invoice_date=analysis_result.invoice_data.invoice_date,
                invoice_total=analysis_result.invoice_data.invoice_total,
                currency=analysis_result.invoice_data.currency,
                products_json=products_json,
                raw_text=analysis_result.raw_text,
            )
            db.add(invoice_data)
        
        elif analysis_result.document_type.value == "informacion" and analysis_result.info_data:
            key_topics_json = json.dumps(analysis_result.info_data.key_topics)
            
            info_data = InfoData(
                document_id=db_document.id,
                description=analysis_result.info_data.description,
                summary=analysis_result.info_data.summary,
                sentiment=analysis_result.info_data.sentiment,
                sentiment_score=analysis_result.info_data.sentiment_score,
                key_topics_json=key_topics_json,
                raw_text=analysis_result.raw_text,
            )
            db.add(info_data)
        
        db.commit()
        db.refresh(db_document)
        
        # Log AI analysis event
        event_service.log_ai_analysis(
            db=db,
            document_id=db_document.id,
            document_type=analysis_result.document_type.value,
            user_id=current_user.id,
            success=True
        )
        
        return _build_document_response(db_document, s3_url, invoice_data, info_data)
        
    except Exception as e:
        db_document.analysis_status = "failed"
        db_document.analysis_error = str(e)
        db.commit()
        
        # Log AI analysis failure
        event_service.log_ai_analysis(
            db=db,
            document_id=db_document.id,
            document_type="unknown",
            user_id=current_user.id,
            success=False,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en el análisis del documento: {str(e)}"
        )


@router.get(
    "/",
    response_model=List[DocumentListResponse],
    dependencies=[Depends(require_role("user"))]
)
async def list_documents(
    status_filter: Optional[str] = Query(None, description="Filtrar por estado: pending, processing, completed, failed"),
    type_filter: Optional[str] = Query(None, description="Filtrar por tipo: factura, informacion"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all documents for the current user.
    
    Supports filtering by status and document type.
    """
    query = db.query(Document).filter(Document.user_id == current_user.id)
    
    if status_filter:
        query = query.filter(Document.analysis_status == status_filter)
    
    if type_filter:
        query = query.filter(Document.document_type == type_filter)
    
    offset = (page - 1) * page_size
    documents = query.order_by(Document.created_at.desc()).offset(offset).limit(page_size).all()
    
    return [
        DocumentListResponse(
            id=doc.id,
            filename=doc.filename,
            original_filename=doc.original_filename,
            document_type=doc.document_type,
            analysis_status=doc.analysis_status,
            file_size=doc.file_size,
            created_at=doc.created_at
        )
        for doc in documents
    ]


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    dependencies=[Depends(require_role("user"))]
)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific document including extracted data.
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado"
        )
    
    s3_url = f"{settings.s3_endpoint_url}/{settings.s3_bucket_name}/{document.s3_key}"
    
    # Get related data
    invoice_data = db.query(InvoiceData).filter(InvoiceData.document_id == document_id).first()
    info_data = db.query(InfoData).filter(InfoData.document_id == document_id).first()
    
    # Log user interaction
    event_service = get_event_service()
    event_service.log_user_interaction(
        db=db,
        action="Visualización de documento",
        user_id=current_user.id,
        document_id=document_id
    )
    
    return _build_document_response(document, s3_url, invoice_data, info_data)


@router.delete(
    "/{document_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_role("uploader"))]
)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a document and its associated data.
    
    **Requires 'uploader' or 'admin' role.**
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado"
        )
    
    # Delete from S3
    s3_service = get_s3_service()
    await s3_service.delete_file(document.s3_key)
    
    # Delete related data
    db.query(InvoiceData).filter(InvoiceData.document_id == document_id).delete()
    db.query(InfoData).filter(InfoData.document_id == document_id).delete()
    
    # Log event
    event_service = get_event_service()
    event_service.log_user_interaction(
        db=db,
        action="Eliminación de documento",
        user_id=current_user.id,
        document_id=document_id,
        details={"filename": document.original_filename}
    )
    
    # Delete document
    db.delete(document)
    db.commit()
    
    return MessageResponse(
        message="Documento eliminado exitosamente",
        success=True
    )


@router.post(
    "/{document_id}/reanalyze",
    response_model=DocumentResponse,
    dependencies=[Depends(require_role("uploader"))]
)
async def reanalyze_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Re-analyze a document with AI.
    
    **Requires 'uploader' or 'admin' role.**
    
    Useful if the initial analysis failed or was incorrect.
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado"
        )
    
    # Download file from S3
    s3_service = get_s3_service()
    file_content = await s3_service.download_file(document.s3_key)
    
    if not file_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se pudo obtener el archivo de S3"
        )
    
    # Delete existing extracted data
    db.query(InvoiceData).filter(InvoiceData.document_id == document_id).delete()
    db.query(InfoData).filter(InfoData.document_id == document_id).delete()
    
    # Update status
    document.analysis_status = "processing"
    document.analysis_error = None
    db.commit()
    
    # Re-analyze with AI
    document_service = get_document_service()
    event_service = get_event_service()
    
    try:
        analysis_result = await document_service.analyze_document(
            file_content=file_content,
            content_type=document.content_type,
            filename=document.original_filename
        )
        
        # Update document
        document.document_type = analysis_result.document_type.value
        document.analysis_status = "completed"
        
        # Store extracted data
        invoice_data = None
        info_data = None
        
        if analysis_result.document_type.value == "factura" and analysis_result.invoice_data:
            products_json = json.dumps([p.model_dump() for p in analysis_result.invoice_data.products])
            
            invoice_data = InvoiceData(
                document_id=document.id,
                client_name=analysis_result.invoice_data.client_name,
                client_address=analysis_result.invoice_data.client_address,
                provider_name=analysis_result.invoice_data.provider_name,
                provider_address=analysis_result.invoice_data.provider_address,
                invoice_number=analysis_result.invoice_data.invoice_number,
                invoice_date=analysis_result.invoice_data.invoice_date,
                invoice_total=analysis_result.invoice_data.invoice_total,
                currency=analysis_result.invoice_data.currency,
                products_json=products_json,
                raw_text=analysis_result.raw_text,
            )
            db.add(invoice_data)
        
        elif analysis_result.document_type.value == "informacion" and analysis_result.info_data:
            key_topics_json = json.dumps(analysis_result.info_data.key_topics)
            
            info_data = InfoData(
                document_id=document.id,
                description=analysis_result.info_data.description,
                summary=analysis_result.info_data.summary,
                sentiment=analysis_result.info_data.sentiment,
                sentiment_score=analysis_result.info_data.sentiment_score,
                key_topics_json=key_topics_json,
                raw_text=analysis_result.raw_text,
            )
            db.add(info_data)
        
        db.commit()
        db.refresh(document)
        
        # Log event
        event_service.log_ai_analysis(
            db=db,
            document_id=document.id,
            document_type=analysis_result.document_type.value,
            user_id=current_user.id,
            success=True
        )
        
        s3_url = f"{settings.s3_endpoint_url}/{settings.s3_bucket_name}/{document.s3_key}"
        return _build_document_response(document, s3_url, invoice_data, info_data)
        
    except Exception as e:
        document.analysis_status = "failed"
        document.analysis_error = str(e)
        db.commit()
        
        event_service.log_ai_analysis(
            db=db,
            document_id=document.id,
            document_type="unknown",
            user_id=current_user.id,
            success=False,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en el re-análisis del documento: {str(e)}"
        )


@router.get(
    "/{document_id}/download",
    dependencies=[Depends(require_role("user"))]
)
async def download_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download the original document file.
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado"
        )
    
    s3_service = get_s3_service()
    file_content = await s3_service.download_file(document.s3_key)
    
    if not file_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se pudo obtener el archivo de S3"
        )
    
    # Log download event
    event_service = get_event_service()
    event_service.log_user_interaction(
        db=db,
        action="Descarga de documento",
        user_id=current_user.id,
        document_id=document_id
    )
    
    return StreamingResponse(
        BytesIO(file_content),
        media_type=document.content_type,
        headers={
            "Content-Disposition": f"attachment; filename={document.original_filename}"
        }
    )
