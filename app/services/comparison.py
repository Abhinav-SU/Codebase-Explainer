"""
Codebase comparison utilities for multi-project analysis.
Compares file structures, dependencies, and summaries across codebases.
"""
import hashlib
from typing import List, Dict, Set, Tuple, Optional
from pathlib import Path
from datetime import datetime

from app.models.codebase_metadata import (
    CodebaseMetadata,
    FileMetadataStandard,
    CodebaseComparison,
    DependencyMetadata
)
from utils.logger import setup_logger

logger = setup_logger(__name__)


class CodebaseComparator:
    """Compare two codebases and identify differences."""
    
    def __init__(self):
        self.base_metadata: Optional[CodebaseMetadata] = None
        self.compare_metadata: Optional[CodebaseMetadata] = None
    
    def compare(
        self,
        base: CodebaseMetadata,
        compare: CodebaseMetadata
    ) -> CodebaseComparison:
        """
        Compare two codebases and return detailed comparison results.
        
        Args:
            base: Base codebase metadata
            compare: Codebase to compare against base
            
        Returns:
            CodebaseComparison with all differences highlighted
        """
        logger.info(f"Comparing {base.name} vs {compare.name}")
        
        self.base_metadata = base
        self.compare_metadata = compare
        
        # Compare file structures
        file_changes = self._compare_file_structures()
        
        # Compare metrics
        metric_changes = self._compare_metrics()
        
        # Compare dependencies
        dep_changes = self._compare_dependencies()
        
        # Calculate similarity
        similarity = self._calculate_similarity()
        
        # Generate summary
        summary = self._generate_summary(file_changes, metric_changes, dep_changes)
        
        return CodebaseComparison(
            base_upload_id=base.upload_id,
            compare_upload_id=compare.upload_id,
            base_name=base.name,
            compare_name=compare.name,
            compared_at=datetime.utcnow(),
            
            files_added=file_changes['added'],
            files_removed=file_changes['removed'],
            files_modified=file_changes['modified'],
            files_unchanged=file_changes['unchanged'],
            
            size_change_bytes=metric_changes['size_change'],
            size_change_percent=metric_changes['size_change_percent'],
            lines_change=metric_changes['lines_change'],
            lines_change_percent=metric_changes['lines_change_percent'],
            classes_change=metric_changes['classes_change'],
            functions_change=metric_changes['functions_change'],
            
            dependencies_added=dep_changes['added'],
            dependencies_removed=dep_changes['removed'],
            new_circular_dependencies=dep_changes['new_circular'],
            resolved_circular_dependencies=dep_changes['resolved_circular'],
            
            similarity_score=similarity,
            comparison_summary=summary
        )
    
    def _compare_file_structures(self) -> Dict[str, List[str]]:
        """Compare file lists and identify changes."""
        base_files = {f.relative_path: f for f in self.base_metadata.files}
        compare_files = {f.relative_path: f for f in self.compare_metadata.files}
        
        base_paths = set(base_files.keys())
        compare_paths = set(compare_files.keys())
        
        added = list(compare_paths - base_paths)
        removed = list(base_paths - compare_paths)
        common = list(base_paths & compare_paths)
        
        # Check for modifications in common files
        modified = []
        unchanged = []
        
        for path in common:
            base_file = base_files[path]
            compare_file = compare_files[path]
            
            # Compare using hash if available
            if base_file.content_hash and compare_file.content_hash:
                if base_file.content_hash != compare_file.content_hash:
                    modified.append(path)
                else:
                    unchanged.append(path)
            # Fallback to size comparison
            elif base_file.size_bytes != compare_file.size_bytes:
                modified.append(path)
            else:
                unchanged.append(path)
        
        logger.info(f"Files: +{len(added)}, -{len(removed)}, ~{len(modified)}, ={len(unchanged)}")
        
        return {
            'added': sorted(added),
            'removed': sorted(removed),
            'modified': sorted(modified),
            'unchanged': sorted(unchanged)
        }
    
    def _compare_metrics(self) -> Dict[str, any]:
        """Compare code metrics between codebases."""
        size_change = self.compare_metadata.total_bytes - self.base_metadata.total_bytes
        size_change_percent = (size_change / self.base_metadata.total_bytes * 100) if self.base_metadata.total_bytes > 0 else 0
        
        lines_change = self.compare_metadata.total_lines - self.base_metadata.total_lines
        lines_change_percent = (lines_change / self.base_metadata.total_lines * 100) if self.base_metadata.total_lines > 0 else 0
        
        classes_change = self.compare_metadata.total_classes - self.base_metadata.total_classes
        functions_change = self.compare_metadata.total_functions - self.base_metadata.total_functions
        
        return {
            'size_change': size_change,
            'size_change_percent': round(size_change_percent, 2),
            'lines_change': lines_change,
            'lines_change_percent': round(lines_change_percent, 2),
            'classes_change': classes_change,
            'functions_change': functions_change
        }
    
    def _compare_dependencies(self) -> Dict[str, List]:
        """Compare dependency information."""
        base_deps = self.base_metadata.dependencies
        compare_deps = self.compare_metadata.dependencies
        
        if not base_deps or not compare_deps:
            return {
                'added': [],
                'removed': [],
                'new_circular': [],
                'resolved_circular': []
            }
        
        # Compare external packages
        base_packages = set(base_deps.external_packages)
        compare_packages = set(compare_deps.external_packages)
        
        added_deps = list(compare_packages - base_packages)
        removed_deps = list(base_packages - compare_packages)
        
        # Compare circular dependencies
        base_circular = set(tuple(chain) for chain in base_deps.circular_dependencies)
        compare_circular = set(tuple(chain) for chain in compare_deps.circular_dependencies)
        
        new_circular = [list(chain) for chain in (compare_circular - base_circular)]
        resolved_circular = [list(chain) for chain in (base_circular - compare_circular)]
        
        return {
            'added': sorted(added_deps),
            'removed': sorted(removed_deps),
            'new_circular': new_circular,
            'resolved_circular': resolved_circular
        }
    
    def _calculate_similarity(self) -> float:
        """
        Calculate similarity score between codebases.
        Based on shared files and unchanged content.
        """
        base_count = len(self.base_metadata.files)
        compare_count = len(self.compare_metadata.files)
        
        if base_count == 0 and compare_count == 0:
            return 1.0
        
        if base_count == 0 or compare_count == 0:
            return 0.0
        
        base_paths = set(f.relative_path for f in self.base_metadata.files)
        compare_paths = set(f.relative_path for f in self.compare_metadata.files)
        
        common_files = base_paths & compare_paths
        total_unique = base_paths | compare_paths
        
        # Jaccard similarity for file sets
        if len(total_unique) == 0:
            return 1.0
        
        similarity = len(common_files) / len(total_unique)
        
        return round(similarity, 3)
    
    def _generate_summary(
        self,
        file_changes: Dict,
        metric_changes: Dict,
        dep_changes: Dict
    ) -> str:
        """Generate human-readable comparison summary."""
        lines = []
        
        # File changes summary
        if file_changes['added']:
            lines.append(f"Added {len(file_changes['added'])} new files")
        if file_changes['removed']:
            lines.append(f"Removed {len(file_changes['removed'])} files")
        if file_changes['modified']:
            lines.append(f"Modified {len(file_changes['modified'])} files")
        
        # Size changes
        size_change = metric_changes['size_change']
        if abs(size_change) > 1024:
            size_kb = size_change / 1024
            direction = "increased" if size_change > 0 else "decreased"
            lines.append(f"Codebase size {direction} by {abs(size_kb):.1f} KB ({metric_changes['size_change_percent']:+.1f}%)")
        
        # Code metrics
        if metric_changes['lines_change'] != 0:
            direction = "added" if metric_changes['lines_change'] > 0 else "removed"
            lines.append(f"{abs(metric_changes['lines_change'])} lines {direction} ({metric_changes['lines_change_percent']:+.1f}%)")
        
        # Dependencies
        if dep_changes['added']:
            lines.append(f"Added dependencies: {', '.join(dep_changes['added'][:5])}" + 
                        (f" and {len(dep_changes['added'])-5} more" if len(dep_changes['added']) > 5 else ""))
        
        if dep_changes['new_circular']:
            lines.append(f"⚠️ Introduced {len(dep_changes['new_circular'])} new circular dependencies")
        
        if dep_changes['resolved_circular']:
            lines.append(f"✓ Resolved {len(dep_changes['resolved_circular'])} circular dependencies")
        
        if not lines:
            return "No significant changes detected"
        
        return "; ".join(lines)


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of file content."""
    sha256 = hashlib.sha256()
    
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        logger.warning(f"Failed to hash {file_path}: {e}")
        return ""
