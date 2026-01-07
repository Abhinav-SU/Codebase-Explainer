"""
Query endpoint with graceful degradation when AI is unavailable.
"""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import settings
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


class QueryRequest(BaseModel):
    """Query request model."""
    question: str
    search_mode: str = "hybrid"
    max_results: int = 5


class QuerySource(BaseModel):
    """Source document for query result."""
    filepath: str
    relevance_score: float
    text_snippet: str
    match_type: str


class QueryResponse(BaseModel):
    """Query response model."""
    upload_id: str
    question: str
    answer: str
    confidence: float
    sources: List[QuerySource]
    timestamp: str
    mode: str


@router.post("/{upload_id}", response_model=QueryResponse)
async def query_codebase(upload_id: str, request: QueryRequest):
    """
    Ask questions about the codebase.
    
    **Note**: This endpoint requires Google Gemini API key to be configured.
    If AI is not available, returns a helpful error message.
    """
    logger.info(f"Query for {upload_id}: {request.question}")
    
    # Check if AI is available
    if not settings.ai_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "AINotAvailable",
                "message": "Google Gemini API key not configured. Q&A features require AI to be enabled.",
                "solution": "Set GEMINI_API_KEY in .env file to enable Q&A functionality."
            }
        )
    
    # Check if upload exists
    upload_dir = settings.get_absolute_path(settings.upload_dir) / upload_id
    if not upload_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload {upload_id} not found"
        )
    
    # TODO: Implement actual query logic with LlamaIndex
    # For now, return placeholder response
    
    return QueryResponse(
        upload_id=upload_id,
        question=request.question,
        answer="Q&A functionality coming soon! For now, you can browse file summaries.",
        confidence=0.0,
        sources=[],
        timestamp=datetime.utcnow().isoformat(),
        mode="placeholder"
    )
