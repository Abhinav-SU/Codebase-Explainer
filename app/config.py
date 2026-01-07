"""
Configuration management with proper validation and defaults.
Handles missing API keys gracefully.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
import warnings


class Settings(BaseSettings):
    """Application settings with validation and defaults."""
    
    # Google Gemini Configuration
    gemini_api_key: Optional[str] = Field(default=None, env='GEMINI_API_KEY')
    enable_ai_features: bool = Field(default=True, env='ENABLE_AI_FEATURES')
    
    # File Upload Settings
    max_upload_size_mb: int = Field(default=100, env='MAX_UPLOAD_SIZE_MB')
    max_file_size_bytes: int = Field(default=104857600, env='MAX_FILE_SIZE_BYTES')
    
    # Storage Paths
    upload_dir: str = Field(default='uploads', env='UPLOAD_DIR')
    summaries_dir: str = Field(default='summaries', env='SUMMARIES_DIR')
    
    # API Configuration
    api_host: str = Field(default='0.0.0.0', env='API_HOST')
    api_port: int = Field(default=8000, env='API_PORT')
    api_workers: int = Field(default=4, env='API_WORKERS')
    
    # CORS Settings
    allowed_origins: str = Field(
        default='http://localhost:8501,http://localhost:3000',
        env='ALLOWED_ORIGINS'
    )
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, env='RATE_LIMIT_PER_MINUTE')
    
    # Cleanup Settings
    cleanup_enabled: bool = Field(default=True, env='CLEANUP_ENABLED')
    cleanup_interval_hours: int = Field(default=24, env='CLEANUP_INTERVAL_HOURS')
    max_file_age_days: int = Field(default=7, env='MAX_FILE_AGE_DAYS')
    
    # Logging
    log_level: str = Field(default='INFO', env='LOG_LEVEL')
    log_format: str = Field(default='json', env='LOG_FORMAT')
    
    # Demo Mode
    demo_mode: bool = Field(default=False, env='DEMO_MODE')
    
    class Config:
        env_file = '.env'
        case_sensitive = False
    
    @field_validator('gemini_api_key')
    @classmethod
    def validate_api_key(cls, v, info):
        """Validate API key if AI features are enabled."""
        # Check if key is missing or is a placeholder
        if v and v.strip().lower() in ['your_api_key_here', 'your_key_here', '']:
            v = None
        
        # Note: In pydantic v2, we can't access other fields directly in validator
        # The enable_ai_features check will happen in model_post_init
        return v
    
    def model_post_init(self, __context):
        """Post-initialization to check AI features."""
        if self.enable_ai_features and not self.gemini_api_key:
            warnings.warn(
                "[WARN] Google Gemini API key not found! AI features will be disabled. "
                "Set GEMINI_API_KEY in .env file to enable AI summarization."
            )
            self.enable_ai_features = False
    
    @field_validator('allowed_origins')
    @classmethod
    def parse_origins(cls, v):
        """Parse comma-separated origins into list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    def get_absolute_path(self, relative_path: str) -> Path:
        """Convert relative path to absolute path."""
        base_dir = Path(__file__).parent.parent
        return base_dir / relative_path
    
    def ensure_directories_exist(self):
        """Create necessary directories on startup."""
        directories = [
            self.get_absolute_path(self.upload_dir),
            self.get_absolute_path(self.summaries_dir),
            self.get_absolute_path(self.upload_dir) / 'temp',
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"[OK] Directory ensured: {directory}")
    
    @property
    def ai_available(self) -> bool:
        """Check if AI features are available."""
        return self.enable_ai_features and self.gemini_api_key is not None
    
    @property
    def cors_origins(self) -> list:
        """Get CORS origins as list."""
        if isinstance(self.allowed_origins, str):
            return [origin.strip() for origin in self.allowed_origins.split(',')]
        return self.allowed_origins


# Global settings instance
settings = Settings()

# Validate configuration on import
if not settings.ai_available:
    print("[WARN] Running in NO-AI mode. Template-based summaries only.")
    print("   To enable AI: Set GEMINI_API_KEY in .env file")
else:
    print("[OK] AI features enabled (Google Gemini)")

# Ensure directories exist on import
settings.ensure_directories_exist()
