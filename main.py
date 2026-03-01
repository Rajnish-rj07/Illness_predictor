"""
Main application entry point for the Illness Prediction System.
FastAPI application with health checks and basic setup.
"""

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from config.logging_config import setup_logging, get_logger
from src.database.connection import check_db_connection, check_redis_connection, init_db

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Check database connections
    if not check_db_connection():
        logger.error("PostgreSQL connection failed")
        raise RuntimeError("Database connection failed")
    
    if not check_redis_connection():
        logger.error("Redis connection failed")
        raise RuntimeError("Redis connection failed")
    
    # Initialize database tables
    try:
        init_db()
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Application shutting down")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Intelligent healthcare application for symptom-based illness prediction",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health", tags=["Health"], status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint.
    Verifies database and Redis connections.
    """
    health_status = {
        "status": "healthy",
        "version": settings.app_version,
        "checks": {
            "database": "unknown",
            "redis": "unknown"
        }
    }
    
    # Check PostgreSQL
    try:
        if check_db_connection():
            health_status["checks"]["database"] = "healthy"
        else:
            health_status["checks"]["database"] = "unhealthy"
            health_status["status"] = "degraded"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["checks"]["database"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        if check_redis_connection():
            health_status["checks"]["redis"] = "healthy"
        else:
            health_status["checks"]["redis"] = "unhealthy"
            health_status["status"] = "degraded"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status["checks"]["redis"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Return appropriate status code
    if health_status["status"] == "healthy":
        return JSONResponse(content=health_status, status_code=status.HTTP_200_OK)
    else:
        return JSONResponse(content=health_status, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


@app.get("/ready", tags=["Health"], status_code=status.HTTP_200_OK)
async def readiness_check():
    """
    Readiness check endpoint.
    Indicates if the application is ready to serve requests.
    """
    return {"status": "ready"}


# Include API routers
try:
    from src.api.routes import sessions, webhooks, retell
    app.include_router(sessions.router)
    app.include_router(webhooks.router)
    app.include_router(retell.router)
    logger.info("API routes registered successfully")
except ImportError as e:
    logger.warning(f"Could not import API routes: {e}")
except Exception as e:
    logger.error(f"Error registering API routes: {e}")


def main():
    """Main entry point for running the application."""
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
