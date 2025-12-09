"""
Web Interface Routes for Document Analysis and Event History.
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

# Setup templates
templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))

router = APIRouter(prefix="/web", tags=["Web Interface"])


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse(
        "login.html",
        {"request": request}
    )


@router.get("/documents", response_class=HTMLResponse)
async def documents_page(request: Request):
    """Document analysis page."""
    return templates.TemplateResponse(
        "documents.html",
        {
            "request": request,
            "title": "Análisis de Documentos",
            "active_page": "documents"
        }
    )


@router.get("/events", response_class=HTMLResponse)
async def events_page(request: Request):
    """Event history page."""
    return templates.TemplateResponse(
        "events.html",
        {
            "request": request,
            "title": "Histórico de Eventos",
            "active_page": "events"
        }
    )


@router.get("/", response_class=HTMLResponse)
async def web_root(request: Request):
    """Redirect to documents page."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/web/documents")
