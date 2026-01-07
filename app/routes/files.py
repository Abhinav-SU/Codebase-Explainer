"""
File listing and content retrieval with proper error handling.
"""
import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel

from app.config import settings
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


class FileMetadata(BaseModel):
    """File metadata model."""
    filename: str
    relative_path: str
    size_bytes: int
    last_modified: str
    file_type: str


class FileListResponse(BaseModel):
    """File list response with pagination."""
    upload_id: str
    total_files: int
    page: int
    page_size: int
    files: List[FileMetadata]


class FileContentResponse(BaseModel):
    """File content response."""
    upload_id: str
    file_path: str
    total_lines: int
    content_range: Optional[dict] = None
    content: str
    encoding: str


class CodebaseParser:
    """Parse codebase and extract metadata."""
    
    SUPPORTED_EXTENSIONS = ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h']
    EXCLUDE_DIRS = {'__pycache__', '.git', 'venv', 'node_modules', '.venv', 'env', 'build', 'dist'}
    
    def __init__(self, upload_dir: Path):
        self.upload_dir = upload_dir
    
    def parse_directory(self, upload_id: str) -> List[FileMetadata]:
        """
        Recursively scan for supported files.
        Includes error handling for permission issues.
        """
        root_dir = self.upload_dir / upload_id
        
        if not root_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload {upload_id} not found"
            )
        
        files = []
        errors = []
        
        try:
            for dirpath, dirnames, filenames in os.walk(root_dir):
                # Skip excluded directories
                dirnames[:] = [d for d in dirnames if d not in self.EXCLUDE_DIRS]
                
                for filename in filenames:
                    if Path(filename).suffix in self.SUPPORTED_EXTENSIONS:
                        try:
                            filepath = Path(dirpath) / filename
                            metadata = self._extract_metadata(filepath, root_dir)
                            files.append(metadata)
                        except Exception as e:
                            errors.append(f"Error processing {filename}: {str(e)}")
                            logger.warning(f"Error processing file {filename}: {e}")
        
        except Exception as e:
            logger.error(f"Error scanning directory {root_dir}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error scanning directory: {str(e)}"
            )
        
        if errors:
            logger.warning(f"Encountered {len(errors)} errors while parsing {upload_id}")
        
        return files
    
    def _extract_metadata(self, filepath: Path, root_dir: Path) -> FileMetadata:
        """Extract file metadata with error handling."""
        try:
            stat = filepath.stat()
            return FileMetadata(
                filename=filepath.name,
                relative_path=str(filepath.relative_to(root_dir)),
                size_bytes=stat.st_size,
                last_modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                file_type=filepath.suffix[1:]  # Remove leading dot
            )
        except Exception as e:
            logger.error(f"Error extracting metadata for {filepath}: {e}")
            raise
    
    def read_file_content(
        self,
        upload_id: str,
        file_path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None
    ) -> FileContentResponse:
        """
        Read file content with encoding detection and pagination.
        """
        root_dir = self.upload_dir / upload_id
        full_path = root_dir / file_path
        
        # Security check: prevent path traversal
        try:
            full_path = full_path.resolve()
            root_dir = root_dir.resolve()
            if not str(full_path).startswith(str(root_dir)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid file path"
                )
        except Exception as e:
            logger.warning(f"Path traversal attempt: {file_path}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path"
            )
        
        if not full_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_path}"
            )
        
        # Try multiple encodings
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(full_path, 'r', encoding=encoding) as f:
                    lines = f.readlines()
                
                total_lines = len(lines)
                
                # Apply pagination
                content_range = None
                if start_line is not None and end_line is not None:
                    # Validate line range
                    if start_line < 1 or end_line < start_line or end_line > total_lines:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid line range. File has {total_lines} lines."
                        )
                    
                    content_lines = lines[start_line-1:end_line]
                    content_range = {
                        "start_line": start_line,
                        "end_line": end_line
                    }
                else:
                    content_lines = lines
                
                return FileContentResponse(
                    upload_id=upload_id,
                    file_path=file_path,
                    total_lines=total_lines,
                    content_range=content_range,
                    content=''.join(content_lines),
                    encoding=encoding
                )
            
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error reading file: {str(e)}"
                )
        
        # If all encodings failed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not decode file with any supported encoding"
        )


# Initialize parser
parser = CodebaseParser(settings.get_absolute_path(settings.upload_dir))


@router.get("/{upload_id}", response_model=FileListResponse)
async def list_files(
    upload_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page")
):
    """
    List all parsed files in an upload with pagination.
    """
    logger.info(f"Listing files for upload {upload_id}")
    
    try:
        # Parse directory
        all_files = parser.parse_directory(upload_id)
        
        # Apply pagination
        total_files = len(all_files)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_files = all_files[start_idx:end_idx]
        
        return FileListResponse(
            upload_id=upload_id,
            total_files=total_files,
            page=page,
            page_size=page_size,
            files=paginated_files
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing files: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while listing files"
        )


@router.get("/{upload_id}/content", response_model=FileContentResponse)
async def get_file_content(
    upload_id: str,
    path: str = Query(..., description="Relative file path"),
    start_line: Optional[int] = Query(None, ge=1, description="Start line number"),
    end_line: Optional[int] = Query(None, ge=1, description="End line number")
):
    """
    Retrieve file content with optional pagination by line numbers.
    """
    logger.info(f"Reading file {path} from upload {upload_id}")
    
    try:
        return parser.read_file_content(upload_id, path, start_line, end_line)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading file content: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while reading file content"
        )
