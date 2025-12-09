"""
Event History API endpoints.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role, get_current_user
from app.models.models import User
from app.services.event_service import get_event_service
from app.schemas.schemas import (
    EventLogResponse,
    EventLogListResponse,
    EventLogFilter,
    EventTypeEnum,
)

router = APIRouter(prefix="/events", tags=["Event History"])


@router.get(
    "/",
    response_model=EventLogListResponse,
    dependencies=[Depends(require_role("user"))]
)
async def list_events(
    event_type: Optional[EventTypeEnum] = Query(None, description="Filtrar por tipo de evento"),
    description_search: Optional[str] = Query(None, description="Buscar en descripción"),
    date_from: Optional[datetime] = Query(None, description="Fecha desde (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Fecha hasta (ISO format)"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List event history with optional filters.
    
    **Filters:**
    - `event_type`: Filter by event type (subida_documento, analisis_ia, interaccion_usuario, sistema)
    - `description_search`: Search text in description
    - `date_from`: Filter events from this date
    - `date_to`: Filter events until this date
    
    **Pagination:**
    - `page`: Page number (default: 1)
    - `page_size`: Items per page (default: 20, max: 100)
    """
    event_service = get_event_service()
    
    # Build filters
    filters = EventLogFilter(
        event_type=event_type,
        description_search=description_search,
        date_from=date_from,
        date_to=date_to
    )
    
    # Get events
    events, total = event_service.get_events(
        db=db,
        filters=filters,
        page=page,
        page_size=page_size
    )
    
    # Convert to response format
    event_responses = [
        event_service.event_to_response(event, db)
        for event in events
    ]
    
    return EventLogListResponse(
        total=total,
        page=page,
        page_size=page_size,
        events=event_responses
    )


@router.get(
    "/types",
    dependencies=[Depends(require_role("user"))]
)
async def get_event_types():
    """
    Get all available event types.
    """
    return {
        "event_types": [
            {"value": "subida_documento", "label": "Subida de Documento"},
            {"value": "analisis_ia", "label": "Análisis IA"},
            {"value": "interaccion_usuario", "label": "Interacción de Usuario"},
            {"value": "sistema", "label": "Sistema"}
        ]
    }


@router.get(
    "/export",
    dependencies=[Depends(require_role("admin"))]
)
async def export_events_to_excel(
    event_type: Optional[EventTypeEnum] = Query(None, description="Filtrar por tipo de evento"),
    description_search: Optional[str] = Query(None, description="Buscar en descripción"),
    date_from: Optional[datetime] = Query(None, description="Fecha desde (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Fecha hasta (ISO format)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export filtered events to Excel file.
    
    **Requires 'admin' role.**
    
    Returns an Excel file (.xlsx) with the filtered event data.
    """
    event_service = get_event_service()
    
    # Build filters
    filters = EventLogFilter(
        event_type=event_type,
        description_search=description_search,
        date_from=date_from,
        date_to=date_to
    )
    
    # Log export action
    event_service.log_user_interaction(
        db=db,
        action="Exportación de histórico a Excel",
        user_id=current_user.id,
        details={
            "filters": {
                "event_type": event_type.value if event_type else None,
                "description_search": description_search,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None
            }
        }
    )
    
    # Generate Excel file
    excel_buffer = event_service.export_to_excel(db=db, filters=filters)
    
    # Generate filename with timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"historico_eventos_{timestamp}.xlsx"
    
    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get(
    "/stats",
    dependencies=[Depends(require_role("user"))]
)
async def get_event_stats(
    date_from: Optional[datetime] = Query(None, description="Fecha desde (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Fecha hasta (ISO format)"),
    db: Session = Depends(get_db)
):
    """
    Get event statistics.
    
    Returns counts grouped by event type.
    """
    from sqlalchemy import func
    from app.models.models import EventLog
    
    query = db.query(
        EventLog.event_type,
        func.count(EventLog.id).label("count")
    )
    
    if date_from:
        query = query.filter(EventLog.created_at >= date_from)
    
    if date_to:
        query = query.filter(EventLog.created_at <= date_to)
    
    stats = query.group_by(EventLog.event_type).all()
    
    # Get total count
    total_query = db.query(func.count(EventLog.id))
    if date_from:
        total_query = total_query.filter(EventLog.created_at >= date_from)
    if date_to:
        total_query = total_query.filter(EventLog.created_at <= date_to)
    
    total = total_query.scalar() or 0
    
    # Format response
    event_type_labels = {
        "subida_documento": "Subida de Documento",
        "analisis_ia": "Análisis IA",
        "interaccion_usuario": "Interacción de Usuario",
        "sistema": "Sistema"
    }
    
    stats_response = {
        "total": total,
        "by_type": {
            event_type_labels.get(s.event_type, s.event_type): s.count
            for s in stats
        }
    }
    
    return stats_response


@router.get(
    "/{event_id}",
    response_model=EventLogResponse,
    dependencies=[Depends(require_role("user"))]
)
async def get_event(
    event_id: int,
    db: Session = Depends(get_db)
):
    """
    Get details of a specific event.
    """
    event_service = get_event_service()
    
    event = event_service.get_event(db=db, event_id=event_id)
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado"
        )
    
    return event_service.event_to_response(event, db)
