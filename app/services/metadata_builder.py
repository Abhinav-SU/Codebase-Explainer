"""
Metadata Builder - Constructs standardized codebase metadata.
Analyzes uploaded codebase and extracts all relevant information.
"""
import ast
from typing import List, Dict, Optional, Set
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from app.models.codebase_metadata import (
    CodebaseMetadata,
    FileMetadataStandard,
    DependencyMetadata
)
from app.services.comparison import compute_file_hash
from utils.logger import setup_logger

logger = setup_logger(__name__)


class MetadataBuilder:
    """Builds standardized metadata from uploaded codebase."""
    
    SUPPORTED_EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h'}
    EXCLUDE_DIRS = {'__pycache__', '.git', 'venv', 'node_modules', '.venv', 'env', 'build', 'dist'}
    
    def __init__(self, upload_dir: Path):
        self.upload_dir = upload_dir
        self.files_metadata: List[FileMetadataStandard] = []
        self.file_types: Dict[str, int] = defaultdict(int)
        self.folder_structure: Dict[str, int] = defaultdict(int)
        self.total_bytes = 0
        self.total_lines = 0
        self.total_classes = 0
        self.total_functions = 0
        self.external_packages: Set[str] = set()
    
    def build_metadata(self, upload_id: str) -> CodebaseMetadata:
        """
        Build complete metadata for a codebase.
        
        Args:
            upload_id: Upload identifier
            
        Returns:
            CodebaseMetadata with all information populated
        """
        logger.info(f"Building metadata for {upload_id}")
        
        # Reset counters
        self.files_metadata = []
        self.file_types = defaultdict(int)
        self.folder_structure = defaultdict(int)
        self.total_bytes = 0
        self.total_lines = 0
        self.total_classes = 0
        self.total_functions = 0
        self.external_packages = set()
        
        # Scan all files
        self._scan_directory()
        
        # Get upload info
        upload_name = self.upload_dir.name
        upload_time = datetime.fromtimestamp(self.upload_dir.stat().st_mtime)
        
        # Check if summaries exist
        summary_dir = Path("summaries") / upload_id
        has_summaries = summary_dir.exists() and any(summary_dir.glob('*.json'))
        summaries_time = datetime.fromtimestamp(summary_dir.stat().st_mtime) if has_summaries else None
        
        # Build dependency metadata if available
        dependencies = self._build_dependency_metadata()
        
        metadata = CodebaseMetadata(
            upload_id=upload_id,
            name=upload_name,
            uploaded_at=upload_time,
            total_files=len(self.files_metadata),
            total_bytes=self.total_bytes,
            file_types=dict(self.file_types),
            folder_structure=dict(self.folder_structure),
            total_lines=self.total_lines,
            total_classes=self.total_classes,
            total_functions=self.total_functions,
            dependencies=dependencies,
            files=self.files_metadata,
            has_summaries=has_summaries,
            summaries_generated_at=summaries_time
        )
        
        logger.info(f"Metadata complete: {len(self.files_metadata)} files, {self.total_lines} lines")
        return metadata
    
    def _scan_directory(self):
        """Scan directory and collect file metadata."""
        for dirpath, dirnames, filenames in self.upload_dir.walk():
            # Skip excluded directories
            dirnames[:] = [d for d in dirnames if d not in self.EXCLUDE_DIRS]
            
            # Get folder name for structure tracking
            rel_dir = dirpath.relative_to(self.upload_dir)
            folder_name = str(rel_dir.parts[0]) if rel_dir.parts else "root"
            
            for filename in filenames:
                filepath = dirpath / filename
                ext = filepath.suffix.lower()
                
                if ext not in self.SUPPORTED_EXTENSIONS:
                    continue
                
                try:
                    # Basic file info
                    size_bytes = filepath.stat().st_size
                    rel_path = filepath.relative_to(self.upload_dir)
                    
                    # Extract code metrics for Python files
                    lines_count = None
                    classes_count = 0
                    functions_count = 0
                    imports = []
                    content_hash = ""
                    
                    if ext == '.py':
                        metrics = self._extract_python_metrics(filepath)
                        lines_count = metrics['lines']
                        classes_count = metrics['classes']
                        functions_count = metrics['functions']
                        imports = metrics['imports']
                        content_hash = compute_file_hash(filepath)
                        
                        # Update totals
                        self.total_lines += lines_count
                        self.total_classes += classes_count
                        self.total_functions += functions_count
                        
                        # Track external packages
                        for imp in imports:
                            if not imp.startswith('.') and '.' not in imp:
                                self.external_packages.add(imp)
                    
                    # Create file metadata
                    file_meta = FileMetadataStandard(
                        relative_path=str(rel_path).replace('\\', '/'),
                        filename=filename,
                        size_bytes=size_bytes,
                        extension=ext,
                        lines_count=lines_count,
                        classes_count=classes_count,
                        functions_count=functions_count,
                        imports=imports,
                        content_hash=content_hash
                    )
                    
                    self.files_metadata.append(file_meta)
                    
                    # Update counters
                    self.file_types[ext] += 1
                    self.folder_structure[folder_name] += 1
                    self.total_bytes += size_bytes
                    
                except Exception as e:
                    logger.warning(f"Failed to process {filepath}: {e}")
    
    def _extract_python_metrics(self, filepath: Path) -> Dict:
        """Extract metrics from Python file using AST."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.count('\n') + 1
            
            try:
                tree = ast.parse(content)
                classes = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
                functions = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
                
                # Extract imports
                imports = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.append(node.module)
                
                return {
                    'lines': lines,
                    'classes': classes,
                    'functions': functions,
                    'imports': imports
                }
            except SyntaxError:
                # File has syntax errors, return basic info
                return {
                    'lines': lines,
                    'classes': 0,
                    'functions': 0,
                    'imports': []
                }
        except Exception as e:
            logger.warning(f"Failed to parse {filepath}: {e}")
            return {
                'lines': 0,
                'classes': 0,
                'functions': 0,
                'imports': []
            }
    
    def _build_dependency_metadata(self) -> Optional[DependencyMetadata]:
        """Build dependency metadata if graph data is available."""
        # For now, return basic dependency info without full graph analysis
        # Full graph can be generated on-demand via /api/graph endpoint
        try:
            return DependencyMetadata(
                total_dependencies=0,
                circular_dependencies=[],
                most_imported_files=[],
                missing_imports=[],
                external_packages=sorted(list(self.external_packages))
            )
        except Exception as e:
            logger.debug(f"Dependency metadata skipped: {e}")
            return None
