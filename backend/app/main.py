"""
Main FastAPI Application for Self Study OS.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import init_db, close_db, get_db
from app.api.routes import router as api_router

logger = logging.getLogger("self_study_os")
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    if settings.ENVIRONMENT != "test":
        try:
            logger.info("Initializing database connection...")
            await init_db()
            logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}] started")
        except Exception as e:
            logger.warning(f"Database initialization warning on startup: {e}")
    else:
        logger.info("Running in test environment, skipping automatic DB init.")

    yield

    # Shutdown
    if settings.ENVIRONMENT != "test":
        try:
            logger.info("Shutting down database connection...")
            await close_db()
            logger.info(f"👋 {settings.APP_NAME} shutdown complete")
        except Exception as e:
            logger.warning(f"Database shutdown warning: {e}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Personal Learning Operating System - Become a multidisciplinary systems engineer",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG or settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.DEBUG or settings.ENVIRONMENT != "production" else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "description": "Personal Learning Operating System",
        "api": "/api/v1",
        "health": "/health",
    }


@app.get("/health")
async def health_check():
    """General health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/health/live")
async def liveness_check():
    """Liveness probe: verifies process is up and responsive."""
    return {
        "status": "alive",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness probe: verifies database and vector extension connectivity."""
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() != 1:
            raise Exception("Database returned invalid ping result")

        vector_res = await db.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
        has_vector = vector_res.scalar() is not None

        return {
            "status": "ready",
            "database": "connected",
            "pgvector_extension": has_vector,
            "environment": settings.ENVIRONMENT,
        }
    except Exception as e:
        logger.error(f"Readiness probe failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", "error": "Database connection unavailable"},
        )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.exception(f"Unhandled exception on {request.url.path}: {exc}")
    detail = str(exc) if settings.DEBUG else "Internal server error"
    return JSONResponse(
        status_code=500,
        content={"detail": detail},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )