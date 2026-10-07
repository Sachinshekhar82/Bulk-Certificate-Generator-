from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routes import router as certificates_router
from app.config import settings
from app.database import init_db
from app.schemas import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan event handler for startup and shutdown initialization."""
    # Ensure database schema is created
    init_db()
    # Ensure storage directory exists
    settings.absolute_storage_dir
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    High-Performance Backend API for Bulk Certificate Generation.
    
    Features:
    - Asynchronous background job processing for high throughput.
    - Fault isolation (individual failures do not affect other certificates).
    - Vector PDF generation using ReportLab with verification QR codes and SHA256 integrity hashes.
    - Real-time progress and job status tracking.
    - Single PDF and bulk ZIP downloads.
    - Public certificate verification endpoint.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable Cross-Origin Resource Sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(certificates_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
def root():
    """Root endpoint welcoming the user and directing to interactive documentation."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "api_v1_jobs": "/api/v1/certificates/jobs",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Health check endpoint for monitoring."""
    return HealthResponse(
        status="healthy",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc),
    )
