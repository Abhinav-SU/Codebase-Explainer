"""
API Routes for Codebase Comparison
"""
from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from app.models.codebase_metadata import CodebaseMetadata, CodebaseComparison
from app.services.comparison import CodebaseComparator
from app.services.metadata_builder import MetadataBuilder
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)

# Cache for metadata
_metadata_cache: Dict[str, CodebaseMetadata] = {}


@router.get("/metadata/{upload_id}", response_model=CodebaseMetadata)
async def get_codebase_metadata(
    upload_id: str,
    refresh: bool = Query(False, description="Force refresh metadata")
) -> CodebaseMetadata:
    """
    Get standardized metadata for a codebase.
    Generates and caches metadata for comparison purposes.
    """
    # Check cache
    if not refresh and upload_id in _metadata_cache:
        logger.info(f"Returning cached metadata for {upload_id}")
        return _metadata_cache[upload_id]
    
    upload_dir = Path("uploads") / upload_id
    
    if not upload_dir.exists():
        raise HTTPException(status_code=404, detail=f"Upload {upload_id} not found")
    
    try:
        # Build metadata
        builder = MetadataBuilder(upload_dir)
        metadata = builder.build_metadata(upload_id)
        
        # Cache it
        _metadata_cache[upload_id] = metadata
        
        logger.info(f"Generated metadata for {upload_id}: {metadata.total_files} files")
        return metadata
        
    except Exception as e:
        logger.error(f"Failed to build metadata for {upload_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate metadata: {str(e)}")


@router.post("/compare", response_model=CodebaseComparison)
async def compare_codebases(
    base_upload_id: str = Query(..., description="Base codebase upload ID"),
    compare_upload_id: str = Query(..., description="Codebase to compare against base")
) -> CodebaseComparison:
    """
    Compare two codebases and return detailed differences.
    
    Compares:
    - File structure (added, removed, modified files)
    - Code metrics (lines, classes, functions)
    - Dependencies (new packages, circular dependencies)
    - Overall similarity score
    """
    logger.info(f"Comparing {base_upload_id} vs {compare_upload_id}")
    
    # Get metadata for both codebases
    try:
        base_metadata = await get_codebase_metadata(base_upload_id)
        compare_metadata = await get_codebase_metadata(compare_upload_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load metadata: {str(e)}")
    
    # Perform comparison
    try:
        comparator = CodebaseComparator()
        comparison = comparator.compare(base_metadata, compare_metadata)
        
        logger.info(f"Comparison complete: {comparison.similarity_score:.2f} similarity")
        return comparison
        
    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.get("/list", response_model=List[Dict])
async def list_available_codebases() -> List[Dict]:
    """
    List all uploaded codebases available for comparison.
    Returns basic info for each upload.
    """
    upload_dir = Path("uploads")
    
    if not upload_dir.exists():
        return []
    
    codebases = []
    
    for upload_path in upload_dir.iterdir():
        if upload_path.is_dir():
            # Get cached metadata if available
            if upload_path.name in _metadata_cache:
                meta = _metadata_cache[upload_path.name]
                codebases.append({
                    'upload_id': upload_path.name,
                    'name': meta.name,
                    'total_files': meta.total_files,
                    'total_lines': meta.total_lines,
                    'uploaded_at': meta.uploaded_at.isoformat()
                })
            else:
                # Basic info without full metadata
                file_count = sum(1 for _ in upload_path.rglob('*') if _.is_file())
                codebases.append({
                    'upload_id': upload_path.name,
                    'name': upload_path.name,
                    'total_files': file_count,
                    'uploaded_at': datetime.fromtimestamp(upload_path.stat().st_mtime).isoformat()
                })
    
    logger.info(f"Found {len(codebases)} available codebases")
    return sorted(codebases, key=lambda x: x['uploaded_at'], reverse=True)


@router.delete("/metadata/{upload_id}/cache")
async def clear_metadata_cache(upload_id: str) -> Dict:
    """Clear cached metadata for an upload."""
    if upload_id in _metadata_cache:
        del _metadata_cache[upload_id]
        logger.info(f"Cleared metadata cache for {upload_id}")
        return {'message': f'Cache cleared for {upload_id}'}
    else:
        return {'message': f'No cache found for {upload_id}'}
