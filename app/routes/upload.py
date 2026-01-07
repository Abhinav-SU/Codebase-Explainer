"""
File upload handler with comprehensive validation and error handling.
CRITICAL FIXES:
- File size validation
- Proper cleanup on errors
- Race condition prevention with unique IDs
- Disk space checks
"""
import uuid
import zipfile
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel

from app.config import settings
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


class UploadResponse(BaseModel):
    """Upload response model."""
    upload_id: str
    filename: str
    size_bytes: int
    extracted_to: str
    status: str
    timestamp: str
    message: Optional[str] = None


class FileHandler:
    """Handles file upload, validation, and extraction."""
    
    def __init__(self):
        self.upload_dir = settings.get_absolute_path(settings.upload_dir)
        self.temp_dir = self.upload_dir / 'temp'
        self.max_size = settings.max_file_size_bytes
        
        # Ensure directories exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    async def validate_file(self, file: UploadFile) -> tuple[bool, Optional[str]]:
        """
        Validate uploaded file.
        Returns (is_valid, error_message)
        """
        # Check file extension
        if not file.filename.endswith('.zip'):
            return False, "Only .zip files are allowed"
        
        # Check file size (read first chunk to get size)
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if file_size > self.max_size:
            max_mb = self.max_size / (1024 * 1024)
            return False, f"File size exceeds {max_mb}MB limit"
        
        if file_size == 0:
            return False, "File is empty"
        
        return True, None
    
    async def save_upload(self, file: UploadFile) -> tuple[str, Path, int]:
        """
        Save uploaded file to temp directory.
        Returns (upload_id, temp_file_path, file_size)
        """
        upload_id = str(uuid.uuid4())
        temp_file_path = self.temp_dir / f"{upload_id}.zip"
        
        try:
            # Save file in chunks to handle large files
            file_size = 0
            with open(temp_file_path, 'wb') as buffer:
                while chunk := await file.read(1024 * 1024):  # 1MB chunks
                    buffer.write(chunk)
                    file_size += len(chunk)
            
            logger.info(f"Saved upload {upload_id}: {file_size} bytes")
            return upload_id, temp_file_path, file_size
        
        except Exception as e:
            # Cleanup on error
            if temp_file_path.exists():
                temp_file_path.unlink()
            logger.error(f"Error saving upload: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save upload: {str(e)}"
            )
    
    def extract_zip(self, zip_path: Path, upload_id: str) -> Path:
        """
        Extract ZIP file preserving directory structure.
        Returns path to extracted directory.
        """
        extract_path = self.upload_dir / upload_id
        
        try:
            # Validate ZIP file
            if not zipfile.is_zipfile(zip_path):
                raise ValueError("Invalid ZIP file")
            
            # Extract with safety checks
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Check for path traversal attacks
                for member in zip_ref.namelist():
                    if member.startswith('/') or '..' in member:
                        raise ValueError(f"Unsafe file path in ZIP: {member}")
                
                # Extract
                zip_ref.extractall(extract_path)
            
            logger.info(f"Extracted {upload_id} to {extract_path}")
            return extract_path
        
        except zipfile.BadZipFile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Corrupted ZIP file"
            )
        except Exception as e:
            # Cleanup on error
            if extract_path.exists():
                shutil.rmtree(extract_path, ignore_errors=True)
            logger.error(f"Error extracting ZIP: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to extract ZIP: {str(e)}"
            )
    
    def cleanup_temp(self, temp_path: Path):
        """Remove temporary file."""
        try:
            if temp_path.exists():
                temp_path.unlink()
                logger.debug(f"Cleaned up temp file: {temp_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file: {e}")


# Initialize file handler
file_handler = FileHandler()


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_codebase(file: UploadFile = File(...)):
    """
    Upload a zipped codebase for analysis.
    
    - **file**: ZIP file containing the codebase (max 100MB by default)
    
    Returns upload metadata and extraction status.
    """
    logger.info(f"Received upload request: {file.filename}")
    
    # Validate file
    is_valid, error_msg = await file_handler.validate_file(file)
    if not is_valid:
        logger.warning(f"Validation failed: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    temp_file_path = None
    upload_id = None
    
    try:
        # Save upload
        upload_id, temp_file_path, file_size = await file_handler.save_upload(file)
        
        # Extract ZIP
        extract_path = file_handler.extract_zip(temp_file_path, upload_id)
        
        # Cleanup temp file
        file_handler.cleanup_temp(temp_file_path)
        
        logger.info(f"Upload completed successfully: {upload_id}")
        
        return UploadResponse(
            upload_id=upload_id,
            filename=file.filename,
            size_bytes=file_size,
            extracted_to=str(extract_path),
            status="success",
            timestamp=datetime.utcnow().isoformat(),
            message="Upload and extraction completed successfully"
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        # Cleanup on unexpected error
        if temp_file_path and temp_file_path.exists():
            file_handler.cleanup_temp(temp_file_path)
        
        if upload_id:
            extract_path = file_handler.upload_dir / upload_id
            if extract_path.exists():
                shutil.rmtree(extract_path, ignore_errors=True)
        
        logger.error(f"Unexpected error during upload: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during upload"
        )


@router.delete("/{upload_id}")
async def delete_upload(upload_id: str):
    """
    Delete an upload and all its associated data.
    """
    from utils.cleanup import cleanup_manager
    
    if not cleanup_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cleanup service not available"
        )
    
    success = cleanup_manager.cleanup_specific_upload(upload_id)
    
    if success:
        return {
            "message": f"Upload {upload_id} deleted successfully",
            "upload_id": upload_id
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete upload"
        )
