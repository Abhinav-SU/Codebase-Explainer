"""
Health check endpoint with system diagnostics.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, status
from pydantic import BaseModel

from app.config import settings
from utils.cleanup import cleanup_manager

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    ai_available: bool
    demo_mode: bool
    disk_usage: Optional[dict] = None


@router.get("", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint.
    Returns system status and configuration.
    """
    disk_usage = None
    if cleanup_manager:
        try:
            disk_usage = cleanup_manager.get_disk_usage()
        except Exception:
            pass
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        ai_available=settings.ai_available,
        demo_mode=settings.demo_mode,
        disk_usage=disk_usage
    )


@router.get("/ready")
async def readiness_check():
    """
    Readiness probe for deployment.
    Checks if all required services are available.
    """
    checks = {
        "directories": False,
        "ai_configured": settings.ai_available or settings.demo_mode,
        "cleanup_running": cleanup_manager is not None if settings.cleanup_enabled else True
    }
    
    # Check directories exist
    try:
        upload_dir = settings.get_absolute_path(settings.upload_dir)
        summaries_dir = settings.get_absolute_path(settings.summaries_dir)
        checks["directories"] = upload_dir.exists() and summaries_dir.exists()
    except Exception:
        checks["directories"] = False
    
    all_ready = all(checks.values())
    
    return {
        "ready": all_ready,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }
