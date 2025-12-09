"""
FastAPI Application Entry Point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.core.config import get_settings
from app.core.database import init_db
from app.services.s3_service import get_s3_service
from app.api import auth, files, documents, events, web

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("🚀 Starting application...")
    
    # Initialize database tables
    print("📦 Initializing database...")
    init_db()
    
    # Initialize S3 bucket
    print("🪣 Ensuring S3 bucket exists...")
    s3_service = get_s3_service()
    s3_service.ensure_bucket_exists()
    
    yield
    
    # Shutdown
    print("👋 Shutting down application...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
## OneCoreMxPy API

API para gestión de archivos y análisis de documentos con IA.

### Características:
- 🔐 Autenticación JWT con roles
- 📁 Subida de archivos CSV a S3 (LocalStack)
- ✅ Validación automática de archivos CSV
- 💾 Almacenamiento en SQL Server
- 🔄 Renovación de tokens
- 📄 **Análisis de documentos con IA** (PDF, JPG, PNG)
- 🧾 **Extracción automática de datos de facturas**
- 📊 **Análisis de sentimiento de documentos informativos**
- 📜 **Módulo histórico de eventos**
- 📥 **Exportación a Excel**

### Módulos Web:
- **Análisis de Documentos**: Clasifica documentos como Factura o Información
- **Histórico**: Registro de eventos del sistema con filtros y exportación

### Roles:
- **user**: Usuario básico
- **uploader**: Puede subir archivos CSV y documentos
- **admin**: Acceso completo
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")

# Include Web interface router
app.include_router(web.router)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - health check."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "status": "healthy",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "modules": {
            "document_analysis": True,
            "event_history": True,
            "ai_enabled": bool(settings.openai_api_key)
        }
    }
