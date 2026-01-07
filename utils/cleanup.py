"""
Automatic cleanup utilities to prevent disk space issues.
Runs scheduled cleanup of old uploads and temporary files.
"""
import shutil
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List
import threading
import schedule

from utils.logger import setup_logger

logger = setup_logger(__name__)


class FileCleanupManager:
    """Manages automatic cleanup of old files."""
    
    def __init__(
        self,
        upload_dir: Path,
        summaries_dir: Path,
        max_age_days: int = 7,
        cleanup_interval_hours: int = 24
    ):
        self.upload_dir = Path(upload_dir)
        self.summaries_dir = Path(summaries_dir)
        self.max_age_days = max_age_days
        self.cleanup_interval_hours = cleanup_interval_hours
        self._stop_event = threading.Event()
        self._cleanup_thread = None
    
    def cleanup_old_files(self) -> dict:
        """
        Remove files older than max_age_days.
        Returns statistics about cleanup.
        """
        cutoff_time = time.time() - (self.max_age_days * 86400)  # 86400 seconds per day
        stats = {
            'uploads_removed': 0,
            'summaries_removed': 0,
            'bytes_freed': 0,
            'errors': []
        }
        
        # Clean uploads
        try:
            for upload_path in self.upload_dir.iterdir():
                if upload_path.is_dir():
                    if upload_path.stat().st_mtime < cutoff_time:
                        size = self._get_dir_size(upload_path)
                        shutil.rmtree(upload_path)
                        stats['uploads_removed'] += 1
                        stats['bytes_freed'] += size
                        logger.info(f"Removed old upload: {upload_path}")
        except Exception as e:
            stats['errors'].append(f"Upload cleanup error: {str(e)}")
            logger.error(f"Error cleaning uploads: {e}")
        
        # Clean summaries
        try:
            for summary_path in self.summaries_dir.iterdir():
                if summary_path.is_dir():
                    if summary_path.stat().st_mtime < cutoff_time:
                        size = self._get_dir_size(summary_path)
                        shutil.rmtree(summary_path)
                        stats['summaries_removed'] += 1
                        stats['bytes_freed'] += size
                        logger.info(f"Removed old summary: {summary_path}")
        except Exception as e:
            stats['errors'].append(f"Summary cleanup error: {str(e)}")
            logger.error(f"Error cleaning summaries: {e}")
        
        # Clean temp directory
        try:
            temp_dir = self.upload_dir / 'temp'
            if temp_dir.exists():
                for temp_file in temp_dir.iterdir():
                    if temp_file.is_file():
                        if temp_file.stat().st_mtime < time.time() - 3600:  # 1 hour
                            size = temp_file.stat().st_size
                            temp_file.unlink()
                            stats['bytes_freed'] += size
        except Exception as e:
            stats['errors'].append(f"Temp cleanup error: {str(e)}")
            logger.error(f"Error cleaning temp files: {e}")
        
        logger.info(f"Cleanup completed: {stats}")
        return stats
    
    def cleanup_specific_upload(self, upload_id: str) -> bool:
        """Remove a specific upload and its summaries."""
        try:
            upload_path = self.upload_dir / upload_id
            summary_path = self.summaries_dir / upload_id
            
            if upload_path.exists():
                shutil.rmtree(upload_path)
                logger.info(f"Removed upload: {upload_id}")
            
            if summary_path.exists():
                shutil.rmtree(summary_path)
                logger.info(f"Removed summary: {upload_id}")
            
            return True
        except Exception as e:
            logger.error(f"Error removing upload {upload_id}: {e}")
            return False
    
    def get_disk_usage(self) -> dict:
        """Get current disk usage statistics."""
        return {
            'upload_dir_bytes': self._get_dir_size(self.upload_dir),
            'summaries_dir_bytes': self._get_dir_size(self.summaries_dir),
            'upload_count': len(list(self.upload_dir.iterdir())) if self.upload_dir.exists() else 0,
            'summary_count': len(list(self.summaries_dir.iterdir())) if self.summaries_dir.exists() else 0
        }
    
    def _get_dir_size(self, path: Path) -> int:
        """Calculate total size of directory."""
        total = 0
        try:
            for item in path.rglob('*'):
                if item.is_file():
                    total += item.stat().st_size
        except Exception as e:
            logger.error(f"Error calculating size for {path}: {e}")
        return total
    
    def start_scheduled_cleanup(self):
        """Start background thread for scheduled cleanup."""
        schedule.every(self.cleanup_interval_hours).hours.do(self.cleanup_old_files)
        
        def run_schedule():
            while not self._stop_event.is_set():
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        self._cleanup_thread = threading.Thread(target=run_schedule, daemon=True)
        self._cleanup_thread.start()
        logger.info(f"Cleanup scheduler started (interval: {self.cleanup_interval_hours}h)")
    
    def stop_scheduled_cleanup(self):
        """Stop the cleanup scheduler."""
        self._stop_event.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        logger.info("Cleanup scheduler stopped")


# Global cleanup manager (initialized in main.py)
cleanup_manager = None
