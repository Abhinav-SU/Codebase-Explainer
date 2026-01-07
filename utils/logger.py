"""
Logging utilities with structured JSON logging for production.
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from pythonjsonlogger import jsonlogger


def setup_logger(name: str, log_level: str = 'INFO', log_format: str = 'json') -> logging.Logger:
    """
    Set up logger with JSON formatting for production.
    
    Args:
        name: Logger name (usually __name__)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: 'json' or 'text'
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if log_format == 'json':
        # JSON formatter for production
        formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s %(pathname)s %(lineno)d',
            rename_fields={'level': 'severity', 'timestamp': 'time'}
        )
    else:
        # Simple text formatter for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler for errors
    log_dir = Path(__file__).parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    error_handler = logging.FileHandler(log_dir / 'errors.log')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    return logger


class RequestLogger:
    """Middleware-compatible logger for API requests."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_request(self, method: str, path: str, status_code: int, duration_ms: float):
        """Log API request with timing."""
        self.logger.info(
            "API Request",
            extra={
                'method': method,
                'path': path,
                'status_code': status_code,
                'duration_ms': duration_ms,
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    def log_error(self, error: Exception, context: dict = None):
        """Log error with context."""
        self.logger.error(
            f"Error: {str(error)}",
            extra={
                'error_type': type(error).__name__,
                'context': context or {},
                'timestamp': datetime.utcnow().isoformat()
            },
            exc_info=True
        )
