"""
FastAPI application for the Illness Prediction System.

This module sets up the FastAPI application with middleware, authentication,
rate limiting, and health check endpoints.

Validates: All requirements (API layer)
"""

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Rate limiting storage (in-memory for simplicity, use Redis in production)
rate_limit_storage: Dict[str, list] = {}


class RateLimiter:
    """Simple rate limiter for API endpoints."""
    
    def __init__(self, requests_per_minute: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60
    
    def is_allowed(self, client_id: str) -> bool:
        """
        Check if request is allowed based on rate limit.
        
        Args:
            client_id: Client identifier (IP address or API key)
            
        Returns:
            True if request is allowed, False otherwise
        """
        now = datetime.utcnow()
        
        # Initialize storage for this client if not exists
        if client_id not in rate_limit_storage:
            rate_limit_storage[client_id] = []
        
        # Remove old requests outside the time window
        cutoff_time = now - timedelta(seconds=self.window_seconds)
        rate_limit_storage[client_id] = [
            req_time for req_time in rate_limit_storage[client_id]
            if req_time > cutoff_time
        ]
        
        # Check if under limit
        if len(rate_limit_storage[client_id]) < self.requests_per_minute:
            rate_limit_storage[client_id].append(now)
            return True
        
        return False
    
    def get_remaining(self, client_id: str) -> int:
        """
        Get remaining requests for client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Number of remaining requests
        """
        if client_id not in rate_limit_storage:
            return self.requests_per_minute
        
        now = datetime.utcnow()
        cutoff_time = now - timedelta(seconds=self.window_seconds)
        
        # Count recent requests
        recent_requests = [
            req_time for req_time in rate_limit_storage[client_id]
            if req_time > cutoff_time
        ]
        
        return max(0, self.requests_per_minute - len(recent_requests))


# Initialize rate limiter
rate_limiter = RateLimiter(requests_per_minute=60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    
    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("Starting Illness Prediction System API")
    logger.info("Initializing services...")
    
    # Initialize services here (database connections, ML models, etc.)
    # This would be where you load ML models, connect to databases, etc.
    
    yield
    
    # Shutdown
    logger.info("Shutting down Illness Prediction System API")
    logger.info("Cleaning up resources...")
    
    # Cleanup resources here


# Create FastAPI application
app = FastAPI(
    title="Illness Prediction System API",
    description="AI-powered illness prediction system with conversational interface",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Trusted host middleware (security)
if os.getenv("TRUSTED_HOSTS"):
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=os.getenv("TRUSTED_HOSTS", "localhost").split(",")
    )


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """
    Middleware for logging all requests and responses.
    
    Args:
        request: Incoming request
        call_next: Next middleware/endpoint handler
        
    Returns:
        Response from endpoint
    """
    start_time = time.time()
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )
    
    # Process request
    try:
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(
            f"Response: {response.status_code} "
            f"in {process_time:.3f}s"
        )
        
        # Add custom headers
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    
    except Exception as e:
        logger.error(f"Request failed: {str(e)}", exc_info=True)
        raise


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """
    Middleware for rate limiting requests.
    
    Args:
        request: Incoming request
        call_next: Next middleware/endpoint handler
        
    Returns:
        Response from endpoint or 429 error
    """
    # Skip rate limiting for health check and docs
    if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
    
    # Get client identifier (IP address or API key)
    client_id = request.client.host if request.client else "unknown"
    
    # Check API key if provided
    api_key = request.headers.get("X-API-Key")
    if api_key:
        client_id = f"api_key:{api_key}"
    
    # Check rate limit
    if not rate_limiter.is_allowed(client_id):
        logger.warning(f"Rate limit exceeded for client: {client_id}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again later.",
                "retry_after": 60
            },
            headers={"Retry-After": "60"}
        )
    
    # Add rate limit headers
    response = await call_next(request)
    remaining = rate_limiter.get_remaining(client_id)
    response.headers["X-RateLimit-Limit"] = str(rate_limiter.requests_per_minute)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Global exception handler for HTTP exceptions.
    
    Args:
        request: Request that caused the exception
        exc: HTTP exception
        
    Returns:
        JSON error response
    """
    logger.error(
        f"HTTP exception: {exc.status_code} - {exc.detail} "
        f"for {request.method} {request.url.path}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled exceptions.
    
    Args:
        request: Request that caused the exception
        exc: Exception
        
    Returns:
        JSON error response
    """
    logger.error(
        f"Unhandled exception: {str(exc)} "
        f"for {request.method} {request.url.path}",
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "path": request.url.path
        }
    )


# Authentication dependency
async def verify_api_key(request: Request) -> Optional[str]:
    """
    Verify API key from request headers.
    
    Args:
        request: Incoming request
        
    Returns:
        API key if valid, None otherwise
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    api_key = request.headers.get("X-API-Key")
    
    # Skip authentication for health check and docs
    if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
        return None
    
    # Check if API key is required
    require_auth = os.getenv("REQUIRE_AUTH", "false").lower() == "true"
    
    if require_auth:
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is required",
                headers={"WWW-Authenticate": "ApiKey"}
            )
        
        # Validate API key (in production, check against database)
        valid_keys = os.getenv("VALID_API_KEYS", "").split(",")
        if api_key not in valid_keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "ApiKey"}
            )
    
    return api_key


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status of the API and its dependencies
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {
            "api": "operational",
            "database": "operational",  # Check actual DB connection in production
            "ml_model": "operational",  # Check actual model status in production
            "cache": "operational"  # Check actual cache status in production
        }
    }


# Include routers
from src.api.routes import sessions, webhooks

app.include_router(sessions.router)
app.include_router(webhooks.router)


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information.
    
    Returns:
        API information and available endpoints
    """
    return {
        "name": "Illness Prediction System API",
        "version": "1.0.0",
        "description": "AI-powered illness prediction system with conversational interface",
        "documentation": "/docs",
        "health": "/health",
        "endpoints": {
            "sessions": "/sessions",
            "webhooks": "/webhooks"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
