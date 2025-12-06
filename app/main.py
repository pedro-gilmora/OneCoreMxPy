"""
FastAPI Application Entry Point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.database import init_db
from app.services.s3_service import get_s3_service
from app.api import auth, files

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

API para gestión de archivos CSV con autenticación JWT.

### Características:
- 🔐 Autenticación JWT con roles
- 📁 Subida de archivos CSV a S3 (LocalStack)
- ✅ Validación automática de archivos CSV
- 💾 Almacenamiento en SQL Server
- 🔄 Renovación de tokens

### Roles:
- **user**: Usuario básico
- **uploader**: Puede subir archivos CSV
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
    }
