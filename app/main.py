"""
Main FastAPI application with all critical fixes:
- CORS middleware properly configured
- Directory creation on startup
- Error handling middleware
- Request logging and timing
- Rate limiting
- File cleanup scheduler
"""
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.routes import health, upload, files, summary, query, graph, comparison
from utils.logger import setup_logger, RequestLogger
from utils.cleanup import FileCleanupManager

# Setup logging
logger = setup_logger(__name__, settings.log_level, settings.log_format)
request_logger = RequestLogger(logger)

# Global cleanup manager
cleanup_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management: startup and shutdown events."""
    # Startup
    logger.info("🚀 Starting Codebase Explainer API...")
    
    # Ensure directories exist
    try:
        settings.ensure_directories_exist()
        logger.info("✓ All directories created/verified")
    except Exception as e:
        logger.error(f"Failed to create directories: {e}")
        raise
    
    # Initialize cleanup manager
    if settings.cleanup_enabled:
        global cleanup_manager
        cleanup_manager = FileCleanupManager(
            upload_dir=settings.get_absolute_path(settings.upload_dir),
            summaries_dir=settings.get_absolute_path(settings.summaries_dir),
            max_age_days=settings.max_file_age_days,
            cleanup_interval_hours=settings.cleanup_interval_hours
        )
        cleanup_manager.start_scheduled_cleanup()
        logger.info("✓ Cleanup scheduler started")
    
    # Log configuration
    logger.info(f"Configuration: AI={settings.ai_available}, Demo={settings.demo_mode}")
    logger.info(f"Max upload size: {settings.max_upload_size_mb}MB")
    logger.info(f"Rate limit: {settings.rate_limit_per_minute}/min")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    if cleanup_manager:
        cleanup_manager.stop_scheduled_cleanup()


# Create FastAPI app
app = FastAPI(
    title="Codebase Explainer API",
    description="AI-powered codebase analysis and Q&A system",
    version="1.0.0",
    lifespan=lifespan
)


# CORS Middleware - CRITICAL FIX
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing and logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing information."""
    start_time = time.time()
    
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        request_logger.log_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms
        )
        
        # Add timing header
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
        return response
    
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        request_logger.log_error(e, context={
            'method': request.method,
            'path': request.url.path,
            'duration_ms': duration_ms
        })
        raise


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages."""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "Invalid request data",
            "details": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler to prevent crashes."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": type(exc).__name__,
            "message": "An internal error occurred. Please try again later.",
            "path": request.url.path
        }
    )


# Rate limiting (simple in-memory implementation)
from collections import defaultdict
from datetime import datetime, timedelta

rate_limit_tracker = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Simple rate limiting per IP address."""
    client_ip = request.client.host
    current_time = datetime.now()
    
    # Clean old entries
    rate_limit_tracker[client_ip] = [
        timestamp for timestamp in rate_limit_tracker[client_ip]
        if current_time - timestamp < timedelta(minutes=1)
    ]
    
    # Check rate limit
    if len(rate_limit_tracker[client_ip]) >= settings.rate_limit_per_minute:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "RateLimitExceeded",
                "message": f"Rate limit exceeded. Max {settings.rate_limit_per_minute} requests per minute.",
                "retry_after": 60
            }
        )
    
    # Add current request
    rate_limit_tracker[client_ip].append(current_time)
    
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_per_minute)
    response.headers["X-RateLimit-Remaining"] = str(
        settings.rate_limit_per_minute - len(rate_limit_tracker[client_ip])
    )
    
    return response


# Register routes
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(files.router, prefix="/files", tags=["Files"])
app.include_router(summary.router, prefix="/summary", tags=["Summary"])
app.include_router(query.router, prefix="/query", tags=["Query"])
app.include_router(graph.router, prefix="/api", tags=["Graph"])
app.include_router(comparison.router, prefix="/api/comparison", tags=["Comparison"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Codebase Explainer API",
        "version": "1.0.0",
        "status": "running",
        "ai_enabled": settings.ai_available,
        "demo_mode": settings.demo_mode,
        "endpoints": {
            "health": "/health",
            "upload": "/upload",
            "files": "/files/{upload_id}",
            "summary": "/summary/{upload_id}",
            "query": "/query/{upload_id}",
            "graph": "/api/graph/{upload_id}",
            "comparison": "/api/comparison/compare?base_upload_id=X&compare_upload_id=Y"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
