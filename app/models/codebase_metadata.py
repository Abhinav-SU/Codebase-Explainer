"""
Standardized metadata models for codebase information.
Enables consistent comparison across multiple uploaded projects.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from pathlib import Path


class FileMetadataStandard(BaseModel):
    """Standardized file metadata for comparison."""
    relative_path: str
    filename: str
    size_bytes: int
    extension: str
    lines_count: Optional[int] = None
    classes_count: Optional[int] = 0
    functions_count: Optional[int] = 0
    imports: List[str] = Field(default_factory=list)
    
    # For comparison purposes
    content_hash: Optional[str] = None  # SHA256 hash for exact match detection
    

class DependencyMetadata(BaseModel):
    """Dependency information for a codebase."""
    total_dependencies: int
    circular_dependencies: List[List[str]] = Field(default_factory=list)
    most_imported_files: List[Dict[str, Any]] = Field(default_factory=list)
    missing_imports: List[str] = Field(default_factory=list)
    external_packages: List[str] = Field(default_factory=list)


class CodebaseMetadata(BaseModel):
    """Complete standardized metadata for a codebase."""
    upload_id: str
    name: str  # Original filename or project name
    uploaded_at: datetime
    
    # File structure
    total_files: int
    total_bytes: int
    file_types: Dict[str, int]  # {'.py': 25, '.js': 10}
    folder_structure: Dict[str, int]  # {'src': 15, 'tests': 10}
    
    # Code metrics
    total_lines: int
    total_classes: int
    total_functions: int
    
    # Dependencies
    dependencies: Optional[DependencyMetadata] = None
    
    # Files detail (for comparison)
    files: List[FileMetadataStandard] = Field(default_factory=list)
    
    # Summary information
    has_summaries: bool = False
    summaries_generated_at: Optional[datetime] = None
    
    # Version/tag for comparison
    version_tag: Optional[str] = None
    

class CodebaseComparison(BaseModel):
    """Result of comparing two codebases."""
    base_upload_id: str
    compare_upload_id: str
    base_name: str
    compare_name: str
    compared_at: datetime
    
    # File structure differences
    files_added: List[str] = Field(default_factory=list)
    files_removed: List[str] = Field(default_factory=list)
    files_modified: List[str] = Field(default_factory=list)
    files_unchanged: List[str] = Field(default_factory=list)
    
    # Size differences
    size_change_bytes: int = 0
    size_change_percent: float = 0.0
    
    # Code metric changes
    lines_change: int = 0
    lines_change_percent: float = 0.0
    classes_change: int = 0
    functions_change: int = 0
    
    # Dependency changes
    dependencies_added: List[str] = Field(default_factory=list)
    dependencies_removed: List[str] = Field(default_factory=list)
    new_circular_dependencies: List[List[str]] = Field(default_factory=list)
    resolved_circular_dependencies: List[List[str]] = Field(default_factory=list)
    
    # Summary
    similarity_score: float = 0.0  # 0-1, based on shared files and content
    comparison_summary: str = ""
