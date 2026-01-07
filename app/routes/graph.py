"""
API Routes for Dependency Graph
"""
from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import Dict
import logging
import json

from app.services.dependency_graph import DependencyGraphBuilder

router = APIRouter()
logger = logging.getLogger(__name__)

# Cache for computed graphs
_graph_cache = {}


@router.get("/graph/{upload_id}")
async def get_dependency_graph(upload_id: str) -> Dict:
    """
    Get dependency graph for an uploaded codebase.
    
    Returns:
        - nodes: List of files with metadata
        - edges: Dependencies between files
        - circular_dependencies: Detected circular imports
        - statistics: Graph metrics
    """
    # Check cache first
    if upload_id in _graph_cache:
        logger.info(f"Returning cached graph for {upload_id}")
        return _graph_cache[upload_id]
    
    upload_dir = Path("uploads") / upload_id
    
    if not upload_dir.exists():
        raise HTTPException(status_code=404, detail=f"Upload {upload_id} not found")
    
    try:
        # Build dependency graph
        builder = DependencyGraphBuilder(upload_dir)
        graph_data = builder.build_graph(upload_id)
        
        # Cache the result
        _graph_cache[upload_id] = graph_data
        
        logger.info(f"Successfully built graph for {upload_id}")
        return graph_data
        
    except Exception as e:
        logger.error(f"Error building dependency graph: {e}")
        raise HTTPException(status_code=500, detail=f"Error building graph: {str(e)}")


@router.get("/graph/{upload_id}/file/{file_path:path}")
async def get_file_dependencies(upload_id: str, file_path: str) -> Dict:
    """
    Get dependencies for a specific file.
    
    Returns:
        - imports_from: Files this file imports from
        - imported_by: Files that import this file
        - counts: Metrics
    """
    upload_dir = Path("uploads") / upload_id
    
    if not upload_dir.exists():
        raise HTTPException(status_code=404, detail=f"Upload {upload_id} not found")
    
    try:
        # Build graph if not cached
        if upload_id not in _graph_cache:
            builder = DependencyGraphBuilder(upload_dir)
            graph_data = builder.build_graph(upload_id)
            _graph_cache[upload_id] = graph_data
        else:
            # Rebuild builder from cache for file query
            builder = DependencyGraphBuilder(upload_dir)
            builder.build_graph(upload_id)
        
        file_deps = builder.get_file_dependencies(file_path)
        return file_deps
        
    except Exception as e:
        logger.error(f"Error getting file dependencies: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.delete("/graph/{upload_id}/cache")
async def clear_graph_cache(upload_id: str) -> Dict:
    """Clear cached graph for an upload."""
    if upload_id in _graph_cache:
        del _graph_cache[upload_id]
        return {"status": "success", "message": f"Cache cleared for {upload_id}"}
    else:
        return {"status": "info", "message": f"No cache found for {upload_id}"}
